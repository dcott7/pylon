"""
Game simulation engines and orchestration.

Provides core simulation components including:
- GameEngine: Main game simulator
- SimulationRunner: Multi-replication orchestrator
- Specialized engines: Drive, Play, Pass, Run, Kickoff, Punt, FieldGoal

Note: Type stubs provided for IDE support. Lazy imports used at runtime
to avoid circular dependencies.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_engine import GameEngine
    from .simulation_runner import SimulationRunner
    from .drive_engine import DriveEngine
    from .play_engine import PlayEngine
    from .pass_engine import PassPlayEngine
    from .run_engine import RunPlayEngine
    from .kickoff_engine import KickoffPlayEngine
    from .punt_engine import PuntPlayEngine
    from .field_goal_engine import FieldGoalPlayEngine


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "GameEngine":
        from .game_engine import GameEngine

        return GameEngine
    elif name == "SimulationRunner":
        from .simulation_runner import SimulationRunner

        return SimulationRunner
    elif name == "DriveEngine":
        from .drive_engine import DriveEngine

        return DriveEngine
    elif name == "PlayEngine":
        from .play_engine import PlayEngine

        return PlayEngine
    elif name == "PassPlayEngine":
        from .pass_engine import PassPlayEngine

        return PassPlayEngine
    elif name == "RunPlayEngine":
        from .run_engine import RunPlayEngine

        return RunPlayEngine
    elif name == "KickoffPlayEngine":
        from .kickoff_engine import KickoffPlayEngine

        return KickoffPlayEngine
    elif name == "PuntPlayEngine":
        from .punt_engine import PuntPlayEngine

        return PuntPlayEngine
    elif name == "FieldGoalPlayEngine":
        from .field_goal_engine import FieldGoalPlayEngine

        return FieldGoalPlayEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GameEngine",
    "SimulationRunner",
    "DriveEngine",
    "PlayEngine",
    "PassPlayEngine",
    "RunPlayEngine",
    "KickoffPlayEngine",
    "PuntPlayEngine",
    "FieldGoalPlayEngine",
]
