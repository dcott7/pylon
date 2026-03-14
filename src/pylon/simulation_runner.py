"""
Simulation orchestration for running multiple game replications.

Provides the SimulationRunner class for executing batches of game simulations
with varying seeds and model configurations, supporting statistical analysis
and model comparison experiments.
"""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from sim.base import Simulation
from sim.factory import SimulationFactory
from sim.observer import SimulationObserver
from sim.runner import SimulationRunner
from sim.runner import SimulationRunnerConfig
from sim.rng import RNG
from .domain.team import Team
from .domain.rules.base import LeagueRules
from .domain.rules.nfl import NFLRules
from .models.registry import TypedModel
from .db.database import DatabaseManager
from .state.game_state import GameState
from .simulation import PylonSimulation, PylonSimulationResult
from .output import (
    DBOutputWriter,
    ExperimentOutputPayload,
    JsonOutputWriter,
    OutputMode,
    SimulationOutputPayload,
    TeamOutputPayload,
    serialize_team,
    validate_output_config,
    wants_db_output,
    wants_json_output,
)
from .output.serializers import serialize_game_state
from .output.types import GameStateOutputPayload, SimulationResultsPayload


logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class PylonSimulationRunnerConfig(SimulationRunnerConfig):
    """Pylon-specific runner configuration built on generic simulation config."""

    home_team: Team
    away_team: Team
    user_models: List[TypedModel[Any, Any]] | None = None
    rules: LeagueRules = field(default_factory=NFLRules)
    max_drives: int | None = None
    db_manager: DatabaseManager | None = None
    output_mode: OutputMode = OutputMode.JSON
    json_output_path: Path | str | None = None
    experiment_name: str | None = None
    experiment_description: str | None = None
    log_dir: Path | str | None = None
    log_level: int = logging.INFO


class _PerReplicationLogObserver(
    SimulationObserver[PylonSimulationResult, Dict[str, Any]]
):
    """Observer that writes one log file per replication."""

    def __init__(self, log_dir: Path, log_level: int) -> None:
        self._log_dir = log_dir
        self._log_level = log_level
        self._active_handlers: Dict[int, tuple[logging.FileHandler, int]] = {}

    def on_run_start(self, config: SimulationRunnerConfig) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def on_replication_start(self, rep_number: int, seed: int) -> None:
        rep_log_path = self._log_dir / f"pylon.{rep_number}.log"
        rep_handler = logging.FileHandler(rep_log_path, mode="w")
        rep_handler.setLevel(self._log_level)
        rep_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        root_logger = logging.getLogger()
        previous_level = root_logger.level
        root_logger.addHandler(rep_handler)
        root_logger.setLevel(min(previous_level, self._log_level))
        self._active_handlers[rep_number] = (rep_handler, previous_level)

    def on_replication_success(
        self,
        rep_number: int,
        seed: int,
        duration_seconds: float,
        result: PylonSimulationResult,
    ) -> None:
        self._teardown_replication_logger(rep_number)

    def on_replication_failure(
        self, rep_number: int, seed: int, error: Exception
    ) -> None:
        self._teardown_replication_logger(rep_number)

    def on_run_complete(self, output: object) -> None:
        for rep_number in list(self._active_handlers.keys()):
            self._teardown_replication_logger(rep_number)

    def _teardown_replication_logger(self, rep_number: int) -> None:
        logger_state = self._active_handlers.pop(rep_number, None)
        if logger_state is None:
            return

        rep_handler, previous_level = logger_state
        root_logger = logging.getLogger()
        root_logger.removeHandler(rep_handler)
        rep_handler.close()
        root_logger.setLevel(previous_level)


class PylonSimulationRunner:
    """
    Orchestrates multiple game simulation replications for statistical analysis.

    Manages:
    - Running multiple GameEngine instances with varied seeds
    - Tracking experiment metadata and results
    - Writing simulation output to JSON, DB, or both
    - Collecting aggregate statistics across reps

    Usage:
        runner = PylonSimulationRunner(
            config=PylonSimulationRunnerConfig(
            home_team=bears,
            away_team=niners,
            num_reps=100,
            base_seed=42,
            db_manager=db,
            output_mode=OutputMode.BOTH,
            ),
        )
        results = runner.run()
    """

    def __init__(self, config: PylonSimulationRunnerConfig) -> None:
        """
        Initialize the SimulationRunner.

        Args:
            config: Pylon-specific runner configuration.
        """
        self.home_team = config.home_team
        self.away_team = config.away_team
        self.num_reps = config.num_reps
        self.base_seed = config.base_seed
        self.schema_version = config.schema_version
        self.user_models = config.user_models
        self.rules = config.rules
        self.max_drives = config.max_drives
        self.db_manager = config.db_manager
        self.output_mode = config.output_mode
        self.log_dir = (
            Path(config.log_dir) if config.log_dir is not None else Path("./log")
        )
        self.json_output_path = (
            Path(config.json_output_path)
            if config.json_output_path is not None
            else self.log_dir / "simulation_results.json"
        )
        self.json_writer = JsonOutputWriter(self.json_output_path)
        self.log_level = config.log_level

        # Experiment metadata
        self.experiment_id = str(uuid.uuid4())
        self.experiment_name = (
            config.experiment_name
            or f"{self.home_team.name} vs {self.away_team.name} - {self.num_reps} reps"
        )
        self.experiment_description = config.experiment_description

        self.db_writer = (
            DBOutputWriter(db_manager=self.db_manager)
            if self.db_manager is not None
            else None
        )

        # Result tracking
        self.game_results: List[Dict[str, Any]] = []
        self.game_details: List[GameStateOutputPayload] = []
        self._pending_db_games: List[tuple[str, Dict[str, Any], GameState]] = []
        self._next_db_game_id: int | None = None

    def run(self) -> SimulationOutputPayload:
        """
        Execute all replications and return aggregated results.

        Returns:
            Dictionary with experiment metadata and aggregate statistics:
            - experiment_id: Experiment UUID
            - num_reps: Number of reps executed
            - games: List of per-game results
            - aggregate: Summary statistics (win counts, avg scores, etc.)
        """
        logger.info(
            f"Starting experiment: {self.experiment_name} ({self.num_reps} reps, base_seed={self.base_seed})"
        )

        # Ensure output configuration is valid based on the OutputMode
        validate_output_config(
            output_mode=self.output_mode,
            has_db_manager=self.db_manager is not None,
            json_output_path=self.json_output_path,
        )

        # Initialize DB game-id sequence for this run if DB output is requested.
        if wants_db_output(self.output_mode):
            self._next_db_game_id = int(self._get_next_game_id())

        # Reset per-run mutable state in case the runner instance is reused.
        self.game_results = []
        self.game_details = []
        self._pending_db_games = []

        rep_logger_observer = _PerReplicationLogObserver(
            log_dir=self.log_dir,
            log_level=self.log_level,
        )
        simulation_factory: SimulationFactory[PylonSimulationResult] = (
            self._simulation_factory
        )

        # Use the generic SimulationRunner to execute all replications with the
        # provided simulation factory and aggregate function.
        base_runner = SimulationRunner[PylonSimulationResult, Dict[str, Any]](
            config=SimulationRunnerConfig(
                num_reps=self.num_reps,
                base_seed=self.base_seed,
                schema_version=self.schema_version,
            ),
            simulation_factory=simulation_factory,
            aggregate_fn=self._aggregate_from_simulation_runs,
            observers=[rep_logger_observer],
        )
        base_output = base_runner.run()

        elapsed_time = base_output.elapsed_time
        logger.info(
            f"Experiment complete: {self.num_reps} reps in {elapsed_time:.2f}s "
            f"({elapsed_time / self.num_reps:.2f}s per game)"
        )

        aggregate_stats = base_output.aggregate

        results = self._build_output_payload(
            elapsed_time=elapsed_time,
            aggregate_stats=aggregate_stats,
        )

        if wants_json_output(self.output_mode):
            json_path = self.json_writer.write_results(results)
            logger.info(f"Results written to JSON: {json_path}")

        if wants_db_output(self.output_mode):
            self._persist_db_output(results)
            logger.info("Results persisted to database.")

        return results

    def _simulation_factory(
        self,
        rep_number: int,
        rng: RNG,
    ) -> Simulation[PylonSimulationResult]:
        """Create one per-rep pylon simulation for the generic sim runner."""
        if wants_db_output(self.output_mode):
            assert self._next_db_game_id is not None
            game_id = str(self._next_db_game_id)
            self._next_db_game_id += 1
        else:
            game_id = str(rep_number)

        logger.info(f"Running rep {rep_number}/{self.num_reps} (seed={rng.seed})...")
        simulation = PylonSimulation(
            home_team=self.home_team,
            away_team=self.away_team,
            game_id=game_id,
            rng=rng,
            user_models=self.user_models,
            rules=self.rules,
            max_drives=self.max_drives,
        )
        return simulation

    def _aggregate_from_simulation_runs(
        self,
        run_results: List[PylonSimulationResult],
    ) -> Dict[str, Any]:
        """Build pylon-specific game outputs and aggregate stats from sim runs."""
        self.game_results = []
        self.game_details = []
        self._pending_db_games = []

        for rep_number, run_result in enumerate(run_results, start=1):
            game_result: Dict[str, Any] = {
                "rep_number": rep_number,
                "seed": run_result.seed,
                "home_score": run_result.home_score,
                "away_score": run_result.away_score,
                "winner_id": run_result.winner_id,
                "final_quarter": run_result.final_quarter,
                "duration_seconds": run_result.duration_seconds,
                "status": run_result.status,
                "total_plays": run_result.total_plays,
                "total_drives": run_result.total_drives,
            }
            self.game_results.append(game_result)
            self.game_details.append(
                serialize_game_state(
                    game_state=run_result.game_state,
                    rep_number=rep_number,
                    seed=run_result.seed,
                )
            )

            if wants_db_output(self.output_mode):
                self._pending_db_games.append(
                    (run_result.game_id, game_result, run_result.game_state)
                )

            logger.info(
                f"Rep {rep_number} complete [{run_result.status}]: "
                f"{run_result.home_score}-{run_result.away_score} "
                f"(Q{run_result.final_quarter}, {run_result.duration_seconds:.2f}s)"
            )

        return self._compute_aggregate_stats()

    def _get_next_game_id(self) -> str:
        """
        Get the next sequential game ID by querying the database.

        Returns:
            Sequential game ID as a string (e.g., "1", "2", "3"...)
        """
        assert self.db_writer is not None
        return self.db_writer.get_next_game_id()

    def _compute_aggregate_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all replications."""
        if not self.game_results:
            return {}

        completed_games = [g for g in self.game_results if g.get("status") != "failed"]
        failed_reps = sum(1 for g in self.game_results if g.get("status") == "failed")

        if not completed_games:
            return {"failed_reps": failed_reps}

        home_wins = sum(
            1 for g in completed_games if g["winner_id"] == self.home_team.uid
        )
        away_wins = sum(
            1 for g in completed_games if g["winner_id"] == self.away_team.uid
        )
        ties = sum(1 for g in completed_games if g["winner_id"] is None)

        avg_home_score = sum(g["home_score"] for g in completed_games) / len(
            completed_games
        )
        avg_away_score = sum(g["away_score"] for g in completed_games) / len(
            completed_games
        )
        avg_duration = sum(g["duration_seconds"] for g in completed_games) / len(
            completed_games
        )

        return {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "ties": ties,
            "home_win_pct": home_wins / len(completed_games),
            "away_win_pct": away_wins / len(completed_games),
            "avg_home_score": avg_home_score,
            "avg_away_score": avg_away_score,
            "avg_duration_seconds": avg_duration,
            "failed_reps": failed_reps,
        }

    def _build_experiment_payload(self, elapsed_time: float) -> ExperimentOutputPayload:
        """Build canonical experiment metadata payload."""
        return {
            "id": self.experiment_id,
            "name": self.experiment_name,
            "num_reps": self.num_reps,
            "base_seed": self.base_seed,
            "elapsed_time": elapsed_time,
            "description": self.experiment_description,
        }

    def _build_teams_payload(self) -> Dict[str, TeamOutputPayload]:
        """Build canonical team payload for consistent JSON/DB projections."""
        return {
            "home": serialize_team(self.home_team),
            "away": serialize_team(self.away_team),
        }

    def _build_output_payload(
        self, elapsed_time: float, aggregate_stats: Dict[str, Any]
    ) -> SimulationOutputPayload:
        """Build canonical output payload shared across JSON and DB paths."""
        experiment = self._build_experiment_payload(elapsed_time=elapsed_time)
        teams = self._build_teams_payload()
        results: SimulationResultsPayload = {
            "games": self.game_results,
            "aggregate": aggregate_stats,
            "game_details": self.game_details,
        }

        return {
            "schema_version": self.schema_version,
            "experiment": experiment,
            "teams": teams,
            "results": results,
        }

    def _persist_db_output(self, output_payload: SimulationOutputPayload) -> None:
        """Persist DB output after simulations complete and payload is assembled."""
        assert self.db_writer is not None

        logger.info("Persisting DB output from canonical payload...")
        self.db_writer.write_results(
            output_payload=output_payload,
            pending_games=self._pending_db_games,
        )

        self._pending_db_games.clear()
