import logging
from simpy import Environment
from typing import Optional

from ..state.play_state import PlayState
from ..state.game_state import GameState
from ..state.drive_state import DriveState
from ..domain.rules.base import LeagueRules
from ..models.registry import ModelRegistry
from ..rng import RNG
from .play_engine import PlayEngine


logger = logging.getLogger(__name__)


class DriveExecutionError(Exception):
    """Custom exception for errors during drive execution."""

    pass


class DriveEngine:
    """Engine to simulate a single drive within a game."""

    def __init__(
        self,
        env: Environment,
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        rules: LeagueRules,
    ) -> None:
        self.env = env
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.rules = rules
        self.drive_state = DriveState(self.game_state)
        self.play_engine = PlayEngine(env, game_state, models, rng, self.rules)

    def run(self) -> DriveState:
        last_play: Optional[PlayState] = None

        while not self.is_drive_over():
            self.run_pre_play_hooks()

            play_state = self.play_engine.run()
            last_play = play_state
            self.drive_state.add_play(play_state)
            self.game_state.apply_play(play_state)  # updates the GameState
            self.run_post_play_hooks()

        if last_play is None:
            msg = "Drive ended without running any plays."
            logger.error(msg)
            raise DriveExecutionError(msg)

        self.drive_state.finalize(last_play, self.game_state)
        # schedule things like kickoffs and extra points based on drive result
        self.rules.on_drive_end(self.game_state, self.drive_state)
        return self.drive_state

    def is_drive_over(self) -> bool:
        return self.game_state.is_drive_over()

    def run_pre_play_hooks(self) -> None:
        """Run any pre-play hooks, such as penalties or special conditions."""
        # TODO: Update with actual pre-play hooks and make calls to models for
        # things like pre play penalties.
        pass

    def run_post_play_hooks(self) -> None:
        """Run any post-play hooks, such as updating stats or checking for turnovers."""
        # TODO: Update with actual post-play hooks and calls to models for things like
        # turnovers, injuries, etc.
        pass
