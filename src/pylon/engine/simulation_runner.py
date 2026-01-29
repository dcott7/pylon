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

from .game_engine import GameEngine
from ..domain.team import Team
from ..domain.rules.base import LeagueRules
from ..domain.rules.nfl import NFLRules
from ..models.registry import TypedModel
from ..rng import RNG
from ..state.game_state import GameState
from ..db.database import DatabaseManager
from ..db.repositories import (
    DimensionRepository,
    FactRepository,
    ExperimentRepository,
    GameRepository,
)

logger = logging.getLogger(__name__)


class SimulationRunner:
    """
    Orchestrates multiple game simulation replications for statistical analysis.

    Manages:
    - Running multiple GameEngine instances with varied seeds
    - Tracking experiment metadata and results
    - Persisting dimension and fact data to database
    - Collecting aggregate statistics across reps

    Usage:
        runner = SimulationRunner(
            home_team=bears,
            away_team=niners,
            num_reps=100,
            base_seed=42,
            db_manager=db,
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
        self.log_dir = Path(log_dir) if log_dir is not None else Path("./log")
        self.log_level = log_level

        # Experiment metadata
        self.experiment_id = str(uuid.uuid4())
        self.experiment_name = (
            experiment_name or f"{home_team.name} vs {away_team.name} - {num_reps} reps"
        )
        self.experiment_description = experiment_description

        # Result tracking
        self.game_results: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
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

        # Persist dimension data once (teams, rosters, playbooks)
        if self.db_manager:
            self._persist_dimension_data()
            self._persist_experiment_metadata()

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

        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "num_reps": self.num_reps,
            "base_seed": self.base_seed,
            "elapsed_time": elapsed_time,
            "games": self.game_results,
            "aggregate": aggregate_stats,
        }

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
        root_logger = logging.getLogger()
        previous_level = root_logger.level
        root_logger.addHandler(rep_handler)
        root_logger.setLevel(min(previous_level, self.log_level))

        rng = RNG(seed)
        game_start = time.time()

        # Create and run game engine
        engine = GameEngine(
            home_team=self.home_team,
            away_team=self.away_team,
            user_models=self.user_models,
            rng=rng,
            rules=self.rules,
            max_drives=self.max_drives,
        )
        engine.run()

        game_duration = time.time() - game_start

        # Extract results from game state
        game_state = engine.game_state
        home_score = game_state.scoreboard.current_score(self.home_team)
        away_score = game_state.scoreboard.current_score(self.away_team)
        winner_id = None
        if home_score > away_score:
            winner_id = self.home_team.uid
        elif away_score > home_score:
            winner_id = self.away_team.uid

        # Determine game status
        status = "failed" if engine.max_drives_reached else "completed"

        game_result: Dict[str, Any] = {
            "rep_number": rep_number,
            "seed": seed,
            "home_score": home_score,
            "away_score": away_score,
            "winner_id": winner_id,
            "final_quarter": game_state.clock.current_quarter,
            "duration_seconds": game_duration,
            "status": status,
            "total_plays": game_state.total_plays(),
            "total_drives": game_state.total_drives(),
        }

        # Persist game result to database
        if self.db_manager:
            game_id = self._persist_game_result(game_result)
            self._persist_game_facts(game_id, game_state)

        logger.info(
            f"Rep {rep_number} complete [{status}]: {home_score}-{away_score} "
            f"(Q{game_state.clock.current_quarter}, {game_duration:.2f}s)"
        )

        # Detach per-rep handler
        root_logger.removeHandler(rep_handler)
        rep_handler.close()
        root_logger.setLevel(previous_level)

        return game_result

    def _persist_dimension_data(self) -> None:
        """Persist teams, rosters, and playbooks to database."""
        logger.info("Persisting dimension data (teams, rosters, playbooks)...")
        assert self.db_manager is not None
        dim_repo = DimensionRepository(self.db_manager)
        dim_repo.persist_game_dimensions(self.home_team, self.away_team)

    def _persist_experiment_metadata(self) -> None:
        """Persist experiment metadata to database."""
        logger.info("Persisting experiment metadata...")
        assert self.db_manager is not None
        exp_repo = ExperimentRepository(self.db_manager)
        exp_repo.create(
            name=self.experiment_name,
            num_reps=self.num_reps,
            base_seed=self.base_seed,
            description=self.experiment_description,
            experiment_id=self.experiment_id,
        )

    def _persist_game_result(self, game_result: Dict[str, Any]) -> str:
        """
        Persist individual game result to database.

        Returns:
            The game ID that was persisted.
        """
        assert self.db_manager is not None
        game_repo = GameRepository(self.db_manager)
        orm_game = game_repo.create(
            seed=game_result["seed"],
            home_team_id=self.home_team.uid,
            away_team_id=self.away_team.uid,
            home_score=game_result["home_score"],
            away_score=game_result["away_score"],
            winner_id=game_result["winner_id"],
            total_plays=game_result["total_plays"],
            total_drives=game_result["total_drives"],
            final_quarter=game_result["final_quarter"],
            experiment_id=self.experiment_id,
            rep_number=game_result["rep_number"],
            duration_seconds=game_result["duration_seconds"],
            status=game_result["status"],
        )
        return orm_game.id

    def _persist_game_facts(self, game_id: str, game_state: GameState) -> None:
        """
        Persist all game facts (drives, plays, personnel assignments, participants).

        Args:
            game_id: The game fact ID to associate with all fact data.
            game_state: The GameState object containing all play/drive execution data.
        """
        assert self.db_manager is not None
        fact_repo = FactRepository(self.db_manager)
        fact_repo.persist_game_facts(game_id, game_state)

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
