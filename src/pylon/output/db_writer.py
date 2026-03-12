"""Database output writer for simulation results."""

from typing import Any, Dict, Mapping

from ..db.database import DatabaseManager
from ..db.repositories import (
    DimensionRepository,
    ExperimentRepository,
    FactRepository,
    GameRepository,
)
from ..state.game_state import GameState
from .types import SimulationOutputPayload, TeamOutputPayload


class DBOutputWriter:
    """Writes simulation dimensions, metadata, and facts to database storage."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def _persist_dimension_data(
        self, home_team: TeamOutputPayload, away_team: TeamOutputPayload
    ) -> None:
        """Persist teams, rosters, and playbooks to database."""
        dim_repo = DimensionRepository(self.db_manager)
        dim_repo.persist_game_dimensions(home_team, away_team)

    def _persist_experiment_metadata(
        self, output_payload: SimulationOutputPayload
    ) -> None:
        """Persist experiment metadata from canonical output payload."""
        experiment: Mapping[str, Any] = output_payload["experiment"]
        exp_repo = ExperimentRepository(self.db_manager)
        exp_repo.create(
            name=experiment["name"],
            num_reps=experiment["num_reps"],
            base_seed=experiment["base_seed"],
            description=experiment.get("description"),
            experiment_id=experiment["id"],
        )

    def _persist_game_result(
        self,
        game_result: Dict[str, Any],
        game_id: str,
        output_payload: SimulationOutputPayload,
    ) -> None:
        """Persist individual game result metadata using canonical payload context."""
        home_team_id = output_payload["teams"]["home"]["uid"]
        away_team_id = output_payload["teams"]["away"]["uid"]
        experiment_id = output_payload["experiment"]["id"]

        game_repo = GameRepository(self.db_manager)
        game_repo.create(
            seed=game_result["seed"],
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=game_result["home_score"],
            away_score=game_result["away_score"],
            winner_id=game_result["winner_id"],
            total_plays=game_result["total_plays"],
            total_drives=game_result["total_drives"],
            final_quarter=game_result["final_quarter"],
            experiment_id=experiment_id,
            rep_number=game_result["rep_number"],
            duration_seconds=game_result["duration_seconds"],
            status=game_result["status"],
            game_id=game_id,
        )

    def _persist_game_facts(self, game_id: str, game_state: GameState) -> None:
        """Persist drives, plays, and participant facts to database."""
        fact_repo = FactRepository(self.db_manager)
        fact_repo.persist_game_facts(game_id, game_state)

    def write_results(
        self,
        output_payload: SimulationOutputPayload,
        pending_games: list[tuple[str, Dict[str, Any], GameState]],
    ) -> None:
        """Persist all DB output from one post-run payload handoff."""
        home_team = output_payload["teams"]["home"]
        away_team = output_payload["teams"]["away"]
        self._persist_dimension_data(home_team, away_team)
        self._persist_experiment_metadata(output_payload)

        for game_id, game_result, game_state in pending_games:
            self._persist_game_result(game_result, game_id, output_payload)
            self._persist_game_facts(game_id, game_state)

    def get_next_game_id(self) -> str:
        """Get the next sequential game ID by querying persisted games."""
        from ..db.schema import Game as OrmGame

        session = self.db_manager.get_session()
        try:
            games = session.query(OrmGame.id).all()
            if not games:
                return "1"
            max_id = max(int(game.id) for game in games)
            return str(max_id + 1)
        finally:
            session.close()
