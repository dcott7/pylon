"""
Simulation orchestration for running multiple game replications.

Provides the SimulationRunner class for executing batches of game simulations
with varying seeds and model configurations, supporting statistical analysis
and model comparison experiments.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .engine.game_engine import GameEngine
from .domain.team import Team
from .domain.rules.base import LeagueRules
from .domain.rules.nfl import NFLRules
from .models.registry import TypedModel
from .engine.rng import RNG
from .db.database import DatabaseManager
from .state.game_state import GameState
from .output import (
    DBOutputWriter,
    ExperimentOutputPayload,
    JsonOutputWriter,
    OUTPUT_SCHEMA_VERSION,
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


class SimulationRunner:
    """
    Orchestrates multiple game simulation replications for statistical analysis.

    Manages:
    - Running multiple GameEngine instances with varied seeds
    - Tracking experiment metadata and results
    - Writing simulation output to JSON, DB, or both
    - Collecting aggregate statistics across reps

    Usage:
        runner = SimulationRunner(
            home_team=bears,
            away_team=niners,
            num_reps=100,
            base_seed=42,
            db_manager=db,
            output_mode=OutputMode.BOTH,
        )
        results = runner.run()
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        num_reps: int,
        base_seed: int = 42,
        user_models: Optional[List[TypedModel[Any, Any]]] = None,
        rules: LeagueRules = NFLRules(),  # type: ignore
        max_drives: Optional[int] = None,
        db_manager: Optional[DatabaseManager] = None,
        output_mode: OutputMode = OutputMode.JSON,
        json_output_path: Optional[Path | str] = None,
        experiment_name: Optional[str] = None,
        experiment_description: Optional[str] = None,
        log_dir: Optional[Path | str] = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize the SimulationRunner.

        Args:
            home_team: Home team for all replications.
            away_team: Away team for all replications.
            num_reps: Number of replications to run.
            base_seed: Base seed for deterministic rep generation (rep N uses base_seed + N).
            user_models: Optional custom models to override defaults.
            rules: League rules (defaults to NFLRules).
            max_drives: Optional drive limit per game.
            db_manager: Optional database manager for persistence.
            output_mode: Output destination: "json", "db", or "both".
            json_output_path: Optional output path for JSON results.
            experiment_name: Optional human-readable experiment name.
            experiment_description: Optional detailed description.
        """
        self.home_team = home_team
        self.away_team = away_team
        self.num_reps = num_reps
        self.base_seed = base_seed
        self.user_models = user_models
        self.rules = rules
        self.max_drives = max_drives
        self.db_manager = db_manager
        self.output_mode = output_mode
        self.log_dir = Path(log_dir) if log_dir is not None else Path("./log")
        self.json_output_path = (
            Path(json_output_path)
            if json_output_path is not None
            else self.log_dir / "simulation_results.json"
        )
        self.json_writer = JsonOutputWriter(self.json_output_path)
        self.log_level = log_level

        # Experiment metadata
        self.experiment_id = str(uuid.uuid4())
        self.experiment_name = (
            experiment_name or f"{home_team.name} vs {away_team.name} - {num_reps} reps"
        )
        self.experiment_description = experiment_description

        self.db_writer = (
            DBOutputWriter(db_manager=self.db_manager)
            if self.db_manager is not None
            else None
        )

        # Result tracking
        self.game_results: List[Dict[str, Any]] = []
        self.game_details: List[GameStateOutputPayload] = []
        self._pending_db_games: List[tuple[str, Dict[str, Any], GameState]] = []
        self._next_db_game_id: Optional[int] = None

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
        start_time = time.time()

        # Ensure output configuration is valid based on the OutputMode
        validate_output_config(
            output_mode=self.output_mode,
            has_db_manager=self.db_manager is not None,
            json_output_path=self.json_output_path,
        )

        # Initialize DB game-id sequence for this run if DB output is requested.
        if wants_db_output(self.output_mode):
            self._next_db_game_id = int(self._get_next_game_id())

        # Ensure log directory exists for per-rep logs
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Run all replications
        for rep_number in range(1, self.num_reps + 1):
            seed = self.base_seed + rep_number
            logger.info(f"Running rep {rep_number}/{self.num_reps} (seed={seed})...")

            game_result = self._run_single_game(rep_number, seed)
            self.game_results.append(game_result)

        elapsed_time = time.time() - start_time
        logger.info(
            f"Experiment complete: {self.num_reps} reps in {elapsed_time:.2f}s "
            f"({elapsed_time / self.num_reps:.2f}s per game)"
        )

        # Compute aggregate statistics
        aggregate_stats = self._compute_aggregate_stats()

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

    def _run_single_game(self, rep_number: int, seed: int) -> Dict[str, Any]:
        """
        Execute a single game replication.

        Args:
            rep_number: Replication number (1-based).
            seed: Random seed for this rep.

        Returns:
            Dictionary with game result metadata.
        """
        # Attach per-rep log file to capture all module logs for this game
        rep_log_path = self.log_dir / f"pylon.{rep_number}.log"
        rep_handler = logging.FileHandler(rep_log_path, mode="w")
        rep_handler.setLevel(self.log_level)
        rep_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        # Attach to root logger to capture logs from all modules during this rep
        root_logger = logging.getLogger()
        previous_level = root_logger.level
        root_logger.addHandler(rep_handler)
        root_logger.setLevel(min(previous_level, self.log_level))

        # Initialize RNG for this game
        rng = RNG(seed)
        game_start = time.time()

        # Determine the game ID. For DB output we reserve sequential IDs in-memory
        # and persist after the full canonical payload has been built.
        if wants_db_output(self.output_mode):
            assert self._next_db_game_id is not None
            game_id = str(self._next_db_game_id)
            self._next_db_game_id += 1
        else:
            game_id = str(rep_number)

        # Create and run game engine
        engine = GameEngine(
            home_team=self.home_team,
            away_team=self.away_team,
            game_id=game_id,
            user_models=self.user_models,
            rng=rng,
            rules=self.rules,
            max_drives=self.max_drives,
        )
        engine.run()

        game_duration = time.time() - game_start

        # Extract winner from the end game state
        end_game_state = engine.game_state
        end_home_score = end_game_state.scoreboard.current_score(self.home_team)
        end_away_score = end_game_state.scoreboard.current_score(self.away_team)
        winner_id: Optional[str] = None
        if end_home_score > end_away_score:
            winner_id = self.home_team.uid
        elif end_away_score > end_home_score:
            winner_id = self.away_team.uid

        # Determine game status
        status = "failed" if engine.max_drives_reached else "completed"

        # Build game result metadata for this replication
        game_result: Dict[str, Any] = {
            "rep_number": rep_number,
            "seed": seed,
            "home_score": end_home_score,
            "away_score": end_away_score,
            "winner_id": winner_id,
            "final_quarter": end_game_state.clock.current_quarter,
            "duration_seconds": game_duration,
            "status": status,
            "total_plays": end_game_state.total_plays(),
            "total_drives": end_game_state.total_drives(),
        }

        # Queue DB persistence and write after canonical payload is built.
        if wants_db_output(self.output_mode):
            self._pending_db_games.append((game_id, game_result, end_game_state))

        self.game_details.append(
            serialize_game_state(
                game_state=end_game_state,
                rep_number=rep_number,
                seed=seed,
            )
        )

        logger.info(
            f"Rep {rep_number} complete [{status}]: {end_home_score}-{end_away_score} "
            f"(Q{end_game_state.clock.current_quarter}, {game_duration:.2f}s)"
        )

        # Detach per-rep handler
        root_logger.removeHandler(rep_handler)
        rep_handler.close()
        root_logger.setLevel(previous_level)

        return game_result

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
            "schema_version": OUTPUT_SCHEMA_VERSION,
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
