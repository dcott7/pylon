from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from .base import (
    LeagueRules,
    KickoffSetup,
    LeagueRulesError,
    ExtraPointSetup,
    ScoringTypeEnum,
)
from ..team import Team
from ...models.registry import ModelRegistry
from ...rng import RNG
from ...state.game_state import GameState
from ...models.misc import (
    CoinTossWinnerModel,
    CoinTossContext,
    CoinTossChoice,
    KickReceiveContext,
    KickReceiveChoiceModel,
)

if TYPE_CHECKING:
    from pylon.state.drive_record import DriveRecord, DriveEndResult
    from pylon.state.play_record import PlayRecord


logger = logging.getLogger(__name__)


class NFLKickoffRules:
    def __init__(self, kickoff_spot: int) -> None:
        self.kickoff_spot = kickoff_spot

    def get_coin_toss_winner(
        self, game_state: GameState, models: ModelRegistry, rng: RNG
    ) -> Team:
        coin_toss_model = models.get_typed("coin_toss_winner", CoinTossWinnerModel)  # type: ignore

        winner = coin_toss_model.execute(CoinTossContext(game_state, rng))
        return winner

    def schedule_kickoff(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        winner = self.get_coin_toss_winner(game_state, models, rng)
        loser = game_state.opponent(winner)
        game_state.set_coin_toss_winner(winner)

        choice = models.get_typed(
            "kick_receive_choice",
            KickReceiveChoiceModel,  # type: ignore
        ).execute(KickReceiveContext(game_state, rng))
        game_state.set_coin_toss_winner_choice(choice)

        if choice == CoinTossChoice.RECEIVE:
            kicking_team = loser
            receiving_team = winner

        elif choice == CoinTossChoice.KICK:
            kicking_team = winner
            receiving_team = loser

        else:
            raise LeagueRulesError("Invalid coin toss choice")

        game_state.set_pending_kickoff(
            KickoffSetup(
                kicking_team=kicking_team,
                receiving_team=receiving_team,
                kickoff_spot=NFLRules.KICKOFF_SPOT,
            )
        )


class NFLRules(LeagueRules):
    MINUTES_PER_QUARTER = 15
    QUARTERS_PER_HALF = 2
    TIMEOUTS_PER_HALF = 3
    KICKOFF_SPOT = 35  # Yard line for kickoff
    EXTRA_POINT_SPOT = 15  # Yard line for extra point attempts

    SCORING_VALUES = {
        ScoringTypeEnum.TOUCHDOWN: 6,
        ScoringTypeEnum.FIELD_GOAL: 3,
        ScoringTypeEnum.SAFETY: 2,
        ScoringTypeEnum.EXTRA_POINT_KICK: 1,
        ScoringTypeEnum.EXTRA_POINT_TWO_POINT: 2,
    }

    def start_game(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        kickoff_rules = NFLKickoffRules(NFLRules.KICKOFF_SPOT)
        kickoff_rules.schedule_kickoff(game_state, models, rng)

    def on_drive_end(self, game_state: GameState, drive_record: DriveRecord) -> None:
        if not drive_record.is_finalized():
            msg = "DriveRecord must be finalized before applying end-of-drive rules."
            logger.error(msg)
            raise LeagueRulesError(msg)

        if drive_record.result == DriveEndResult.SCORE:
            assert drive_record.end_pos_team is not None
            scoring_team = drive_record.end_pos_team

            game_state.set_pending_extra_point(
                ExtraPointSetup(
                    kicking_team=scoring_team,
                    spot=NFLRules.EXTRA_POINT_SPOT,
                )
            )

        # schedule kickoff for next drive based on the drive result
        if drive_record.result in (DriveEndResult.SCORE, DriveEndResult.END_OF_HALF):
            assert drive_record.end_pos_team is not None
            scoring_team = drive_record.end_pos_team
            receiving_team = game_state.opponent(scoring_team)

            # TODO: Handle SAFETY case... we dont kick, we punt from our 20

            game_state.set_pending_kickoff(
                KickoffSetup(
                    kicking_team=scoring_team,
                    receiving_team=receiving_team,
                    kickoff_spot=NFLRules.KICKOFF_SPOT,
                )
            )

    def on_play_end(self, game_state: GameState, play_record: PlayRecord) -> None:
        if not play_record.is_finalized():
            msg = "PlayRecord must be finalized before applying to GameState"
            logger.error(msg)
            raise LeagueRulesError(msg)

        if play_record.is_scoring_play:
            if play_record.scoring_team is None:
                msg = "Scoring play must have a scoring team"
                logger.error(msg)
                raise LeagueRulesError(msg)

            play_record.end_pos_team_score = play_record.start_pos_team_score
            play_record.end_def_team_score = play_record.start_def_team_score

            scoring_value = NFLRules.SCORING_VALUES[play_record.scoring_type]

            if play_record.scoring_team == play_record.end_pos_team:
                play_record.end_pos_team_score += scoring_value
            elif play_record.scoring_team == play_record.end_def_team:
                play_record.end_def_team_score += scoring_value
            else:
                msg = "Scoring team must be either offense or defense"
                logger.error(msg)
                raise LeagueRulesError(msg)

        assert play_record.end_pos_team is not None
        assert play_record.end_def_team is not None
        play_record.end_pos_team_score = game_state.scoreboard.current_score(
            play_record.end_pos_team
        )
        play_record.end_def_team_score = game_state.scoreboard.current_score(
            play_record.end_def_team
        )

    def start_half(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        if game_state.coin_toss_winner is None:
            msg = "Coin toss winner must be set before starting half"
            logger.error(msg)
            raise LeagueRulesError(msg)

        if game_state.coin_toss_winner_choice is None:
            msg = "Coin toss winner choice must be set before starting half"
            logger.error(msg)
            raise LeagueRulesError(msg)

        kicking_team = (
            game_state.coin_toss_winner
            if game_state.coin_toss_winner_choice == CoinTossChoice.RECEIVE
            else game_state.opponent(game_state.coin_toss_winner)
        )
        receiving_team = game_state.opponent(kicking_team)

        game_state.set_pending_kickoff(
            KickoffSetup(
                kicking_team=kicking_team,
                receiving_team=receiving_team,
                kickoff_spot=NFLRules.KICKOFF_SPOT,
            )
        )
