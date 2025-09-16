# src\pylon\engine\plugins\play_outcome.py
from abc import abstractmethod
import random

from pylon.engine.plugins.base import GamePluginModel
from pylon.model.game.play import PlayType

class PlayOutcomeModel(GamePluginModel):
    @abstractmethod
    def run(self, game_state, *args, **kwargs) -> dict:
        """Run logic with access to full game state."""
        pass

class DefaultPlayOutcomeModel(PlayOutcomeModel):
    def run(self, play_call, game_state, seed=None):
        if play_call['type'] == PlayType.RUN:
            yards = random.randint(0, 8)
        else:
            yards = random.randint(-2, 12)
        return {'yards': yards, 'is_clock_running': random.choice([True, False])}