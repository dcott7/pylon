import logging
from typing import Optional

from ..state.play_record import PlayRecord
from ..state.game_state import GameState, GameStateUpdater
from ..state.drive_record import DriveRecord, DriveExecutionData
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
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        rules: LeagueRules,
    ) -> None:
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.rules = rules
        self.drive_record = DriveRecord(self.game_state)
        self.play_engine = PlayEngine(game_state, models, rng, self.rules)

    def run(self) -> DriveRecord:
        last_play: Optional[PlayRecord] = None
        drive_data = DriveExecutionData()

        while not self.is_drive_over():
            # create snapshots of the current game state before the play
            play_record = PlayRecord(self.game_state)
            # execute the play
            play_data = self.play_engine.run()

            self.run_pre_play_hooks()

            GameStateUpdater.apply_play_data(self.game_state, play_data, self.rules)

            play_record.set_end_state(self.game_state)
            drive_data.add_play(play_record)

            self.run_post_play_hooks()

        # ensure at least one play was run
        if last_play is None:
            msg = "Drive ended without running any plays."
            logger.error(msg)
            raise DriveExecutionError(msg)

        self.drive_record.set_end_state(self.game_state)
        self.rules.on_drive_end(self.game_state, self.drive_record)
        return self.drive_record

    def is_drive_over(self) -> bool:
        return self.rules.is_drive_over(self.game_state)

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
