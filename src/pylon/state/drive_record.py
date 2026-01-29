"""Drive-level state and snapshots used during simulation.

Captures drive execution metadata (status, elapsed time, yards, scoring info) and
provides snapshots of clock, possession, and scoreboard at drive boundaries.
"""

from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import logging
import uuid

from ..domain.team import Team
from .snapshot import ClockSnapshot, PossessionSnapshot, ScoreSnapshot
from .play_record import PlayRecord, PlayFinalizationError, ScoringTypeEnum

if TYPE_CHECKING:
    from .game_state import GameState


logger = logging.getLogger(__name__)


class DriveFinalizationError(Exception):
    pass


class DriveEndResult(Enum):
    SCORE = "score"
    TURNOVER = "turnover"  # e.g., downs, interception, fumble lost (not scored)
    PUNT = "punt"  # punt occured (not scored)
    FIELD_GOAL_ATTEMPT = "field_goal_attempt"  # field goal attempt (not scored)
    END_OF_HALF = "end_of_half"  # end of quarter/half/game
    END_OF_GAME = "end_of_game"  # end of game


class DriveStatus(Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


class DriveSnapshot:
    def __init__(self, game_state: Optional[GameState] = None) -> None:
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


class DriveExecutionData:
    def __init__(self) -> None:
        self._status: DriveStatus = DriveStatus.IN_PROGRESS
        self._time_elapsed: int = 0
        self._yards_gained: int = 0
        self._is_scoring_drive: bool = False
        self._scoring_type: ScoringTypeEnum = ScoringTypeEnum.NONE
        self._scoring_team: Optional[Team] = None
        self._result: Optional[DriveEndResult] = None
        # TODO: We need to update this because PlayRecord does not
        # contain all of the information like personnel used, offensive
        # and defensive formations, etc. This data is contained in the
        # PlayExecutionData class.
        self._plays: List[PlayRecord] = []

    # ==============================
    # Setters
    # ==============================
    def set_status(self, status: DriveStatus) -> None:
        self._status = status
        logger.debug(f"Set status to {status.name}")

    def set_time_elapsed(self, time_elapsed: int) -> None:
        self._time_elapsed = time_elapsed
        logger.debug(f"Set time_elapsed to {time_elapsed}")

    def set_yards_gained(self, yards_gained: int) -> None:
        self._yards_gained = yards_gained
        logger.debug(f"Set yards_gained to {yards_gained}")

    def set_is_scoring_drive(self, is_scoring_drive: bool) -> None:
        self._is_scoring_drive = is_scoring_drive
        logger.debug(f"Set is_scoring_drive to {is_scoring_drive}")

    def set_scoring_type(self, scoring_type: ScoringTypeEnum) -> None:
        self._scoring_type = scoring_type
        logger.debug(f"Set scoring_type to {scoring_type.name}")

    def set_scoring_team(self, scoring_team: Team) -> None:
        self._scoring_team = scoring_team
        logger.debug(f"Set scoring_team to {scoring_team.name}")

    def set_result(self, result: DriveEndResult) -> None:
        self._result = result
        logger.debug(f"Set result to {result.name}")

    def add_play(self, play: "PlayRecord") -> None:
        if not play.is_finalized():
            msg = "Attempted to add unfinalized PlayRecord to DriveRecord."
            logger.error(msg)
            raise PlayFinalizationError(msg)

        # TODO: Create and then call an _assert_consistency method here. This should
        # ensure/assert consistency between GameState and DriveRecord by comparing the
        # current game state to the end state of the last drive.
        # self._assert_consistency()  # raise if inconsistent
        self._plays.append(play)
        logger.debug(f"Added PlayRecord {play.uid} to DriveRecord.")

    # ==============================
    # Getters
    # ==============================
    @property
    def status(self) -> DriveStatus:
        return self._status

    @property
    def time_elapsed(self) -> int:
        return self._time_elapsed

    @property
    def yards_gained(self) -> int:
        return self._yards_gained

    @property
    def is_scoring_drive(self) -> bool:
        return self._is_scoring_drive

    @property
    def scoring_type(self) -> ScoringTypeEnum:
        return self._scoring_type

    @property
    def scoring_team(self) -> Optional[Team]:
        return self._scoring_team

    @property
    def result(self) -> Optional[DriveEndResult]:
        return self._result

    @property
    def plays(self) -> List[PlayRecord]:
        return self._plays

    @property
    def last_play(self) -> Optional[PlayRecord]:
        if len(self._plays) == 0:
            logger.warning("No plays in DriveRecord; last_play is None.")
            return None
        return self._plays[-1]

    def total_plays(self) -> int:
        return len(self._plays)

    def total_yards(self) -> int:
        return sum(p.yards_gained for p in self._plays if p.yards_gained is not None)

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        return (
            self.status == DriveStatus.COMPLETED
            and self.result is not None
            and len(self.plays) > 0  # at least one play
        )


class DriveRecord:
    def __init__(self, start_game_state: GameState) -> None:
        self.uid: str = str(uuid.uuid4())
        # initialize start snapshot from provided game state
        self._start_snapshot = DriveSnapshot(start_game_state)
        # this will be filled in later during finalization
        self._end_snapshot = DriveSnapshot(None)
        # Execution data (plays, stats, results)
        self._execution_data: DriveExecutionData = DriveExecutionData()

    # ==============================
    # Getters
    # ==============================
    @property
    def start(self) -> DriveSnapshot:
        return self._start_snapshot

    @property
    def end(self) -> DriveSnapshot:
        return self._end_snapshot

    @property
    def execution_data(self) -> DriveExecutionData:
        return self._execution_data

    @property
    def plays(self) -> List[PlayRecord]:
        """Access plays through execution data."""
        return self._execution_data.plays

    @property
    def last_play(self) -> Optional[PlayRecord]:
        """Access last play through execution data."""
        return self._execution_data.last_play

    def add_play(self, play: PlayRecord) -> None:
        """Add a finalized play to this drive."""
        self._execution_data.add_play(play)

    def total_plays(self) -> int:
        """Return number of plays in this drive."""
        return self._execution_data.total_plays()

    def total_yards(self) -> int:
        """Return total yards gained on all plays in this drive."""
        return self._execution_data.total_yards()

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        return self._start_snapshot.is_finalized() and self._end_snapshot.is_finalized()

    def set_end_state(self, end_game_state: GameState) -> None:
        if self.is_finalized():
            msg = "Cannot set end state on a finalized DriveRecord."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        self._end_snapshot = DriveSnapshot(end_game_state)
