from abc import abstractmethod
import logging

from .model import TypedModel
from ..state.game_state import GameState
from ..domain.playbook import PlayCall, PlayTypeEnum
from ..rng import RNG


logger = logging.getLogger(__name__)


class DefPlayCallContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class DefensivePlayCallModel(TypedModel[DefPlayCallContext, PlayCall]):
    def __init__(self) -> None:
        super().__init__(name="def_play_call")

    @abstractmethod
    def execute(self, context: DefPlayCallContext) -> PlayCall: ...


class DefaultDefensivePlayCallModel(DefensivePlayCallModel):
    def execute(self, context: DefPlayCallContext) -> PlayCall:
        # TODO: Implement a more sophisticated play-calling logic
        playbook = context.game_state.def_team.def_playbook
        return context.rng.choice(playbook.get_by_type(PlayTypeEnum.DEFENSIVE_PLAY))
