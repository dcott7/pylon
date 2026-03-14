"""Lifecycle observer interfaces for simulation runner orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from .output import SimulationOutput

if TYPE_CHECKING:
    from .runner import SimulationRunnerConfig


TResult = TypeVar("TResult")
TAggregate = TypeVar("TAggregate")


class SimulationObserver(Protocol, Generic[TResult, TAggregate]):
    """Observer hooks emitted by SimulationRunner lifecycle events."""

    def on_run_start(self, config: SimulationRunnerConfig) -> None:
        """Called once before the first replication."""
        ...

    def on_replication_start(self, rep_number: int, seed: int) -> None:
        """Called before a replication executes."""
        ...

    def on_replication_success(
        self,
        rep_number: int,
        seed: int,
        duration_seconds: float,
        result: TResult,
    ) -> None:
        """Called when a replication completes successfully."""
        ...

    def on_replication_failure(
        self, rep_number: int, seed: int, error: Exception
    ) -> None:
        """Called when a replication raises an error."""
        ...

    def on_run_complete(self, output: SimulationOutput[TResult, TAggregate]) -> None:
        """Called once after all replications complete."""
        ...
