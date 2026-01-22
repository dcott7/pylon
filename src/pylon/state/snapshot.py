from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..domain.team import Team

if TYPE_CHECKING:
    from .game_clock import GameClock
    from .possession_state import PossessionState
    from .scoreboard_state import Scoreboard


class ClockSnapshot:
    """
    Snapshot of the game clock state at a specific moment in time. If
    clock is provided, capture the relevant attributes; otherwise, initialize
    all attributes to None.
    """

    def __init__(self, clock: Optional[GameClock] = None) -> None:
        self.clock_is_running = clock.clock_is_running if clock else None
        self.quarter = clock.current_quarter if clock else None
        self.time_remaining = clock.time_remaining if clock else None

    # ==============================
    # Validation
    # ==============================
    def is_finalized(self) -> bool:
        return (
            self.clock_is_running is not None
            and self.quarter is not None
            and self.time_remaining is not None
        )


class PossessionSnapshot:
    """
    Snapshot of the possession state at a specific moment in time. If
    possession_state is provided, capture the relevant attributes; otherwise, initialize
    all attributes to None.
    """

    def __init__(self, possession_state: Optional[PossessionState] = None) -> None:
        self.yardline = possession_state.ball_position if possession_state else None
        self.down = possession_state.down if possession_state else None
        self.distance = possession_state.distance if possession_state else None

    # ==============================
    # Validation
    # ==============================
    def is_finalized(self) -> bool:
        return (
            self.yardline is not None
            and self.down is not None
            and self.distance is not None
        )


class ScoreSnapshot:
    """
    Snapshot of the scoreboard state at a specific moment in time. If
    scoreboard is provided, capture the relevant attributes; otherwise, initialize
    all attributes to None.
    """

    def __init__(
        self,
        scoreboard: Optional[Scoreboard] = None,
        pos_team: Optional[Team] = None,
        def_team: Optional[Team] = None,
    ) -> None:
        self.pos_team_score = (
            scoreboard.current_score(pos_team) if scoreboard and pos_team else None
        )
        self.def_team_score = (
            scoreboard.current_score(def_team) if scoreboard and def_team else None
        )

    # ==============================
    # Validation
    # ==============================
    def is_finalized(self) -> bool:
        return self.pos_team_score is not None and self.def_team_score is not None
