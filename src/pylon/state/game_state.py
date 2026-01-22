from __future__ import annotations
from enum import auto, Enum
import logging
from typing import TYPE_CHECKING, Dict, Optional, List
import uuid

from .game_clock import GameClock
from .possession_state import PossessionState
from .scoreboard_state import Scoreboard
from ..domain.team import Team
from ..domain.rules.base import KickoffSetup, ExtraPointSetup
from ..engine.timeout import TimeoutManager
from ..models.misc import CoinTossChoice
from .snapshot import ClockSnapshot, PossessionSnapshot, ScoreSnapshot

if TYPE_CHECKING:
    from .drive_record import DriveRecord
    from .play_record import PlayRecord


logger = logging.getLogger(__name__)


class GameStateError(Exception):
    pass


class GameStateConsistencyError(GameStateError):
    pass


class GameStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()


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
    # Validation
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
        self._pending_kickoff: Optional[KickoffSetup] = None
        self._pending_extra_point: Optional[ExtraPointSetup] = None
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

    def set_pending_kickoff(self, kickoff_setup: KickoffSetup) -> None:
        self._pending_kickoff = kickoff_setup
        # TODO: Update possession state for kickoff accordingly to:
        # kickoff_setup.kicking_team, kickoff_setup.receiving_team and kickoff_setup.spot
        logger.debug(f"Set pending_kickoff to {kickoff_setup}")

    def set_pending_extra_point(self, extra_point_setup: ExtraPointSetup) -> None:
        self._pending_extra_point = extra_point_setup
        # TODO: Update possession state for extra point attempt accordingly to:
        # extra_point_setup.kicking_team and extra_point_setup.spot
        self._pending_extra_point = extra_point_setup
        logger.debug(f"Set pending_extra_point to {extra_point_setup}")

    def add_drive(self, drive_record: "DriveRecord") -> None:
        if not drive_record.is_finalized():
            msg = "Attempted to add unfinalized DriveRecord to GameState."
            logger.error(msg)
            raise GameStateError(msg)

        # Ensure consistency between GameExecutionData and DriveRecord by comparing
        # the current state to the end state of the last drive / last play.
        # self._assert_consistency()

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
    def pending_kickoff(self) -> Optional[KickoffSetup]:
        return self._pending_kickoff

    @property
    def pending_extra_point(self) -> Optional[ExtraPointSetup]:
        return self._pending_extra_point

    @property
    def last_drive(self) -> Optional["DriveRecord"]:
        if not self.drives:
            logger.warning("No drives found in game state.")
            return None
        return self.drives[-1]

    # ==============================

    # ==============================
    def consume_pending_kickoff(self) -> KickoffSetup:
        ko = self._pending_kickoff
        if ko is None:
            logger.error("Attempted to consume a kickoff when there is none pending.")
            raise GameStateError("No pending kickoff to consume.")

        self._pending_kickoff = None
        logger.debug("Consumed pending kickoff.")
        return ko

    def consume_pending_extra_point(self) -> ExtraPointSetup:
        ep = self._pending_extra_point
        if ep is None:
            logger.error(
                "Attempted to consume an extra point when there is none pending."
            )
            raise GameStateError("No pending extra point to consume.")

        self._pending_extra_point = None
        logger.debug("Consumed pending extra point.")
        return ep


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
    # Validation
    # ==============================
    def is_finalized(self) -> bool:
        return self._start_snapshot.is_finalized() and self._end_snapshot.is_finalized()


class GameRules:
    @staticmethod
    def is_game_over(game_state: GameState) -> bool:
        if game_state.clock.is_expired():
            logger.info("Game over: clock expired")
            return True
        # TODO: add overtime rules, mercy rule, etc.
        return False

    @staticmethod
    def is_end_of_half(game_state: GameState) -> bool:
        if (
            game_state.clock.current_quarter in [2, 4]
            and game_state.clock.time_remaining <= 0
        ):
            logger.info("End of half condition met")
            return True
        return False

    @staticmethod
    def is_drive_over(game_state: GameState) -> bool:
        if (
            GameRules.is_game_over(game_state)
            or GameRules.is_end_of_half(game_state)
            or game_state.last_play_was_scoring()
            or game_state.possession_changed()
            or game_state.last_play_was_kick()
        ):
            logger.info("Drive over condition met by GameRules")
            return True

        return False


class GameState:
    """
    Authoritative, mutable, live game state owned by the GameEngine.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        clock: GameClock,
        scoreboard: Scoreboard,
        timeout_mgr: TimeoutManager,
    ) -> None:
        self._home_team: Team = home_team
        self._away_team: Team = away_team
        self._clock: GameClock = clock
        self._scoreboard: Scoreboard = scoreboard
        self._timeout_mgr: TimeoutManager = timeout_mgr
        self.ot_possessions: Dict[str, int] = {
            self._home_team.uid: 0,
            self._away_team.uid: 0,
        }  # team uid -> number of OT possessions
        self.first_ot_possession_complete: bool = False
        # default starting possession
        self._possession = PossessionState(
            pos_team=home_team,
            ball_position=35,  # kickoff yard line (TODO: this should be configurable)
            down=1,
            distance=10,
        )

    # ===============================
    # Setters
    # ===============================
    def set_possession(self, team: Team) -> None:
        self._possession.set_possession(team)
        logger.debug(f"Possession set to team: {team.name}")

    # ===============================
    # Getters
    # ===============================
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

    # ===============================
    # Derived state queries
    # ===============================
    def opponent(self, team: Team) -> Team:
        if team == self._home_team:
            return self._away_team
        elif team == self._away_team:
            return self._home_team

        msg = f"Team {team.name} is not part of this game."
        logger.error(msg)
        raise GameStateError(msg)

    def leading_team(self) -> Team | None:
        return self._scoreboard.leader()

    def lead(self, team: Team) -> int:
        scores = self.scoreboard.score()
        teams = list(scores.keys())
        values = list(scores.values())

        if values[0] == values[1]:
            return 0

        if teams[0] == team:
            return values[0] - values[1]
        elif teams[1] == team:
            return values[1] - values[0]

        logger.error(f"Team {team} is not part of this game")
        raise GameStateError(f"Team {team} is not part of this game")

    def last_play_was_scoring(self) -> bool:
        if self.last_drive is None or self.last_drive.last_play is None:
            return False

        return self.last_drive.last_play.is_scoring_play

    def last_play_was_kick(self) -> bool:
        if self.last_drive is None or self.last_drive.last_play is None:
            return False

        return (
            self.last_drive.last_play.off_play_call is not None
            and self.last_drive.last_play.off_play_call.play_type.is_kick()
        )

    def possession_changed(self) -> bool:
        if self.last_drive is None or self.last_drive.last_play is None:
            return False

        return self.last_drive.last_play.is_possession_change

    # ===============================
    # Internal Consistency Checks
    # ===============================

    def _assert_consistency(self) -> None:
        """Assert internal consistency between GameState and DriveRecord/PlayRecord."""
        assert self.last_drive is not None
        ld = self.last_drive

        if ld.end_pos_team != self.possession.pos_team:
            msg = (
                f"End possession team {ld.end_pos_team} does not match current "
                f"possession team {self.possession.pos_team}."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_def_team != self.def_team:
            msg = (
                f"End defense team {ld.end_def_team} does not match current "
                f"defense team {self.def_team}."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_yardline != self.possession.ball_position:
            msg = (
                f"End yardline ({ld.end_yardline}) does not match current "
                f"ball position ({self.possession.ball_position})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_time != self.clock.time_remaining:
            msg = (
                f"End time ({ld.end_time}) does not match current clock "
                f"time ({self.clock.time_remaining})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_quarter != self.clock.current_quarter:
            msg = (
                f"End quarter ({ld.end_quarter}) does not match current "
                f"quarter ({self.clock.current_quarter})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_pos_team_score != self.scoreboard.current_score(
            self.possession.pos_team
        ):
            msg = (
                f"End possession team score ({ld.end_pos_team_score}) does not "
                f"match current score ({self.scoreboard.current_score(self.possession.pos_team)})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_def_team_score != self.scoreboard.current_score(self.def_team):
            msg = (
                f"End possession team score ({ld.end_pos_team_score}) does not "
                f"match current score ({self.scoreboard.current_score(self.possession.pos_team)})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)
