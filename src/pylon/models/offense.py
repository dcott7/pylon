from abc import abstractmethod
import logging
from typing import Dict, List

from .model import TypedModel
from ..state.game_state import GameState
from ..domain.playbook import PlayCall, PlayTypeEnum
from ..domain.athlete import Athlete, AthletePositionEnum
from ..rng import RNG


logger = logging.getLogger(__name__)


class AirYardsContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class CompletionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        passer: Athlete,
        targetted: Athlete,
        air_yards: int,
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments
        self.passer = passer
        self.targetted = targetted
        self.air_yards = air_yards


class YardsAfterCatchContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class OffPlayCallContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class RushYardsGainedContext:
    def __init__(
        self, game_state: GameState, rng: RNG, play_call: PlayCall, rusher: Athlete
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.play_call = play_call
        self.rusher = rusher


class OffensivePlayCallModel(TypedModel[OffPlayCallContext, PlayCall]):
    def __init__(self) -> None:
        super().__init__(name="off_play_call")

    @abstractmethod
    def execute(self, context: OffPlayCallContext) -> PlayCall: ...


class DefaultOffensivePlayCallModel(OffensivePlayCallModel):
    def execute(self, context: OffPlayCallContext) -> PlayCall:
        # TODO: Implement a more sophisticated play-calling logic
        playbook = context.game_state.pos_team.off_playbook
        return context.rng.choice(
            playbook.get_by_type(PlayTypeEnum.RUN)
            + playbook.get_by_type(PlayTypeEnum.PASS)
        )


class RushYardsGainedModel(TypedModel[RushYardsGainedContext, int]):
    def __init__(self) -> None:
        super().__init__(name="rush_yards_gained")

    @abstractmethod
    def execute(self, context: RushYardsGainedContext) -> int: ...


class DefaultRushYardsGainedModel(RushYardsGainedModel):
    def execute(self, context: RushYardsGainedContext) -> int:
        # Simple model: Yards gained is based on rusher's rushing skill plus some randomness
        return context.rng.randint(-1, 10)


class AirYardsModel(TypedModel[AirYardsContext, int]):
    def __init__(self) -> None:
        super().__init__(name="airyards")

    @abstractmethod
    def execute(self, context: AirYardsContext) -> int: ...


class DefaultAirYardsModel(AirYardsModel):
    def execute(self, context: AirYardsContext) -> int:
        return context.rng.randint(0, 10)  # TODO: make this more realistic


class CompletionModel(TypedModel[CompletionContext, bool]):
    def __init__(self) -> None:
        super().__init__(name="completion")

    @abstractmethod
    def execute(self, context: CompletionContext) -> bool: ...


class DefaultCompletionModel(CompletionModel):
    def execute(self, context: CompletionContext) -> bool:
        return context.rng.random() < 0.7  # default to 70% chance completion


class YardsAfterCatchModel(TypedModel[YardsAfterCatchContext, int]):
    def __init__(self) -> None:
        super().__init__(name="yac")

    @abstractmethod
    def execute(self, context: YardsAfterCatchContext) -> int: ...


class DefaultYardsAfterCatchModel(YardsAfterCatchModel):
    def execute(self, context: YardsAfterCatchContext) -> int:
        return context.rng.randint(0, 10)
