"""
Simulation orchestration for running multiple game replications.

Provides the SimulationRunner class for executing batches of game simulations
with varying seeds and model configurations, supporting statistical analysis
and model comparison experiments.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .game_engine import GameEngine
from ..domain.team import Team
from ..domain.rules.base import LeagueRules
from ..domain.rules.nfl import NFLRules
from ..models.registry import TypedModel
from ..rng import RNG
from ..db.database import DatabaseManager
from ..db.repositories import DimensionRepository, ExperimentRepository, GameRepository

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

        game_result: Dict[str, Any] = {
            "rep_number": rep_number,
            "seed": seed,
            "home_score": home_score,
            "away_score": away_score,
            "winner_id": winner_id,
            "final_quarter": game_state.clock.current_quarter,
            "duration_seconds": game_duration,
            # TODO: Add total_plays and total_drives once GameExecutionData is accessible
            "total_plays": 0,
            "total_drives": 0,
        }

        # Persist game result to database
        if self.db_manager:
            self._persist_game_result(game_result)

        logger.info(
            f"Rep {rep_number} complete: {home_score}-{away_score} "
            f"(Q{game_state.clock.current_quarter}, {game_duration:.2f}s)"
        )

        return game_result

    def _persist_dimension_data(self) -> None:
        """Persist teams, rosters, and playbooks to database."""
        logger.info("Persisting dimension data (teams, rosters, playbooks)...")
        dim_repo = DimensionRepository(self.db_manager)  # type: ignore
        dim_repo.persist_game_dimensions(self.home_team, self.away_team)

    def _persist_experiment_metadata(self) -> None:
        """Persist experiment metadata to database."""
        logger.info("Persisting experiment metadata...")
        exp_repo = ExperimentRepository(self.db_manager)  # type: ignore
        exp_repo.create(
            name=self.experiment_name,
            num_reps=self.num_reps,
            base_seed=self.base_seed,
            description=self.experiment_description,
            experiment_id=self.experiment_id,
        )

    def _persist_game_result(self, game_result: Dict[str, Any]) -> None:
        """Persist individual game result to database."""
        game_repo = GameRepository(self.db_manager)  # type: ignore
        game_repo.create(
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
        )

    def _compute_aggregate_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all replications."""
        if not self.game_results:
            return {}

        home_wins = sum(
            1 for g in self.game_results if g["winner_id"] == self.home_team.uid
        )
        away_wins = sum(
            1 for g in self.game_results if g["winner_id"] == self.away_team.uid
        )
        ties = sum(1 for g in self.game_results if g["winner_id"] is None)

        avg_home_score = sum(g["home_score"] for g in self.game_results) / len(
            self.game_results
        )
        avg_away_score = sum(g["away_score"] for g in self.game_results) / len(
            self.game_results
        )
        avg_duration = sum(g["duration_seconds"] for g in self.game_results) / len(
            self.game_results
        )

        return {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "ties": ties,
            "home_win_pct": home_wins / len(self.game_results),
            "away_win_pct": away_wins / len(self.game_results),
            "avg_home_score": avg_home_score,
            "avg_away_score": avg_away_score,
            "avg_duration_seconds": avg_duration,
        }
