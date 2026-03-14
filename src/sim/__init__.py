"""Domain-agnostic simulation abstraction package."""

from .base import Simulation
from .exceptions import (
    OutputSinkError,
    SimulationConfigurationError,
    SimulationError,
    SimulationExecutionError,
)
from .factory import SimulationFactory
from .observer import SimulationObserver
from .output import OutputSink, SimulationOutput
from .rng import RNG
from .runner import SimulationRunner, SimulationRunnerConfig

__all__ = [
    "Simulation",
    "SimulationOutput",
    "SimulationFactory",
    "SimulationObserver",
    "OutputSink",
    "RNG",
    "SimulationError",
    "SimulationConfigurationError",
    "SimulationExecutionError",
    "OutputSinkError",
    "SimulationRunner",
    "SimulationRunnerConfig",
]
