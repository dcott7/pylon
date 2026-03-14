"""Factory protocol for creating per-replication simulation instances."""

from __future__ import annotations

from typing import Protocol, TypeVar

from .base import Simulation
from .rng import RNG


TResult = TypeVar("TResult", covariant=True)


class SimulationFactory(Protocol[TResult]):
    """Callable contract for building simulations for each replication."""

    def __call__(self, rep_number: int, rng: RNG) -> Simulation[TResult]:
        """Create a simulation instance for a replication."""
        ...
