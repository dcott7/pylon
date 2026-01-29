"""Authoritative game state: clock, possession, score, and pending specials.

GameState owns the single source of truth for in-game mutable state while engines
and models read/update it. It wires together the clock, scoreboard, possession,
pending kickoffs/extra points, and drive/play records.
"""

from __future__ import annotations
from enum import auto, Enum
import logging
from typing import TYPE_CHECKING, Optional, List
import uuid

from .game_clock import GameClock
from .possession_state import PossessionState
from .scoreboard_state import Scoreboard
from ..domain.team import Team
from ..domain.rules.base import KickoffSetup, ExtraPointSetup
from ..engine.timeout import TimeoutManager
from ..models.misc import CoinTossChoice
from .snapshot import ClockSnapshot, PossessionSnapshot, ScoreSnapshot
from .play_record import ScoringTypeEnum

if TYPE_CHECKING:
    from .drive_record import DriveRecord
    from .play_record import PlayRecord, PlayExecutionData
    from ..domain.rules.base import LeagueRules


logger = logging.getLogger(__name__)


class GameStateError(Exception):
    pass


class GameStateConsistencyError(GameStateError):
    pass


class GameStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()


class PlayOutcome:
    def __init__(self) -> None:
        self.scoring_type: Optional[ScoringTypeEnum] = None
        self.scoring_team: Optional[Team] = None
        self.possession_change: bool = False
        self.is_turnover: bool = False
        self.is_terminal: bool = False


# class PlayOutcomeType(Enum):
#     NO_SCORE = auto()
#     OFFENSIVE_TOUCHDOWN = auto()
#     DEFENSIVE_TOUCHDOWN = auto()
#     FIELD_GOAL = auto()
#     SAFETY = auto()
#     TURNOVER = auto()
#     PUNT = auto()


class GameSnapshot:
    def __init__(self, game_state: Optional["GameState"] = None) -> None:
        self.pos_team: Optional[Team] = game_state.pos_team if game_state else None
        self.def_team: Optional[Team] = game_state.def_team if game_state else None
        self.clock_snapshot: ClockSnapshot = (
            ClockSnapshot(game_state.clock) if game_state else ClockSnapshot(None)
        )
        self.possession_snapshot: PossessionSnapshot = (
            PossessionSnapshot(game_state.possession)
            if game_state
            else PossessionSnapshot(None)
        )
        self.scoreboard_snapshot: ScoreSnapshot = (
            ScoreSnapshot(
                game_state.scoreboard,
                game_state.pos_team,
                game_state.def_team,
            )
            if game_state
            else ScoreSnapshot(None, None, None)
        )

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        return (
            self.pos_team is not None
            and self.def_team is not None
            and self.clock_snapshot.is_finalized()
            and self.possession_snapshot.is_finalized()
            and self.scoreboard_snapshot.is_finalized()
        )


class GameExecutionData:
    def __init__(self) -> None:
        self._status: GameStatus = GameStatus.NOT_STARTED
        self._coin_toss_winner: Optional[Team] = None
        self._coin_toss_winner_choice: Optional[CoinTossChoice] = None
        self.drives: List["DriveRecord"] = []

    # ==============================
    # Setters
    # ==============================
    def set_status(self, status: GameStatus) -> None:
        self._status = status
        logger.debug(f"Set status to {status.name}")

    def set_coin_toss_winner(self, team: Team) -> None:
        self._coin_toss_winner = team
        logger.debug(f"Set coin_toss_winner to {team.name}")

    def set_coin_toss_winner_choice(self, choice: CoinTossChoice) -> None:
        self._coin_toss_winner_choice = choice
        logger.debug(f"Set coin_toss_winner_choice choice to {choice.name}")

    def add_drive(self, drive_record: "DriveRecord") -> None:
        if not drive_record.is_finalized():
            msg = "Attempted to add unfinalized DriveRecord to GameState."
            logger.error(msg)
            raise GameStateError(msg)

        # TODO: Ensure consistency between the current GameState and DriveRecord by
        # comparing the current state to the end state of the last drive / last play.
        # self._assert_consistency(drive_record, game_state)

        self.drives.append(drive_record)
        logger.debug(f"Drive {drive_record.uid} added to game state.")

    def start_game(self) -> None:
        if self.status != GameStatus.NOT_STARTED:
            logger.error("Attempted to start a game that has already started")
            raise GameStateError("Game already started")

        self.set_status(GameStatus.IN_PROGRESS)

    def end_game(self) -> None:
        if self.status != GameStatus.IN_PROGRESS:
            logger.error("Attempted to end a game that is not in progress")
            raise GameStateError("Game not in progress")

        self.set_status(GameStatus.COMPLETE)

    # ==============================
    # Getters
    # ==============================
    @property
    def status(self) -> GameStatus:
        return self._status

    @property
    def coin_toss_winner(self) -> Optional[Team]:
        return self._coin_toss_winner

    @property
    def coin_toss_winner_choice(self) -> Optional[CoinTossChoice]:
        return self._coin_toss_winner_choice

    @property
    def last_drive(self) -> Optional["DriveRecord"]:
        if not self.drives:
            logger.warning("No drives found in game state.")
            return None
        return self.drives[-1]

    # ==============================
    # Validators
    # ==============================
    def _assert_offdef_consistency(self, dr: DriveRecord, gs: GameState) -> None:
        if dr.end.pos_team != gs.possession.pos_team or dr.end.def_team != gs.opponent(
            gs.possession.pos_team
        ):
            return

        msg = (
            f"End possession ({dr.end.pos_team}) or defense team "
            f"({dr.end.def_team}) does not match game state."
        )
        logger.error(msg)
        raise GameStateConsistencyError(msg)

    def _assert_possession_consistency(self, dr: DriveRecord, gs: GameState) -> None:
        if dr.end.possession_snapshot == PossessionSnapshot(gs.possession):
            return

        msg = (
            f"End drive possession snapshot ({dr.end.possession_snapshot}) "
            f"does not match the game state ({PossessionSnapshot(gs.possession)})."
        )
        logger.error(msg)
        raise GameStateConsistencyError(msg)

    def _assert_clock_consistency(self, dr: DriveRecord, gs: GameState) -> None:
        if dr.end.clock_snapshot == ClockSnapshot(gs.clock):
            return

        msg = (
            f"End clock snapshot ({dr.end.clock_snapshot}) "
            f"does not match the game state ({ClockSnapshot(gs.clock)})."
        )
        logger.error(msg)
        raise GameStateConsistencyError(msg)

    def _assert_scoreboard_consistency(self, dr: DriveRecord, gs: GameState) -> None:
        if dr.end.scoreboard_snapshot == ScoreSnapshot(gs.scoreboard):
            return

        msg = (
            f"End scoreboard snapshot ({dr.end.scoreboard_snapshot}) "
            f"does not match the game state ({ScoreSnapshot(gs.scoreboard)})."
        )
        logger.error(msg)
        raise GameStateConsistencyError(msg)

    def _assert_consistency(
        self, drive_record: DriveRecord, game_state: GameState
    ) -> None:
        """Assert internal consistency between GameRecord and DriveRecord."""
        self._assert_offdef_consistency(drive_record, game_state)
        self._assert_possession_consistency(drive_record, game_state)
        self._assert_clock_consistency(drive_record, game_state)
        self._assert_scoreboard_consistency(drive_record, game_state)


class GameRecord:
    def __init__(self, start_game_state: GameState) -> None:
        self.uid: str = str(uuid.uuid4())
        self._start_snapshot: GameSnapshot = GameSnapshot(start_game_state)
        self._end_snapshot: GameSnapshot = GameSnapshot(None)

    # ==============================
    # Getters
    # ==============================
    @property
    def start(self) -> GameSnapshot:
        return self._start_snapshot

    @property
    def end(self) -> GameSnapshot:
        return self._end_snapshot

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        return self._start_snapshot.is_finalized() and self._end_snapshot.is_finalized()


class GameState:
    """
    Authoritative, mutable, live game state owned by the GameEngine.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        minutes_per_quarter: int,
        quarters_per_half: int,
        max_timeouts: int,
    ) -> None:
        self._home_team: Team = home_team
        self._away_team: Team = away_team
        self._seconds_elapsed: int = 0
        self._clock: GameClock = GameClock(
            lambda: self._seconds_elapsed, minutes_per_quarter, quarters_per_half * 2
        )
        self._scoreboard: Scoreboard = Scoreboard(home_team, away_team)
        self._timeout_mgr: TimeoutManager = TimeoutManager(
            home_team, away_team, max_timeouts
        )
        # default starting possession
        self._possession = PossessionState(
            pos_team=home_team,
            ball_position=35,  # kickoff yard line (TODO: this should be configurable)
            down=None,
            distance=None,
        )
        # Pending special plays (kickoffs, extra points)
        self._pending_kickoff: Optional[KickoffSetup] = None
        self._pending_extra_point: Optional[ExtraPointSetup] = None
        # Coin toss info
        self._coin_toss_winner: Optional[Team] = None
        self._coin_toss_winner_choice: Optional[CoinTossChoice] = None
        # Execution data (set by GameEngine)
        self._game_data: GameExecutionData = GameExecutionData()

    # ===============================
    # Getters
    # ===============================
    @property
    def seconds_elapsed(self) -> int:
        return self._seconds_elapsed

    @property
    def home_team(self) -> Team:
        return self._home_team

    @property
    def away_team(self) -> Team:
        return self._away_team

    @property
    def clock(self) -> GameClock:
        return self._clock

    @property
    def scoreboard(self) -> Scoreboard:
        return self._scoreboard

    @property
    def timeout_mgr(self) -> TimeoutManager:
        return self._timeout_mgr

    @property
    def possession(self) -> PossessionState:
        return self._possession

    @property
    def pos_team(self) -> Team:
        return self.possession.pos_team

    @property
    def def_team(self) -> Team:
        return self.opponent(self.possession.pos_team)

    @property
    def pending_kickoff(self) -> Optional[KickoffSetup]:
        return self._pending_kickoff

    @property
    def pending_extra_point(self) -> Optional[ExtraPointSetup]:
        return self._pending_extra_point

    @property
    def coin_toss_winner(self) -> Optional[Team]:
        return self._coin_toss_winner

    @property
    def coin_toss_winner_choice(self) -> Optional[CoinTossChoice]:
        return self._coin_toss_winner_choice

    @property
    def game_data(self) -> GameExecutionData:
        """Access to execution data (drives, game status, etc.)."""
        # Note: game_data is set externally by GameEngine after instantiation
        return self._game_data  # type: ignore

    @property
    def drives(self) -> List["DriveRecord"]:
        return self.game_data.drives

    def total_drives(self) -> int:
        return len(self.drives)

    def total_plays(self) -> int:
        return sum(len(drive.plays) for drive in self.drives)

    def total_yards(self) -> int:
        """Return total yards gained across all drives (offensive perspective)."""
        return sum(drive.total_yards() for drive in self.drives)

    def drives_by_team(self, team: Team) -> List["DriveRecord"]:
        """Return all drives where the given team was on offense."""
        return [d for d in self.drives if d.start.pos_team == team]

    def all_plays(self) -> List["PlayRecord"]:
        """Return a flattened list of all plays from all drives."""
        plays: List["PlayRecord"] = []
        for drive in self.drives:
            plays.extend(drive.plays)
        return plays

    # ===============================
    # Setters
    # ===============================
    def set_pending_kickoff(self, kickoff_setup: KickoffSetup) -> None:
        self._pending_kickoff = kickoff_setup
        logger.debug(
            f"Set pending kickoff: {kickoff_setup.kicking_team.name} kicking to {kickoff_setup.receiving_team.name}"
        )

    def set_pending_extra_point(self, extra_point_setup: ExtraPointSetup) -> None:
        self._pending_extra_point = extra_point_setup
        logger.debug(f"Set pending extra point at {extra_point_setup.spot}")

    def set_coin_toss_winner(self, team: Team) -> None:
        self._coin_toss_winner = team
        logger.debug(f"Set coin toss winner to {team.name}")

    def set_coin_toss_winner_choice(self, choice: CoinTossChoice) -> None:
        self._coin_toss_winner_choice = choice
        logger.debug(f"Set coin toss winner choice to {choice.name}")

    # ===============================
    # Pending Play Helpers
    # ===============================
    def has_pending_kickoff(self) -> bool:
        """Check if there is a pending kickoff."""
        return self._pending_kickoff is not None

    def has_pending_extra_point(self) -> bool:
        """Check if there is a pending extra point attempt."""
        return self._pending_extra_point is not None

    def consume_pending_kickoff(self) -> KickoffSetup:
        """Consume and return the pending kickoff setup, clearing it from state."""
        ko = self._pending_kickoff
        if ko is None:
            logger.error("Attempted to consume a kickoff when there is none pending.")
            raise GameStateError("No pending kickoff to consume.")

        self._pending_kickoff = None
        logger.debug("Consumed pending kickoff.")
        return ko

    def consume_pending_extra_point(self) -> ExtraPointSetup:
        """Consume and return the pending extra point setup, clearing it from state."""
        ep = self._pending_extra_point
        if ep is None:
            logger.error(
                "Attempted to consume an extra point when there is none pending."
            )
            raise GameStateError("No pending extra point to consume.")

        self._pending_extra_point = None
        logger.debug("Consumed pending extra point.")
        return ep

    # ===============================
    # Utility Methods
    # ===============================
    def opponent(self, team: Team) -> Team:
        if team == self._home_team:
            return self._away_team
        elif team == self._away_team:
            return self._home_team

        msg = f"Team {team.name} is not part of this game."
        logger.error(msg)
        raise GameStateError(msg)


class GameStateUpdater:
    """
    This is the ONLY class that is allowed to modify the GameState. It contains
    static methods that take a GameState and a PlayExecutionData and applies
    the results of the play to the GameState. It can ask the LeagueRules for
    any rule-specific logic needed to update the GameState.
    """

    # ==============================
    # Static Methods
    # ==============================
    @staticmethod
    def apply_play_data(
        game_state: GameState, play_data: PlayExecutionData, league_rules: LeagueRules
    ) -> None:
        """Apply the results of a play execution to the game state."""
        # For kickoffs and punts, down/distance may not be set yet (they're special teams plays)
        # They'll be set after possession change via reset_down_and_distance()
        has_play_call = play_data.off_play_call is not None
        if has_play_call:
            assert play_data.off_play_call is not None
            is_special_teams = play_data.off_play_call.play_type.is_kick()
            if not is_special_teams:
                game_state.possession.assert_down_and_distance_set()
        play_data.assert_is_finalized()

        GameStateUpdater._update_clock(game_state, play_data)

        if play_data.is_fg_attempt:
            GameStateUpdater._update_scoring(game_state, play_data, league_rules)
            return

        # Skip scoring for kickoffs/punts - they don't result in scores by themselves
        # (fumbles/returns to endzone would be handled differently)
        is_special_play = play_data.off_play_call is None
        if not is_special_play:
            # Update score if scoring occurred (only for regular plays)
            GameStateUpdater._update_scoring(game_state, play_data, league_rules)

        # Update possession state based on play result
        GameStateUpdater._update_possession(game_state, play_data, league_rules)

        logger.debug("Play updated the game state.")

    @staticmethod
    def _update_clock(game_state: GameState, play_data: PlayExecutionData) -> None:
        """Advance the game clock based on play execution data."""
        assert play_data.time_elapsed is not None
        assert play_data.preplay_clock_runoff is not None

        total_time_advance = play_data.time_elapsed + play_data.preplay_clock_runoff
        game_state._seconds_elapsed += total_time_advance  # type: ignore
        logger.debug(
            f"Advanced clock by {total_time_advance} seconds to {game_state.seconds_elapsed}. "
            f"Preplay runoff: {play_data.preplay_clock_runoff} seconds "
            f"Play elapsed time: {play_data.time_elapsed} seconds"
        )

    @staticmethod
    def _update_scoring(
        game_state: GameState, play_data: PlayExecutionData, league_rules: LeagueRules
    ) -> None:
        """Update the scoreboard based on play result."""
        # Handle field goal attempts
        if play_data.is_fg_attempt:
            play_data.assert_fg_good_set()
            if not play_data.fg_good:
                return

            fg_points = league_rules.get_scoring_value(ScoringTypeEnum.FIELD_GOAL)
            game_state._scoreboard.add_points(game_state.pos_team, fg_points)  # type: ignore
            logger.debug(
                f"Field goal good! {fg_points} points added to {game_state.pos_team.name}."
            )
            league_rules.handle_post_score_possession(game_state, play_data)
            return

        assert play_data.yards_gained is not None
        assert play_data.is_possession_change is not None

        possession = game_state.possession
        start_spot = possession.ball_position
        end_spot = start_spot + play_data.yards_gained

        scoring_team = None
        scoring_type = None

        # Check for touchdown
        if league_rules.is_touchdown(end_spot, play_data.is_possession_change):
            if not play_data.is_possession_change:
                # Offensive touchdown
                scoring_team = possession.pos_team
                scoring_type = ScoringTypeEnum.TOUCHDOWN
            else:
                # Defensive touchdown (return)
                scoring_team = game_state.opponent(possession.pos_team)
                scoring_type = ScoringTypeEnum.TOUCHDOWN

        # Check for safety
        elif league_rules.is_safety(end_spot, play_data.is_possession_change):
            # Defensive safety
            scoring_team = game_state.opponent(possession.pos_team)
            scoring_type = ScoringTypeEnum.SAFETY

        # Apply scoring if it occurred
        if scoring_team and scoring_type:
            points = league_rules.get_scoring_value(scoring_type)
            game_state._scoreboard.add_points(scoring_team, points)  # type: ignore
            logger.debug(
                f"{scoring_type.value}: {points} points added to {scoring_team.name}."
            )
            # Handle post-score possession
            league_rules.handle_post_score_possession(game_state, play_data)

    @staticmethod
    def _update_possession(
        game_state: GameState,
        play_data: PlayExecutionData,
        league_rules: LeagueRules,
    ) -> None:
        """Update possession state based on play result and league rules."""
        assert play_data.yards_gained is not None
        assert play_data.is_possession_change is not None
        assert play_data.is_turnover is not None

        possession = game_state.possession
        start_spot = possession.ball_position
        end_spot = start_spot + play_data.yards_gained

        # For kickoffs, off_play_call is None
        is_kick = (
            play_data.off_play_call is not None
            and play_data.off_play_call.play_type.is_kick()
        )

        # Check for touchback on kick plays
        if league_rules.is_touchback(end_spot, play_data.is_possession_change, is_kick):
            league_rules.handle_touchback(game_state, play_data)
            return

        # Check if turnover on downs occurred (only for regular plays with down/distance)
        is_turnover_on_downs = False
        if possession.down is not None and possession.distance is not None:
            is_turnover_on_downs = league_rules.is_turnover_on_downs(
                possession.down, play_data.yards_gained, possession.distance
            )

        # Possession change (turnover or turnover on downs)
        if play_data.is_possession_change or is_turnover_on_downs:
            possession.set_ball_position(end_spot)
            possession.set_pos_team(game_state.opponent(possession.pos_team))
            possession.flip_field()
            possession.reset_down_and_distance()
            logger.debug(f"Possession changed to {possession.pos_team.name}")
            # Don't log "First down achieved" on possession changes
            return

        # No possession change - update down and distance (regular plays only)
        if possession.down is None or possession.distance is None:
            # This shouldn't happen for regular plays, but handle it gracefully
            logger.warning(
                "Down/distance not set for non-possession-change play, resetting"
            )
            possession.reset_down_and_distance()
            return

        # Check for first down BEFORE advancing the ball
        # (advance_ball modifies distance, so we need original distance for comparison)
        if league_rules.is_first_down(play_data.yards_gained, possession.distance):
            possession.advance_ball(play_data.yards_gained)
            possession.reset_down_and_distance()
            logger.debug("First down achieved!")
        else:
            possession.advance_ball(play_data.yards_gained)
            possession._down += 1  # type: ignore
            logger.debug(
                f"Now {possession.down} down and {possession.distance} yards to go"
            )
