"""Shared output models for domain-agnostic simulation runners."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, Sequence, TypeVar, runtime_checkable


TRunResult = TypeVar("TRunResult")
TAggregate = TypeVar("TAggregate")
TOutput = TypeVar("TOutput", contravariant=True)


@dataclass(frozen=True)
class SimulationOutput(Generic[TRunResult, TAggregate]):
    """Canonical batch output for repeated simulation runs."""

    schema_version: str
    num_reps: int
    base_seed: int
    elapsed_time: float
    runs: Sequence[TRunResult]
    aggregate: TAggregate


@runtime_checkable
class OutputSink(Protocol[TOutput]):
    """Pluggable output sink for simulation outputs (json/db/xml/etc.)."""

    def write(self, output: TOutput) -> None:
        """Persist or emit the given output payload."""
        ...
