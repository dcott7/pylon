import logging
import simpy

from .state import GameState, GameStatusEnum
from .models.registry import ModelRegistry
from .rng import RNG
from .rule import GameRules


logger = logging.getLogger(__name__)


class GameEngine:
    def __init__(
        self,
        env: simpy.Environment,
        game_state: GameState,
        rules: GameRules,
        models: ModelRegistry,
        rng: RNG,
    ) -> None:
        self.env = env
        self.game_state = game_state
        self.rules = rules
        self.models = models
        self.rng = rng

    def run(self) -> None:
        self.env.process(self._game_loop())
        self.env.run()

    def _game_loop(self):
        logger.info("Game started")
        self.state._game_status = GameStatusEnum.IN_PROGRESS  # type: ignore

        yield self.env.process(self._kickoff_event())

        while not self.rules.is_game_over(self.state):
            yield self.env.process(self._play_event())

        self.state._game_status = GameStatusEnum.COMPLETE  # type: ignore
        logger.info("Game ended")
