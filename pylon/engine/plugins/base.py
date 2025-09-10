# src\pylon\engine\plugins\base.py
from abc import ABC, abstractmethod

# from pylon.engine.game import GameState

class GamePluginModel(ABC):
    @abstractmethod
    def run(self, game_state, *args, **kwargs):
        """Run logic with access to full game state."""
        pass