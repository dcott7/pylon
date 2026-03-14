"""Pylon implementation of the generic simulation contract.

This module adapts one football game execution to ``sim.Simulation`` so the
higher-level batch orchestration can later move to ``sim.SimulationRunner``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, List

from sim.base import Simulation
from sim.rng import RNG

from .domain.rules.base import LeagueRules
from .domain.rules.nfl import NFLRules
from .domain.team import Team
from .engine.game_engine import GameEngine
from .models.registry import TypedModel
from .state.game_state import GameState


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PylonSimulationResult:
    """Single-game execution result for the pylon simulation implementation."""

    game_id: str
    seed: int
    home_score: int
    away_score: int
    winner_id: str | None
    final_quarter: int
    duration_seconds: float
    status: str
    total_plays: int
    total_drives: int
    game_state: GameState


class SimulationStatus(Enum):
    """Enumeration of simulation execution statuses."""

    COMPLETED = "completed"
    FAILED = "failed"


class PylonSimulation(Simulation[PylonSimulationResult]):
    """One-game pylon simulation compatible with the generic sim protocol."""

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        game_id: str,
        rng: RNG,
        user_models: List[TypedModel[Any, Any]] | None = None,
        rules: LeagueRules = NFLRules(),  # type: ignore
        max_drives: int | None = None,
    ) -> None:
        self.home_team = home_team
        self.away_team = away_team
        self.game_id = game_id
        self.rng = rng
        self.user_models = user_models
        self.rules = rules
        self.max_drives = max_drives

    def run(self) -> PylonSimulationResult:
        """Execute one game and return canonical pylon simulation result."""
        logger.debug(
            "Starting pylon simulation game_id=%s seed=%s home=%s away=%s",
            self.game_id,
            self.rng.seed,
            self.home_team.uid,
            self.away_team.uid,
        )
        started_at = time.time()

        try:
            engine = self._create_game_engine()
            engine.run()
        except Exception:
            # TODO: Add more context to this exception handling and maybe even
            # consider adding retry logic for transient errors. If we proceed
            # with retry logic we should be make a max retry count configurable
            # and also ensure that we use a different seed for each retry attempt
            # to avoid deterministic failures. This is especially important if we
            # end up running multiple replications where we would need to ensure
            # there is no seed overlap.
            logger.exception(
                "Pylon simulation failed game_id=%s seed=%s",
                self.game_id,
                self.rng.seed,
            )
            raise

        elapsed = time.time() - started_at
        result = self._build_result(engine=engine, elapsed=elapsed)
        logger.debug(
            "Completed pylon simulation game_id=%s status=%s score=%s-%s elapsed=%.3fs",
            result.game_id,
            result.status,
            result.home_score,
            result.away_score,
            result.duration_seconds,
        )

        return result

    def _create_game_engine(self) -> GameEngine:
        """Create a game engine for this simulation execution."""
        return GameEngine(
            home_team=self.home_team,
            away_team=self.away_team,
            game_id=self.game_id,
            user_models=self.user_models,
            rng=self.rng,
            rules=self.rules,
            max_drives=self.max_drives,
        )

    def _resolve_winner_id(self, home_score: int, away_score: int) -> str | None:
        """Resolve winner ID from final scores (or None for ties)."""
        if home_score > away_score:
            return self.home_team.uid
        if away_score > home_score:
            return self.away_team.uid
        return None

    def _build_result(
        self, engine: GameEngine, elapsed: float
    ) -> PylonSimulationResult:
        """Build canonical pylon simulation result from a finished engine run."""
        game_state = engine.game_state
        home_score = game_state.scoreboard.current_score(self.home_team)
        away_score = game_state.scoreboard.current_score(self.away_team)
        winner_id = self._resolve_winner_id(
            home_score=home_score, away_score=away_score
        )
        status = (
            SimulationStatus.FAILED
            if engine.max_drives_reached
            else SimulationStatus.COMPLETED
        )

        return PylonSimulationResult(
            game_id=self.game_id,
            seed=self.rng.seed,
            home_score=home_score,
            away_score=away_score,
            winner_id=winner_id,
            final_quarter=game_state.clock.current_quarter,
            duration_seconds=elapsed,
            status=status.value,
            total_plays=game_state.total_plays(),
            total_drives=game_state.total_drives(),
            game_state=game_state,
        )
