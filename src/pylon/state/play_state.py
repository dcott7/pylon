from __future__ import annotations
from enum import Enum
import logging
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional

from ..domain.team import Team
from ..domain.athlete import Athlete, AthletePositionEnum
from ..domain.playbook import PlayCall
from ..domain.rules.base import ScoringTypeEnum

if TYPE_CHECKING:
    from .game_state import GameState


logger = logging.getLogger(__name__)


class PlayStateError(Exception):
    """Custom exception for errors during play execution."""

    pass


class PlayFinalizationError(PlayStateError):
    pass


class PlayParticipantType(Enum):
    PASSER = "passer"
    RUSHER = "rusher"
    RECEIVER = "receiver"
    KICKER = "kicker"
    PUNTER = "punter"
    RETURNER = "returner"
    # ... add more participant types as needed ...


class PlayState:
    """
    Class to track the state of a play during its execution. This class
    captures the starting conditions, play calls, personnel assignments,
    and the resulting state after the play is executed. This class should
    NOT modify the game state directly; instead, it serves as a record
    of what happened during the play for later application to the game state.
    """

    def __init__(self, start_game_state: "GameState") -> None:
        # TODO: add penalty tracking (type and accepted/declined)
        self.uid: str = str(uuid.uuid4())

        # used to cast integer clock time to quarter and time remaining
        self._start_clock = start_game_state.clock

        self.off_play_call: Optional[PlayCall] = None
        self.def_play_call: Optional[PlayCall] = None

        self.start_pos_team: Team = start_game_state.pos_team
        self.start_def_team: Team = start_game_state.def_team
        self.start_is_clock_running: bool = start_game_state.clock.clock_is_running
        self.start_quarter: int = start_game_state.clock.current_quarter
        self.start_time: int = start_game_state.clock.time_remaining
        self.start_yardline: int = start_game_state.possession.ball_position
        self.start_distance: int = start_game_state.possession.distance
        self.start_down: int = start_game_state.possession.down
        self.start_pos_team_score: int = start_game_state.scoreboard.current_score(
            self.start_pos_team
        )
        self.start_def_team_score: int = start_game_state.scoreboard.current_score(
            self.start_def_team
        )

        # attributes to be set during play execution
        self.time_elapsed: int = 0
        self.is_scoring_play: bool = False
        self.scoring_type: ScoringTypeEnum = ScoringTypeEnum.NONE
        self.scoring_team: Optional[Team] = None
        self.preplay_clock_runoff: int = 0
        self.yards_gained: int = 0
        self.is_clock_running: bool = True
        self.is_turnover: bool = False
        self.is_possession_change: bool = False
        self.off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]] = {}
        self.def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]] = {}
        self.participants: Dict[str, PlayParticipantType] = {}

        # attributes to be set AFTER the end of the play
        self.end_pos_team: Optional[Team] = None
        self.end_def_team: Optional[Team] = None
        self.end_is_clock_running: Optional[bool] = None
        self.end_quarter: Optional[int] = None
        self.end_time: Optional[int] = None
        self.end_yardline: Optional[int] = None
        self.end_down: Optional[int] = None
        self.end_distance: Optional[int] = None
        self.end_pos_team_score: Optional[int] = None
        self.end_def_team_score: Optional[int] = None

    def add_participant(
        self, player_id: str, participant_type: PlayParticipantType
    ) -> None:
        self.participants[player_id] = participant_type

    def is_finalized(self) -> bool:
        return (
            self.end_pos_team is not None
            and self.end_def_team is not None
            and self.end_quarter is not None
            and self.end_time is not None
            and self.end_yardline is not None
            and self.end_down is not None
            and self.end_distance is not None
        )

    def is_finalized_for_scoring(self) -> bool:
        return (
            self.end_pos_team_score is not None and self.end_def_team_score is not None
        )

    def check_ready_to_execute(self) -> None:
        """Check that all necessary components are set to execute the play."""
        if self.off_play_call is None:
            raise PlayStateError(
                "Offensive play call must be set before executing play."
            )

        if self.def_play_call is None:
            raise PlayStateError(
                "Defensive play call must be set before executing play."
            )

        if not self.off_personnel_assignments:
            raise PlayStateError(
                "Offensive personnel assignments must be set before executing play."
            )

        if not self.def_personnel_assignments:
            raise PlayStateError(
                "Defensive personnel assignments must be set before executing play."
            )

    def _finalize_possession(self) -> None:
        """Set the end possession teams based on turnovers."""
        if self.end_def_team is not None or self.end_pos_team is not None:
            msg = "End state of play has already been finalized."
            logger.error(msg)
            raise PlayFinalizationError(msg)

        if self.is_turnover:
            if not self.is_possession_change:
                logger.warning(
                    "Play marked as turnover but possession change not indicated. "
                    "Assuming possession change."
                )
                self.is_possession_change = True

        if self.is_possession_change:
            self.end_pos_team = self.start_def_team
            self.end_def_team = self.start_pos_team
        else:
            self.end_pos_team = self.start_pos_team
            self.end_def_team = self.start_def_team

    def _finalize_yardline_down_distance(self) -> None:
        """Set the end yardline, down, and distance after play execution."""

        if (
            self.end_yardline is not None
            or self.end_down is not None
            or self.end_distance is not None
        ):
            msg = "End yardline, down, or distance of play has already been finalized."
            logger.error(msg)
            raise PlayFinalizationError(msg)

        end_yardline = self.start_yardline - self.yards_gained
        if end_yardline < 0:
            logger.warning(
                "End yardline calculated below 0, clamping to 0 (opponent endzone)."
            )
            end_yardline = 0

        if self.is_possession_change:
            # New possession always starts 1st & 10. This does not need
            # to be configurable as it is standard across all football rulesets.
            end_down = 1
            end_distance = 10

        else:
            first_down_gained = self.yards_gained >= self.start_distance

            if first_down_gained:
                end_down = 1
                end_distance = 10
            else:
                end_down = self.start_down + 1
                end_distance = max(self.start_distance - self.yards_gained, 0)

                if end_down > 4:
                    logger.info("Turnover on downs occurred.")
                    self.is_turnover = True
                    self.is_possession_change = True
                    end_down = 1
                    end_distance = 10

        self.end_yardline = end_yardline
        self.end_down = end_down
        self.end_distance = end_distance

    def _finalize_clock(self) -> None:
        """Set the end quarter and time based on time elapsed during play."""
        if (
            self.end_quarter is not None
            or self.end_time is not None
            or self.end_is_clock_running is not None
        ):
            msg = "End clock state already finalized."
            logger.error(msg)
            raise PlayFinalizationError(msg)

        end_quarter, end_time = self._start_clock.project(
            self.preplay_clock_runoff + self.time_elapsed
        )

        self.end_quarter = end_quarter
        self.end_time = end_time
        self.end_is_clock_running = self.is_clock_running

    def _finalize_score(self) -> None:
        # When this method is called the possession and yardline must be finalized
        if (
            self.is_scoring_play
            or self.scoring_team is not None
            or self.scoring_type != ScoringTypeEnum.NONE
        ):
            if not self.is_finalized_for_scoring():
                msg = "Cannot finalize scoring without end scores set."
                logger.error(msg)
                raise PlayFinalizationError(msg)
            return  # Score already finalized

        if self.end_yardline == 0 and not self.is_possession_change:
            self.is_scoring_play = True
            self.scoring_type = ScoringTypeEnum.TOUCHDOWN
            self.scoring_team = self.start_pos_team

        elif self.end_yardline == 100 and self.is_possession_change:
            self.is_scoring_play = True
            self.scoring_type = ScoringTypeEnum.TOUCHDOWN
            self.scoring_team = self.start_def_team

        # Safety
        elif self.end_yardline == 100 and not self.is_possession_change:
            self.is_scoring_play = True
            self.scoring_type = ScoringTypeEnum.SAFETY
            self.scoring_team = self.start_def_team

    def finalize(self) -> None:
        """Set the end state of the play based on the game state after play execution."""

        self._finalize_yardline_down_distance()
        self._finalize_possession()
        self._finalize_clock()
        self._finalize_score()

        if not self.is_finalized():
            msg = "Play state finalization incomplete."
            logger.error(msg)
            raise PlayFinalizationError(msg)
