"""
National Football League (NFL) ruleset implementation.

Defines all NFL-specific constants and rules including:
- Game structure (15-minute quarters, 2 halves, 4 downs, 10-yard first downs)
- Field dimensions and kickoff/extra point spots
- Scoring values (touchdown=6, field goal=3, safety=2, etc.)
- Game flow (coin toss, kickoffs, halves, drive ends, game end conditions)

The NFLRules class implements the LeagueRules interface and is responsible for
deciding what should happen according to NFL rules. It interacts with the model
registry to make decisions (coin toss winner, kick/receive choice, etc.).
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from ...models.registry import ModelRegistry
from ...rng import RNG
from ...models.misc import (
    CoinTossWinnerModel,
    CoinTossContext,
    KickReceiveContext,
    KickReceiveChoiceModel,
    CoinTossChoice,
)
from ...state.game_state import GameState
from ...state.play_record import ScoringTypeEnum
from .base import (
    LeagueRules,
    FirstDownRule,
    KickoffSetup,
)

if TYPE_CHECKING:
    from pylon.state.drive_record import DriveRecord
    from pylon.state.play_record import PlayRecord, PlayExecutionData
    from pylon.domain.team import Team


logger = logging.getLogger(__name__)


class NFLRules(LeagueRules):
    """
    Official National Football League ruleset.

    Defines all constants and behaviors for NFL simulations:

    Game Structure:
    - 15 minutes per quarter (900 seconds)
    - 2 quarters per half (1,800 seconds/half)
    - 4 quarters per game
    - 3 timeouts per team per half

    Field Rules:
    - 100-yard field (plus end zones)
    - Kickoffs from the 35-yard line
    - Extra point attempts from the 15-yard line
    - 10-yard first down requirement
    - Touchback spots at 20-yard line (default) or 35-yard line (kickoff)

    Scoring:
    - Touchdown: 6 points
    - Field Goal: 3 points
    - Safety: 2 points
    - Extra Point (kick): 1 point
    - Extra Point (two-point conversion): 2 points
    """

    # Game structure constants
    MINUTES_PER_QUARTER = 15
    QUARTERS_PER_HALF = 2
    TIMEOUTS_PER_HALF = 3

    # Field position constants
    KICKOFF_SPOT = 35
    EXTRA_POINT_SPOT = 15
    DEFAULT_TOUCHBACK_SPOT = 20
    KICKOFF_TOUCHBACK_SPOT = 35
    FIELD_LENGTH = 100

    # Play rules constants
    FIRST_DOWN_YARDS = 10
    MAX_DOWNS = 4

    # Scoring values
    SCORING_VALUES = {
        ScoringTypeEnum.TOUCHDOWN: 6,
        ScoringTypeEnum.FIELD_GOAL: 3,
        ScoringTypeEnum.SAFETY: 2,
        ScoringTypeEnum.EXTRA_POINT_KICK: 1,
        ScoringTypeEnum.EXTRA_POINT_TWO_POINT: 2,
    }

    # First down rule configuration
    first_down_rule = FirstDownRule(FIRST_DOWN_YARDS, MAX_DOWNS)

    def start_game(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        """
        Execute the opening sequence of an NFL game.

        Involves:
        1. Conducting the coin toss (determines which team gets to choose)
        2. Asking the coin toss winner whether to kick or receive
        3. Setting up the opening kickoff with the appropriate teams

        Args:
            game_state: Current game state to update.
            models: Model registry for accessing coin toss and choice models.
            rng: Random number generator for reproducibility.
        """
        coin_toss_winner = models.get_typed(
            "coin_toss_winner",
            CoinTossWinnerModel,  # type: ignore
        ).execute(CoinTossContext(game_state, rng))
        game_state.set_coin_toss_winner(coin_toss_winner)

        # Coin toss winner typically chooses to receive or defer
        # If they choose to receive, the other team kicks
        # If they defer (choose direction/etc), they kick
        choice = models.get_typed(
            "kick_receive_choice",
            KickReceiveChoiceModel,  # type: ignore
        ).execute(KickReceiveContext(game_state, rng))
        game_state.set_coin_toss_winner_choice(choice)
        # If winner chooses to RECEIVE, the opponent kicks
        # If winner chooses to KICK, they kick
        kicking_team = (
            game_state.opponent(coin_toss_winner)
            if choice == CoinTossChoice.RECEIVE
            else game_state.coin_toss_winner
        )
        assert kicking_team is not None
        receiving_team = game_state.opponent(kicking_team)

        kickoff_setup = KickoffSetup(
            kicking_team=kicking_team,
            receiving_team=receiving_team,
            kickoff_spot=self.KICKOFF_SPOT,
        )
        game_state.set_pending_kickoff(kickoff_setup)
        logger.debug(
            f"Coin toss won by {coin_toss_winner.name}, {kicking_team.name} kicking to {receiving_team.name}"
        )

    def start_half(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        """
        Execute the opening sequence of a new half (after half-time).

        In the NFL, the team that did not kick off in the previous half receives
        the kickoff in the new half. This method sets up the kickoff.

        Args:
            game_state: Current game state to update.
            models: Model registry (unused, but required by interface).
            rng: Random number generator (unused, but required by interface).
        """
        # In NFL, the team that didn't kick in the first half kicks in the second half
        current_possession_team = game_state.pos_team
        kicking_team = game_state.opponent(current_possession_team)
        receiving_team = current_possession_team

        kickoff_setup = KickoffSetup(
            kicking_team=kicking_team,
            receiving_team=receiving_team,
            kickoff_spot=self.KICKOFF_SPOT,
        )
        game_state.set_pending_kickoff(kickoff_setup)
        logger.debug(
            f"Set up half start kickoff: {kicking_team.name} kicking to {receiving_team.name}"
        )

    def is_game_over(self, game_state: "GameState") -> bool:
        """
        Determine if the game should end.

        The game ends when the game clock is expired (time_remaining <= 0) after
        the completion of the 4th quarter (current_quarter >= 4).

        Args:
            game_state: Current game state.

        Returns:
            True if the game should end, False otherwise.
        """
        # Game is over when the clock is expired after the 4th quarter
        is_over = (
            game_state.clock.is_expired() and game_state.clock.current_quarter >= 4
        )
        logger.debug(
            f"Is game over? {is_over}; is_expired-{game_state.clock.is_expired()}, "
            f"quarter-{game_state.clock.current_quarter}"
        )
        return is_over

    def is_half_over(self, game_state: "GameState") -> bool:
        """
        Determine if the current half should end.

        A half ends after 2 quarters are completed. This occurs when the quarter
        changes from 2 to 3 (end of 1st half) or from 4+ (end of 2nd half/game).

        Args:
            game_state: Current game state.

        Returns:
            True if the current half should end, False otherwise.
        """
        # Half is over when we complete 2 quarters (quarter 2) or end of game (quarter 4)
        # A quarter ends when time_remaining reaches 0 for that quarter
        quarter_length = game_state.clock.min_per_qtr * 60
        seconds_in_current_quarter = game_state.clock.seconds_elapsed % quarter_length

        # Half ends at end of quarter 2 or quarter 4
        return seconds_in_current_quarter == 0 and game_state.clock.current_quarter in [
            2,
            4,
        ]

    def is_drive_over(
        self, game_state: "GameState", drive_possession_team: "Team", play_count: int
    ) -> bool:
        """
        Determine if a drive should end.

        A drive ends when:
        - Possession has changed (turnover, turnover on downs, score)
        - A pending kickoff is set (after a score) and at least one play has been run
        - The half is over
        - The game is over

        Args:
            game_state: Current game state.
            drive_possession_team: The team that started the drive.
            play_count: Number of plays executed during this drive.

        Returns:
            True if the drive should end, False otherwise.
        """
        # A drive ends when:
        # 1. Possession changed (turnover, turnover on downs)
        # 2. There's a pending kickoff (after a score) AND we've run at least one play
        # 3. The half is over
        # 4. The game is over

        # Check if possession changed from when the drive started
        if game_state.pos_team != drive_possession_team:
            logger.debug(
                f"Drive ended due to possession change ({play_count} plays run)"
            )
            return True

        # Pending kickoff only ends drive if we've already run plays
        # (initial kickoff to start game/half doesn't end a drive)
        if game_state.has_pending_kickoff() and play_count > 0:
            logger.debug(f"Drive ended due to pending kickoff ({play_count} plays run)")
            return True

        if self.is_half_over(game_state):
            logger.debug(f"Drive ended due to half ending ({play_count} plays run)")
            return True

        if self.is_game_over(game_state):
            logger.debug(f"Drive ended due to game ending ({play_count} plays run)")
            return True

        return False

    def on_drive_end(
        self, game_state: "GameState", drive_record: "DriveRecord"
    ) -> None:
        """Handle the end of a drive."""
        # After a drive ends, the next team typically gets the ball
        # unless there was a score (then we need a kickoff)
        # This is called by the game engine to let rules decide what's next
        logger.debug(f"Drive ended for {game_state.pos_team.name}")

    def on_play_end(self, game_state: "GameState", play_record: "PlayRecord") -> None:
        """Handle the end of each play."""
        # Called after play is applied to game state
        # Used for any play-by-play rule checks
        logger.debug("Play completed")

    def handle_post_score_possession(
        self, game_state: "GameState", play_data: "PlayExecutionData"
    ) -> None:
        """Set up a kickoff after a score."""
        # After a score, the scoring team kicks off to the other team
        scoring_team = game_state.opponent(game_state.pos_team)
        receiving_team = game_state.pos_team

        kickoff_setup = KickoffSetup(
            kicking_team=scoring_team,
            receiving_team=receiving_team,
            kickoff_spot=self.KICKOFF_SPOT,
        )
        game_state.set_pending_kickoff(kickoff_setup)
        logger.debug(
            f"Set up post-score kickoff: {scoring_team.name} kicking to {receiving_team.name}"
        )

    def handle_touchback(
        self, game_state: "GameState", play_data: "PlayExecutionData"
    ) -> None:
        """Handle a touchback by placing the ball at the 25 yard line."""
        # In NFL, a touchback on a punt/kickoff results in ball at 25 yard line
        # The possession team (now defensive team) becomes the offensive team
        possession = game_state.possession

        # Ball is placed at the 25 yard line (receiving team's 25)
        possession.set_ball_position(self.KICKOFF_SPOT - 10)  # 35 - 10 = 25 yard line
        possession.reset_down_and_distance()

        logger.debug(f"Touchback: {possession.pos_team.name} ball at 25 yard line")

    def get_touchback_spot(self, is_kickoff: bool = False) -> int:
        """NFL touchback spot is the 25 yard line."""
        return (
            self.KICKOFF_TOUCHBACK_SPOT if is_kickoff else self.DEFAULT_TOUCHBACK_SPOT
        )

    def is_first_down(self, yards_gained: int, distance: int) -> bool:
        return self.first_down_rule.is_first_down(yards_gained, distance)

    def is_turnover_on_downs(
        self, current_down: int, yards_gained: int, distance: int
    ) -> bool:
        return self.first_down_rule.is_turnover_on_downs(
            current_down, yards_gained, distance
        )
