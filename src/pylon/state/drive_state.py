from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import logging
import uuid

from ..domain.team import Team
from ..domain.playbook import PlayTypeEnum
from ..domain.rules.base import ScoringTypeEnum

if TYPE_CHECKING:
    from .game_state import GameState
    from .play_state import PlayState, PlayFinalizationError


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


class DriveState:
    """
    Authoritative, mutable, live drive state owned by the DriveEngine.

    The DriveState tracks the overall progress and outcome of a drive,
    including start and end conditions, time elapsed, yards gained,
    scoring status, and offensive plays run.
    """

    def __init__(self, start_game_state: "GameState") -> None:
        self.uid: str = str(uuid.uuid4())

        self.status: DriveStatus = DriveStatus.IN_PROGRESS

        self.start_pos_team: Team = start_game_state.pos_team
        self.start_def_team: Team = start_game_state.def_team
        self.start_quarter: int = start_game_state.clock.current_quarter
        self.start_time: int = start_game_state.clock.time_remaining
        self.start_yardline: int = start_game_state.possession.ball_position
        self.start_pos_team_score: int = start_game_state.scoreboard.current_score(
            self.start_pos_team
        )
        self.start_def_team_score: int = start_game_state.scoreboard.current_score(
            self.start_def_team
        )

        self.end_pos_team: Optional[Team] = None
        self.end_def_team: Optional[Team] = None
        self.end_quarter: Optional[int] = None
        self.end_time: Optional[int] = None
        self.end_yardline: Optional[int] = None
        self.end_pos_team_score: Optional[int] = None
        self.end_def_team_score: Optional[int] = None

        self.time_elapsed: int = 0
        self.yards_gained: int = 0
        self.is_scoring_drive: bool = False
        self.scoring_type: ScoringTypeEnum = ScoringTypeEnum.NONE
        self.scoring_team: Optional[Team] = None
        self.result: Optional[DriveEndResult] = None

        self.last_play: Optional["PlayState"] = None
        self.plays: List["PlayState"] = []

    def add_play(self, play: "PlayState") -> None:
        if not play.is_finalized():
            msg = "Attempted to add unfinalized PlayState to DriveState."
            logger.error(msg)
            raise PlayFinalizationError(msg)

        self.last_play = play
        self.plays.append(play)

    def is_finalized(self) -> bool:
        return (
            self.end_pos_team is not None
            and self.end_quarter is not None
            and self.end_time is not None
            and self.end_yardline is not None
            and self.end_pos_team_score is not None
            and self.end_def_team_score is not None
            and self.result is not None
        )


class DriveStateUpdater:
    def __init__(self, drive_state: DriveState) -> None:
        self._ds = drive_state

    def apply_play(self, play_state: "PlayState", game_state: "GameState") -> None:
        self._update_clock(play_state)
        if play_state.is_possession_change:
            self._update_scoreboard(play_state)
        self._update_possession(play_state)
        self._update_result(play_state, game_state)

    def _update_possession(self, play_state: "PlayState") -> None:
        if self._ds.end_def_team is not None or self._ds.end_pos_team is not None:
            msg = (
                "Attempted to update possession state of already finalized DriveState."
            )
            logger.error(msg)
            raise DriveFinalizationError(msg)

        assert play_state.end_pos_team is not None
        assert play_state.end_def_team is not None

        self._ds.end_pos_team = play_state.end_pos_team
        self._ds.end_def_team = play_state.end_def_team

    def _update_clock(self, play_state: "PlayState") -> None:
        if self._ds.end_quarter is not None or self._ds.end_time is not None:
            msg = "Attempted to finalize time info of already finalized DriveState."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        assert play_state.end_quarter is not None
        assert play_state.end_time is not None

        self._ds.end_quarter = play_state.end_quarter
        self._ds.end_time = play_state.end_time
        self._ds.time_elapsed = self._ds.start_time - play_state.end_time

    def _update_scoreboard(self, play_state: "PlayState") -> None:
        if (
            self._ds.end_pos_team_score is not None
            or self._ds.end_def_team_score is not None
        ):
            msg = "Attempted to finalize scores of already finalized DriveState."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        self._ds.end_pos_team_score = play_state.end_pos_team_score
        self._ds.end_def_team_score = play_state.end_def_team_score
        self._ds.is_scoring_drive = play_state.is_scoring_play

    def _update_yardline(self, play_state: "PlayState") -> None:
        if self._ds.end_yardline is not None:
            msg = "Attempted to finalize yardline of already finalized DriveState."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        assert play_state.end_yardline is not None

        self._ds.end_yardline = play_state.end_yardline
        self._ds.yards_gained = self._ds.start_yardline - play_state.end_yardline

    def _update_result(self, play_state: "PlayState", game_state: "GameState") -> None:
        if self._ds.result is not None:
            msg = "Attempted to finalize result of already finalized DriveState."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        last_off_play_call = play_state.off_play_call
        if last_off_play_call is None:
            msg = "Cannot finalize DriveState result without offensive play call."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        if play_state.is_scoring_play:
            result = DriveEndResult.SCORE
        elif play_state.is_turnover:
            result = DriveEndResult.TURNOVER
        elif game_state.is_end_of_half():
            result = DriveEndResult.END_OF_HALF
        elif game_state.is_game_over():
            result = DriveEndResult.END_OF_GAME
        elif last_off_play_call.play_type == PlayTypeEnum.PUNT:
            result = DriveEndResult.PUNT
        elif last_off_play_call.play_type == PlayTypeEnum.FIELD_GOAL:
            result = DriveEndResult.FIELD_GOAL_ATTEMPT
        else:
            msg = "Cannot determine DriveEndResult from last play and game state."
            logger.error(msg)
            raise DriveFinalizationError(msg)

        self._ds.result = result
