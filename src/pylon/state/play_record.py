from __future__ import annotations
from enum import Enum
import logging
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional

from ..domain.team import Team
from ..domain.athlete import Athlete, AthletePositionEnum
from ..domain.playbook import PlayCall
from ..domain.rules.base import ScoringTypeEnum
from .snapshot import ClockSnapshot, PossessionSnapshot, ScoreSnapshot

if TYPE_CHECKING:
    from .game_state import GameState


logger = logging.getLogger(__name__)


class PlayRecordError(Exception):
    """Custom exception for errors during play execution."""

    pass


class PlayFinalizationError(PlayRecordError):
    pass


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


class PlayExecutionData:
    """
    Class to hold the execution-time data of a play. This includes the play calls,
    time elapsed, scoring information, yardage gained, and participant details. This
    information is filled in during the execution of the play and will be used to
    update the PlayRecord._end_snapshot.
    """

    def __init__(self) -> None:
        self._off_play_call: Optional[PlayCall] = None
        self._def_play_call: Optional[PlayCall] = None
        self._time_elapsed: Optional[int] = None
        self._is_scoring_play: Optional[bool] = None
        self._scoring_type: ScoringTypeEnum = ScoringTypeEnum.NONE
        self._scoring_team: Optional[Team] = None  # this will remain None if no score
        self._preplay_clock_runoff: Optional[int] = None
        self._yards_gained: Optional[int] = None
        self._is_clock_running: Optional[bool] = None
        self._is_turnover: Optional[bool] = None
        self._is_possession_change: Optional[bool] = None

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

    def set_is_scoring_play(self, is_scoring_play: bool) -> None:
        self._is_scoring_play = is_scoring_play
        logger.debug(f"Set is_scoring_play to {is_scoring_play}")

    def set_scoring_type(self, scoring_type: ScoringTypeEnum) -> None:
        self._scoring_type = scoring_type
        logger.debug(f"Set scoring_type to {scoring_type}")

    def set_scoring_team(self, scoring_team: Team) -> None:
        self._scoring_team = scoring_team
        logger.debug(f"Set scoring_team to {scoring_team}")

    def set_preplay_clock_runoff(self, preplay_clock_runoff: int) -> None:
        self._preplay_clock_runoff = preplay_clock_runoff
        logger.debug(f"Set preplay_clock_runoff to {preplay_clock_runoff}")

    def set_yards_gained(self, yards_gained: int) -> None:
        self._yards_gained = yards_gained
        logger.debug(f"Set yards_gained to {yards_gained}")

    def set_is_clock_running(self, is_clock_running: bool) -> None:
        self._is_clock_running = is_clock_running
        logger.debug(f"Set is_clock_running to {is_clock_running}")

    def set_is_turnover(self, is_turnover: bool) -> None:
        self._is_turnover = is_turnover
        logger.debug(f"Set is_turnover to {is_turnover}")

    def set_is_possession_change(self, is_possession_change: bool) -> None:
        self._is_possession_change = is_possession_change
        logger.debug(f"Set is_possession_change to {is_possession_change}")

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
    def is_scoring_play(self) -> Optional[bool]:
        return self._is_scoring_play

    @property
    def scoring_type(self) -> ScoringTypeEnum:
        return self._scoring_type

    @property
    def scoring_team(self) -> Optional[Team]:
        return self._scoring_team

    @property
    def preplay_clock_runoff(self) -> Optional[int]:
        return self._preplay_clock_runoff

    @property
    def yards_gained(self) -> Optional[int]:
        return self._yards_gained

    @property
    def is_clock_running(self) -> Optional[bool]:
        return self._is_clock_running

    @property
    def is_turnover(self) -> Optional[bool]:
        return self._is_turnover

    @property
    def is_possession_change(self) -> Optional[bool]:
        return self._is_possession_change

    @property
    def off_personnel_assignments(self) -> Dict[AthletePositionEnum, List[Athlete]]:
        return self._off_personnel_assignments

    @property
    def def_personnel_assignments(self) -> Dict[AthletePositionEnum, List[Athlete]]:
        return self._def_personnel_assignments

    # ==============================
    # Validation
    # ==============================
    def is_finalized(self) -> bool:
        return (
            self.off_play_call is not None
            and self.def_play_call is not None
            and self.time_elapsed is not None
            and self.is_scoring_play is not None
            and self.preplay_clock_runoff is not None
            and self.yards_gained is not None
            and self.is_clock_running is not None
            and self.is_turnover is not None
            and self.is_possession_change is not None
        )

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

    # ==============================
    # Getters
    # ==============================
    @property
    def start(self) -> PlaySnapshot:
        return self._start_snapshot

    @property
    def end(self) -> PlaySnapshot:
        return self._end_snapshot

    # ==============================
    # Validation
    # ==============================
    def is_finalized(self) -> bool:
        return self._start_snapshot.is_finalized() and self._end_snapshot.is_finalized()

    # ==============================
    # Finalization
    # ==============================
    def finalize(self, play_execution_data: PlayExecutionData) -> None:
        """Set the end state of the play based on the game state after play execution."""
        ...
        self._end_snapshot.pos_team
        self._end_snapshot.def_team
        self._end_snapshot.clock_snapshot.clock_is_running
        self._end_snapshot.clock_snapshot.quarter
        self._end_snapshot.clock_snapshot.time_remaining
        self._end_snapshot.possession_snapshot.yardline
        self._end_snapshot.possession_snapshot.down
        self._end_snapshot.possession_snapshot.distance
        self._end_snapshot.scoreboard_snapshot.pos_team_score
        self._end_snapshot.scoreboard_snapshot.def_team_score

    def _finalize_possession(self) -> None: ...

    # def _finalize_possession(self) -> None:
    #     """Set the end possession teams based on turnovers."""
    #     if self.end_def_team is not None or self.end_pos_team is not None:
    #         msg = "End state of play has already been finalized."
    #         logger.error(msg)
    #         raise PlayFinalizationError(msg)

    #     if self.is_turnover:
    #         if not self.is_possession_change:
    #             logger.warning(
    #                 "Play marked as turnover but possession change not indicated. "
    #                 "Assuming possession change."
    #             )
    #             self.is_possession_change = True

    #     if self.is_possession_change:
    #         self.end_pos_team = self.start_def_team
    #         self.end_def_team = self.start_pos_team
    #     else:
    #         self.end_pos_team = self.start_pos_team
    #         self.end_def_team = self.start_def_team

    # def _finalize_yardline_down_distance(self) -> None:
    #     """Set the end yardline, down, and distance after play execution."""

    #     if (
    #         self.end_yardline is not None
    #         or self.end_down is not None
    #         or self.end_distance is not None
    #     ):
    #         msg = "End yardline, down, or distance of play has already been finalized."
    #         logger.error(msg)
    #         raise PlayFinalizationError(msg)

    #     end_yardline = self.start_yardline - self.yards_gained
    #     if end_yardline < 0:
    #         logger.warning(
    #             "End yardline calculated below 0, clamping to 0 (opponent endzone)."
    #         )
    #         end_yardline = 0

    #     if self.is_possession_change:
    #         # New possession always starts 1st & 10. This does not need
    #         # to be configurable as it is standard across all football rulesets.
    #         end_down = 1
    #         end_distance = 10

    #     else:
    #         first_down_gained = self.yards_gained >= self.start_distance

    #         if first_down_gained:
    #             end_down = 1
    #             end_distance = 10
    #         else:
    #             end_down = self.start_down + 1
    #             end_distance = max(self.start_distance - self.yards_gained, 0)

    #             if end_down > 4:
    #                 logger.info("Turnover on downs occurred.")
    #                 self.is_turnover = True
    #                 self.is_possession_change = True
    #                 end_down = 1
    #                 end_distance = 10

    #     self.end_yardline = end_yardline
    #     self.end_down = end_down
    #     self.end_distance = end_distance

    # def _finalize_clock(self) -> None:
    #     """Set the end quarter and time based on time elapsed during play."""
    #     if (
    #         self.end_quarter is not None
    #         or self.end_time is not None
    #         or self.end_is_clock_running is not None
    #     ):
    #         msg = "End clock state already finalized."
    #         logger.error(msg)
    #         raise PlayFinalizationError(msg)

    #     end_quarter, end_time = self._start_clock.project(
    #         self.preplay_clock_runoff + self.time_elapsed
    #     )

    #     self.end_quarter = end_quarter
    #     self.end_time = end_time
    #     self.end_is_clock_running = self.is_clock_running

    # def _finalize_score(self) -> None:
    #     # When this method is called the possession and yardline must be finalized
    #     if (
    #         self.is_scoring_play
    #         or self.scoring_team is not None
    #         or self.scoring_type != ScoringTypeEnum.NONE
    #     ):
    #         if not self.end_snapshot.is_finalized():
    #             msg = "Cannot finalize scoring without end scores set."
    #             logger.error(msg)
    #             raise PlayFinalizationError(msg)
    #         return  # Score already finalized

    #     if self.end_yardline == 0 and not self.is_possession_change:
    #         self.is_scoring_play = True
    #         self.scoring_type = ScoringTypeEnum.TOUCHDOWN
    #         self.scoring_team = self.start_pos_team

    #     elif self.end_yardline == 100 and self.is_possession_change:
    #         self.is_scoring_play = True
    #         self.scoring_type = ScoringTypeEnum.TOUCHDOWN
    #         self.scoring_team = self.start_def_team

    #     # Safety
    #     elif self.end_yardline == 100 and not self.is_possession_change:
    #         self.is_scoring_play = True
    #         self.scoring_type = ScoringTypeEnum.SAFETY
    #         self.scoring_team = self.start_def_team

    # def finalize(self) -> None:
    #     """Set the end state of the play based on the game state after play execution."""

    #     self._finalize_yardline_down_distance()
    #     self._finalize_possession()
    #     self._finalize_clock()
    #     self._finalize_score()

    #     if not self.is_finalized():
    #         msg = "Play state finalization incomplete."
    #         logger.error(msg)
    #         raise PlayFinalizationError(msg)
