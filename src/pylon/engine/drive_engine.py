"""Drive-level simulation loop: executes plays until drive ends per league rules."""

import logging
from typing import Optional

from ..state.play_record import PlayRecord
from ..state.game_state import GameState, GameStateUpdater
from ..state.drive_record import DriveRecord
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
        play_count = 0
        max_plays = 50  # Safety limit to prevent infinite loops during testing

        while not self.is_drive_over(play_count) and play_count < max_plays:
            # create snapshots of the current game state before the play
            play_record = PlayRecord(self.game_state)
            # execute the play
            play_data = self.play_engine.run()

            self.run_pre_play_hooks()

            # Assign execution data to the play record before updating game state
            play_record.set_execution_data(play_data)

            GameStateUpdater.apply_play_data(self.game_state, play_data, self.rules)

            play_record.set_end_state(self.game_state)
            self.drive_record.add_play(play_record)
            last_play = play_record

            self.run_post_play_hooks()
            play_count += 1

        # ensure at least one play was run; allow empty drive when a pending kickoff/half transition is in progress
        if last_play is None:
            if self.game_state.has_pending_kickoff():
                logger.info(
                    "Skipping empty drive because a pending kickoff/half transition is in progress."
                )
                self.drive_record.set_end_state(self.game_state)
                self.rules.on_drive_end(self.game_state, self.drive_record)
                return self.drive_record

            msg = "Drive ended without running any plays."
            logger.error(msg)
            raise DriveExecutionError(msg)

        self.drive_record.set_end_state(self.game_state)
        self.rules.on_drive_end(self.game_state, self.drive_record)
        return self.drive_record

    def is_drive_over(self, play_count: int) -> bool:
        # Get the possession team that started this drive
        drive_start_team = self.drive_record.start.pos_team
        assert drive_start_team is not None
        return self.rules.is_drive_over(self.game_state, drive_start_team, play_count)

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
