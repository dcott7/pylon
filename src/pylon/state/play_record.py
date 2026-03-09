"""Play-level state, participants, and snapshots.

Defines play execution records, participant roles, scoring types, and snapshots of
game state before/after a play for downstream analysis and consistency checks.
"""

from __future__ import annotations
from enum import Enum
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from ..domain.team import Team
from ..domain.athlete import Athlete, AthletePositionEnum
from ..domain.playbook import PlayCall, PlayTypeEnum
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
    TACKLER = "tackler"
    INTERCEPTOR = "interceptor"
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
        self._play_type: Optional[PlayTypeEnum] = None
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

        # Pass-specific metrics
        self._air_yards: Optional[int] = None
        self._yards_after_catch: Optional[int] = None
        self._is_complete: Optional[bool] = None
        self._is_interception: Optional[bool] = None
        self._is_sack: Optional[bool] = None

        # Run-specific metrics
        self._run_gap: Optional[str] = None  # "A", "B", "C", etc.
        self._is_fumble: Optional[bool] = None
        self._fumble_recovered_by_team: Optional[Team] = None

        # Penalty information
        self._penalty_occurred: Optional[bool] = None
        self._penalty_yards: Optional[int] = None
        self._penalty_team: Optional[Team] = None
        self._penalty_type: Optional[str] = None

    # ==============================
    # Setters
    # ==============================
    def set_play_type(self, play_type: PlayTypeEnum) -> None:
        self._play_type = play_type
        logger.debug(f"Set play_type to {play_type}")

    def set_off_play_call(self, play_call: Optional[PlayCall]) -> None:
        self._off_play_call = play_call
        logger.debug(f"Set off_play_call to {play_call}")

    def set_def_play_call(self, play_call: Optional[PlayCall]) -> None:
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

    def set_air_yards(self, air_yards: int) -> None:
        self._air_yards = air_yards
        logger.debug(f"Set air_yards to {air_yards}")

    def set_yards_after_catch(self, yac: int) -> None:
        self._yards_after_catch = yac
        logger.debug(f"Set yards_after_catch to {yac}")

    def set_is_complete(self, is_complete: bool) -> None:
        self._is_complete = is_complete
        logger.debug(f"Set is_complete to {is_complete}")

    def set_is_interception(self, is_interception: bool) -> None:
        self._is_interception = is_interception
        logger.debug(f"Set is_interception to {is_interception}")

    def set_is_sack(self, is_sack: bool) -> None:
        self._is_sack = is_sack
        logger.debug(f"Set is_sack to {is_sack}")

    def set_run_gap(self, run_gap: str) -> None:
        self._run_gap = run_gap
        logger.debug(f"Set run_gap to {run_gap}")

    def set_is_fumble(self, is_fumble: bool) -> None:
        self._is_fumble = is_fumble
        logger.debug(f"Set is_fumble to {is_fumble}")

    def set_fumble_recovered_by_team(self, team: Team) -> None:
        self._fumble_recovered_by_team = team
        logger.debug(f"Set fumble_recovered_by_team to {team}")

    def set_penalty_occurred(self, penalty_occurred: bool) -> None:
        self._penalty_occurred = penalty_occurred
        logger.debug(f"Set penalty_occurred to {penalty_occurred}")

    def set_penalty_yards(self, penalty_yards: int) -> None:
        self._penalty_yards = penalty_yards
        logger.debug(f"Set penalty_yards to {penalty_yards}")

    def set_penalty_team(self, team: Team) -> None:
        self._penalty_team = team
        logger.debug(f"Set penalty_team to {team}")

    def set_penalty_type(self, penalty_type: str) -> None:
        self._penalty_type = penalty_type
        logger.debug(f"Set penalty_type to {penalty_type}")

    # ==============================
    # Getters
    # ==============================
    @property
    def play_type(self) -> Optional[PlayTypeEnum]:
        return self._play_type

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

    @property
    def air_yards(self) -> Optional[int]:
        return self._air_yards

    @property
    def yards_after_catch(self) -> Optional[int]:
        return self._yards_after_catch

    @property
    def is_complete(self) -> Optional[bool]:
        return self._is_complete

    @property
    def is_interception(self) -> Optional[bool]:
        return self._is_interception

    @property
    def is_sack(self) -> Optional[bool]:
        return self._is_sack

    @property
    def run_gap(self) -> Optional[str]:
        return self._run_gap

    @property
    def is_fumble(self) -> Optional[bool]:
        return self._is_fumble

    @property
    def fumble_recovered_by_team(self) -> Optional[Team]:
        return self._fumble_recovered_by_team

    @property
    def penalty_occurred(self) -> Optional[bool]:
        return self._penalty_occurred

    @property
    def penalty_yards(self) -> Optional[int]:
        return self._penalty_yards

    @property
    def penalty_team(self) -> Optional[Team]:
        return self._penalty_team

    @property
    def penalty_type(self) -> Optional[str]:
        return self._penalty_type

    # ==============================
    # Validators
    # ==============================
    def is_finalized(self) -> bool:
        if self.play_type is None:
            return False

        is_o_special_play = self.play_type.is_special_teams()

        # Base required fields for all plays
        base_complete = (
            self.time_elapsed is not None
            and self.preplay_clock_runoff is not None
            and self.yards_gained is not None
            and self.is_clock_running is not None
            and self.is_possession_change is not None
            and self.is_turnover is not None
        )

        if not base_complete:
            return False

        # Special plays just need the basic fields
        if is_o_special_play:
            return True

        # Pass plays must have pass-specific analytics
        if self.play_type.is_pass():
            return (
                self.air_yards is not None
                and self.yards_after_catch is not None
                and self.is_complete is not None
                and self.is_interception is not None
                and self.is_sack is not None
            )

        # Run plays must have run-specific analytics (fumble status at minimum)
        if self.play_type.is_run():
            return self.is_fumble is not None and self.run_gap is not None

        # Other play types just need base fields
        return True

    def assert_is_finalized(self) -> None:
        """Check that all necessary components are set to finalize the play."""
        if self.is_finalized():
            return

        # Debug output to show which fields are missing
        missing: List[str] = []
        if self.play_type is None:
            missing.append("play_type")
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

        # Check play-type specific fields if we have a play call
        if self.play_type is not None:
            if self.play_type.is_pass():
                if self.air_yards is None:
                    missing.append("air_yards")
                if self.yards_after_catch is None:
                    missing.append("yards_after_catch")
                if self.is_complete is None:
                    missing.append("is_complete")
                if self.is_interception is None:
                    missing.append("is_interception")
                if self.is_sack is None:
                    missing.append("is_sack")
            elif self.play_type.is_run():
                if self.is_fumble is None:
                    missing.append("is_fumble")
                if self.run_gap is None:
                    missing.append("run_gap")

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
        if self.play_type is None:
            msg = "Play type must be set before executing play."
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

    def __init__(self, start_game_state: GameState, play_number: int) -> None:
        # Use the provided play_number which accounts for:
        # - All plays from completed drives (game_state.total_plays())
        # - Plus plays from the current in-progress drive
        # - Plus 1 for this new play being created
        self.uid: str = str(play_number)
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

    @property
    def air_yards(self) -> Optional[int]:
        return self._execution_data.air_yards

    @property
    def yards_after_catch(self) -> Optional[int]:
        return self._execution_data.yards_after_catch

    @property
    def is_complete(self) -> Optional[bool]:
        return self._execution_data.is_complete

    @property
    def is_interception(self) -> Optional[bool]:
        return self._execution_data.is_interception

    @property
    def is_sack(self) -> Optional[bool]:
        return self._execution_data.is_sack

    @property
    def run_gap(self) -> Optional[str]:
        return self._execution_data.run_gap

    @property
    def is_fumble(self) -> Optional[bool]:
        return self._execution_data.is_fumble

    @property
    def fumble_recovered_by_team(self) -> Optional[Team]:
        return self._execution_data.fumble_recovered_by_team

    @property
    def penalty_occurred(self) -> Optional[bool]:
        return self._execution_data.penalty_occurred

    @property
    def penalty_yards(self) -> Optional[int]:
        return self._execution_data.penalty_yards

    @property
    def penalty_team(self) -> Optional[Team]:
        return self._execution_data.penalty_team

    @property
    def penalty_type(self) -> Optional[str]:
        return self._execution_data.penalty_type

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
