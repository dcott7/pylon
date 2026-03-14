"""Core simulation protocols that are domain-agnostic.

This package is intentionally independent from ``pylon`` so it can support
football and non-football simulations alike.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from .rng import RNG


TResult = TypeVar("TResult", covariant=True)


@runtime_checkable
class Simulation(Protocol[TResult]):
    """Single-run simulation contract.

    A concrete simulation encapsulates one RNG-driven execution and returns a
    structured result object when run.
    """

    rng: RNG

    def run(self) -> TResult:
        """Execute the simulation once and return result data."""
        ...
