"""Play-level state, participants, and snapshots.

Defines play execution records, participant roles, scoring types, and snapshots of
game state before/after a play for downstream analysis and consistency checks.
"""

from __future__ import annotations
from enum import Enum
import logging
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional

from ..domain.team import Team
from ..domain.athlete import Athlete, AthletePositionEnum
from ..domain.playbook import PlayCall
from .snapshot import ClockSnapshot, PossessionSnapshot, ScoreSnapshot

if TYPE_CHECKING:
    from .game_state import GameState


logger = logging.getLogger(__name__)


class PlayRecordError(Exception):
    """Custom exception for errors during play execution."""

    pass


class PlayFinalizationError(PlayRecordError):
    pass


class ScoringTypeEnum(Enum):
    NONE = "none"
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    SAFETY = "safety"
    EXTRA_POINT_KICK = "extra_point_kick"
    EXTRA_POINT_TWO_POINT = "extra_point_two_point"


class PlayParticipantType(Enum):
    PASSER = "passer"
    RUSHER = "rusher"
    RECEIVER = "receiver"
    KICKER = "kicker"
    PUNTER = "punter"
    RETURNER = "returner"
    # ... add more participant types as needed ...


class PlaySnapshot:
    """
    Snapshot of the game state at a specific moment in time. If
    game_state is provided, capture the relevant attributes; otherwise, initialize
    all attributes to None.
    """

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


class PlayExecutionData:
    """
    Class to hold the execution-time data of a play. This includes the play calls,
    time elapsed, scoring information, yardage gained, and participant details. This
    information is filled in during the execution of the play and will be used to
    update the PlayRecord._end_snapshot. It is essential that this has enough
    information to fully describe the outcome of the play for later application to
    the GameEngine.
    """

    def __init__(self) -> None:
        self._off_play_call: Optional[PlayCall] = None
        self._def_play_call: Optional[PlayCall] = None
        self._time_elapsed: Optional[int] = None
        self._preplay_clock_runoff: Optional[int] = None
        self._is_clock_running: Optional[bool] = None
        self._yards_gained: Optional[int] = None
        self._is_fg_attempt: Optional[bool] = None
        self._fg_good: Optional[bool] = None
        self._is_possession_change: Optional[bool] = None
        self._is_turnover: Optional[bool] = None
        self._off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]] = {}
        self._def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]] = {}
        self._participants: Dict[str, PlayParticipantType] = {}

    # ==============================
    # Setters
    # ==============================
    def set_off_play_call(self, play_call: PlayCall) -> None:
        self._off_play_call = play_call
        logger.debug(f"Set off_play_call to {play_call}")

    def set_def_play_call(self, play_call: PlayCall) -> None:
        self._def_play_call = play_call
        logger.debug(f"Set def_play_call to {play_call}")

    def set_time_elapsed(self, time_elapsed: int) -> None:
        self._time_elapsed = time_elapsed
        logger.debug(f"Set time_elapsed to {time_elapsed}")

    def set_preplay_clock_runoff(self, preplay_clock_runoff: int) -> None:
        self._preplay_clock_runoff = preplay_clock_runoff
        logger.debug(f"Set preplay_clock_runoff to {preplay_clock_runoff}")

    def set_yards_gained(self, yards_gained: int) -> None:
        self._yards_gained = yards_gained
        logger.debug(f"Set yards_gained to {yards_gained}")

    def set_is_fg_attempt(self, is_fg_attempt: bool) -> None:
        self._is_fg_attempt = is_fg_attempt
        logger.debug(f"Set is_fg_attempt to {is_fg_attempt}")

    def set_fg_good(self, fg_good: bool) -> None:
        self._fg_good = fg_good
        logger.debug(f"Set fg_good to {fg_good}")

    def set_is_clock_running(self, is_clock_running: bool) -> None:
        self._is_clock_running = is_clock_running
        logger.debug(f"Set is_clock_running to {is_clock_running}")

    def set_is_possession_change(self, is_possession_change: bool) -> None:
        self._is_possession_change = is_possession_change
        logger.debug(f"Set is_possession_change to {is_possession_change}")

    def set_is_turnover(self, is_turnover: bool) -> None:
        self._is_turnover = is_turnover
        logger.debug(f"Set is_turnover to {is_turnover}")

    def set_off_personnel_assignments(
        self, off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]]
    ) -> None:
        self._off_personnel_assignments = off_personnel_assignments
        logger.debug(f"Set off_personnel_assignments to {off_personnel_assignments}")

    def set_def_personnel_assignments(
        self, def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]]
    ) -> None:
        self._def_personnel_assignments = def_personnel_assignments
        logger.debug(f"Set def_personnel_assignments to {def_personnel_assignments}")

    def add_participant(
        self, player_id: str, participant_type: PlayParticipantType
    ) -> None:
        self._participants[player_id] = participant_type
        logger.debug(f"Added participant {player_id} as {participant_type}")

    # ==============================
    # Getters
    # ==============================
    @property
    def off_play_call(self) -> Optional[PlayCall]:
        return self._off_play_call

    @property
    def def_play_call(self) -> Optional[PlayCall]:
        return self._def_play_call

    @property
    def time_elapsed(self) -> Optional[int]:
        return self._time_elapsed

    @property
    def preplay_clock_runoff(self) -> Optional[int]:
        return self._preplay_clock_runoff

    @property
    def yards_gained(self) -> Optional[int]:
        return self._yards_gained

    @property
    def is_fg_attempt(self) -> Optional[bool]:
        return self._is_fg_attempt

    @property
    def fg_good(self) -> Optional[bool]:
        return self._fg_good

    @property
    def is_clock_running(self) -> Optional[bool]:
        return self._is_clock_running

    @property
    def is_possession_change(self) -> Optional[bool]:
        return self._is_possession_change

    @property
    def is_turnover(self) -> Optional[bool]:
        return self._is_turnover

    @property
    def off_personnel_assignments(self) -> Dict[AthletePositionEnum, List[Athlete]]:
        return self._off_personnel_assignments

    @property
    def def_personnel_assignments(self) -> Dict[AthletePositionEnum, List[Athlete]]:
        return self._def_personnel_assignments

    @property
    def participants(self) -> Dict[str, PlayParticipantType]:
        return self._participants

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        # For special teams plays like kickoffs, play calls may be None
        # Check if this looks like a kickoff (no play calls but has possession change)
        is_special_play = (
            self.off_play_call is None
            and self.def_play_call is None
            and self.is_possession_change is True
        )

        if is_special_play:
            # For special plays, we just need the basic fields
            return (
                self.time_elapsed is not None
                and self.preplay_clock_runoff is not None
                and self.yards_gained is not None
                and self.is_clock_running is not None
                and self.is_possession_change is not None
                and self.is_turnover is not None
            )

        # For regular plays, we need play calls too
        return (
            self.off_play_call is not None
            and self.def_play_call is not None
            and self.time_elapsed is not None
            and self.preplay_clock_runoff is not None
            and self.yards_gained is not None
            and self.is_clock_running is not None
            and self.is_possession_change is not None
            and self.is_turnover is not None
        )

    def assert_is_finalized(self) -> None:
        """Check that all necessary components are set to finalize the play."""
        if self.is_finalized():
            return

        # Debug output to show which fields are missing
        missing: List[str] = []
        if self.off_play_call is None:
            missing.append("off_play_call")
        if self.def_play_call is None:
            missing.append("def_play_call")
        if self.time_elapsed is None:
            missing.append("time_elapsed")
        if self.preplay_clock_runoff is None:
            missing.append("preplay_clock_runoff")
        if self.yards_gained is None:
            missing.append("yards_gained")
        if self.is_clock_running is None:
            missing.append("is_clock_running")
        if self.is_possession_change is None:
            missing.append("is_possession_change")
        if self.is_turnover is None:
            missing.append("is_turnover")

        msg = f"PlayExecutionData is not finalized. Missing required fields: {', '.join(missing)}"
        logger.error(msg)
        raise PlayFinalizationError(msg)

    def assert_fg_good_set(self) -> None:
        """Check that fg_good is set if the play is a field goal attempt."""
        if self.fg_good is not None:
            return
        msg = "fg_good must be set for a field goal attempt."
        logger.error(msg)
        raise PlayRecordError(msg)

    def assert_is_ready_to_execute(self) -> None:
        """Check that all necessary components are set to execute the play."""
        if self.off_play_call is None:
            msg = "Offensive play call must be set before executing play."
            raise PlayRecordError(msg)

        if self.def_play_call is None:
            msg = "Defensive play call must be set before executing play."
            raise PlayRecordError(msg)

        if not self.off_personnel_assignments:
            msg = "Offensive personnel assignments must be set before executing play."
            raise PlayRecordError(msg)

        if not self.def_personnel_assignments:
            msg = "Defensive personnel assignments must be set before executing play."
            raise PlayRecordError(msg)


class PlayRecord:
    """
    Class to track the state of a play during its execution. This class
    captures the starting conditions, play calls, personnel assignments,
    and the resulting state after the play is executed. This class should
    NOT modify the game state directly; instead, it serves as a record
    of what happened during the play for later application to the game state.
    """

    def __init__(self, start_game_state: GameState) -> None:
        self.uid: str = str(uuid.uuid4())
        self._start_snapshot = PlaySnapshot(start_game_state)
        # this will be filled in later during finalization
        self._end_snapshot = PlaySnapshot(None)
        # Execution data (play calls, personnel, outcomes, participants)
        self._execution_data: PlayExecutionData = PlayExecutionData()

    # ==============================
    # Setters
    # ==============================
    def set_execution_data(self, execution_data: PlayExecutionData) -> None:
        self._execution_data = execution_data
        logger.debug(f"Set execution data for PlayRecord {self.uid}")

    # ==============================
    # Getters
    # ==============================
    @property
    def start(self) -> PlaySnapshot:
        return self._start_snapshot

    @property
    def end(self) -> PlaySnapshot:
        return self._end_snapshot

    @property
    def execution_data(self) -> PlayExecutionData:
        """Access execution data directly."""
        return self._execution_data

    @property
    def off_play_call(self) -> Optional[PlayCall]:
        return self._execution_data.off_play_call

    @property
    def def_play_call(self) -> Optional[PlayCall]:
        return self._execution_data.def_play_call

    @property
    def yards_gained(self) -> Optional[int]:
        return self._execution_data.yards_gained

    @property
    def time_elapsed(self) -> Optional[int]:
        return self._execution_data.time_elapsed

    @property
    def preplay_clock_runoff(self) -> Optional[int]:
        return self._execution_data.preplay_clock_runoff

    @property
    def is_fg_attempt(self) -> Optional[bool]:
        return self._execution_data.is_fg_attempt

    @property
    def fg_good(self) -> Optional[bool]:
        return self._execution_data.fg_good

    @property
    def is_clock_running(self) -> Optional[bool]:
        return self._execution_data.is_clock_running

    @property
    def is_possession_change(self) -> Optional[bool]:
        return self._execution_data.is_possession_change

    @property
    def is_turnover(self) -> Optional[bool]:
        return self._execution_data.is_turnover

    @property
    def off_personnel_assignments(self) -> Dict[AthletePositionEnum, List[Athlete]]:
        return self._execution_data.off_personnel_assignments

    @property
    def def_personnel_assignments(self) -> Dict[AthletePositionEnum, List[Athlete]]:
        return self._execution_data.def_personnel_assignments

    @property
    def participants(self) -> Dict[str, PlayParticipantType]:
        """Return participant roles (passer, rusher, receiver, etc.)."""
        return self._execution_data.participants

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        return self._start_snapshot.is_finalized() and self._end_snapshot.is_finalized()

    def set_end_state(self, end_game_state: GameState) -> None:
        if self.is_finalized():
            msg = "Cannot set end state on a finalized PlayRecord."
            logger.error(msg)
            raise PlayFinalizationError(msg)

        self._end_snapshot = PlaySnapshot(end_game_state)
