"""Domain-agnostic simulation runner.

This runner knows how to execute N replications with deterministic seed
progression while delegating domain behavior to user-provided callables.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Callable, Generic, List, Sequence, TypeVar

from .base import Simulation
from .exceptions import (
    OutputSinkError,
    SimulationConfigurationError,
    SimulationExecutionError,
)
from .output import OutputSink, SimulationOutput
from .rng import RNG


logger = logging.getLogger(__name__)


TResult = TypeVar("TResult")
TAggregate = TypeVar("TAggregate")


@dataclass(frozen=True)
class SimulationRunnerConfig:
    """Configuration for batch simulation execution."""

    num_reps: int
    base_seed: int = 42
    schema_version: str = "1.0"


class SimulationRunner(Generic[TResult, TAggregate]):
    """Execute seeded replications for any simulation implementation."""

    def __init__(
        self,
        config: SimulationRunnerConfig,
        simulation_factory: Callable[[int, RNG], Simulation[TResult]],
        aggregate_fn: Callable[[List[TResult]], TAggregate],
        sinks: Sequence[OutputSink[SimulationOutput[TResult, TAggregate]]]
        | None = None,
    ) -> None:
        if config.num_reps < 1:
            raise SimulationConfigurationError("num_reps must be greater than 0")

        self.config = config
        self.simulation_factory = simulation_factory
        self.aggregate_fn = aggregate_fn
        self.sinks = list(sinks) if sinks is not None else []

    def run(self) -> SimulationOutput[TResult, TAggregate]:
        """Run all configured replications and return canonical output."""
        logger.info(
            "Starting simulation batch: reps=%s base_seed=%s sinks=%s",
            self.config.num_reps,
            self.config.base_seed,
            len(self.sinks),
        )
        started_at = time.time()
        run_results: List[TResult] = []

        # Run each replication with a deterministic seed progression
        # (base_seed + rep_number) to ensure reproducibility and independence
        # across runs
        for rep_number in range(1, self.config.num_reps + 1):
            seed = self.config.base_seed + rep_number
            run_results.append(self._run_single(rep_number=rep_number, seed=seed))

        elapsed_time = time.time() - started_at
        avg_per_rep = (
            elapsed_time / self.config.num_reps if self.config.num_reps else 0.0
        )
        logger.info(
            "Simulation batch complete in %.3fs (avg %.3fs/rep)",
            elapsed_time,
            avg_per_rep,
        )

        aggregate = self.aggregate_fn(run_results)

        # Create canonical output object with run results and aggregate summaries
        output = SimulationOutput(
            schema_version=self.config.schema_version,
            num_reps=self.config.num_reps,
            base_seed=self.config.base_seed,
            elapsed_time=elapsed_time,
            runs=run_results,
            aggregate=aggregate,
        )

        # Emit output to all configured sinks (DB, JSON, etc.)
        self._emit_to_sinks(output)

        return output

    def _run_single(self, rep_number: int, seed: int) -> TResult:
        """Run one replication with an explicit seed."""
        logger.debug("Running replication %s with seed=%s", rep_number, seed)
        rep_start = time.time()

        try:
            rng = RNG(seed)
            simulation = self.simulation_factory(rep_number, rng)
            result = simulation.run()
        except Exception as exc:
            logger.exception("Replication %s failed with seed=%s", rep_number, seed)
            raise SimulationExecutionError(
                f"Replication {rep_number} failed for seed={seed}"
            ) from exc

        rep_elapsed = time.time() - rep_start
        logger.debug("Replication %s complete in %.3fs", rep_number, rep_elapsed)
        return result

    def _emit_to_sinks(self, output: SimulationOutput[TResult, TAggregate]) -> None:
        """Helper to emit output to all configured sinks."""
        for sink in self.sinks:
            sink_name = sink.__class__.__name__
            logger.debug("Writing simulation output to sink=%s", sink_name)
            sink_start = time.time()
            try:
                sink.write(output)
            except Exception as exc:
                logger.exception(
                    "Failed writing simulation output to sink=%s", sink_name
                )
                raise OutputSinkError(
                    f"Failed writing simulation output to sink={sink_name}"
                ) from exc
            sink_elapsed = time.time() - sink_start
            logger.debug(
                "Wrote simulation output to sink=%s in %.3fs",
                sink_name,
                sink_elapsed,
            )
