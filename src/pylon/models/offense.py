from abc import abstractmethod
import logging
from typing import Dict, List

from sim.rng import RNG
from .model import TypedModel, ModelContext, ModelExecutionError
from ..state.game_state import GameState
from ..domain.playbook import PlayCall, PlayTypeEnum
from ..domain.athlete import Athlete, AthletePositionEnum


logger = logging.getLogger(__name__)


# ==============================
# Offensive Model Contexts
# ==============================


class AirYardsContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments


class CompletionContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        passer: Athlete,
        targetted: Athlete,
        air_yards: int,
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments
        self.passer = passer
        self.targetted = targetted
        self.air_yards = air_yards


class YardsAfterCatchContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments


class PlayTypeContext(ModelContext):
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        super().__init__(game_state, rng)


class OffPlayCallContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        requested_play_type: PlayTypeEnum,
    ) -> None:
        super().__init__(game_state, rng)
        self.requested_play_type = requested_play_type


class RushYardsGainedContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        play_call: PlayCall,
        rusher: Athlete,
    ) -> None:
        super().__init__(game_state, rng)
        self.play_call = play_call
        self.rusher = rusher


# ==============================
# Offensive Models
# ==============================


class PlayTypeModel(TypedModel[PlayTypeContext, PlayTypeEnum]):
    """Selects the offensive play type for the upcoming play."""

    def __init__(self) -> None:
        super().__init__(name="play_type")

    @abstractmethod
    def execute(self, context: PlayTypeContext) -> PlayTypeEnum: ...


class DefaultPlayTypeModel(PlayTypeModel):
    """Baseline play type model with simple down-based tendencies."""

    def execute(self, context: PlayTypeContext) -> PlayTypeEnum:
        down = context.game_state.possession.down
        if down is None:
            down = 1
        # Heavier run tendency on early downs, heavier pass tendency later.
        if down <= 2:
            return context.rng.choice([PlayTypeEnum.RUN, PlayTypeEnum.PASS], [0.6, 0.4])
        return context.rng.choice([PlayTypeEnum.RUN, PlayTypeEnum.PASS], [0.3, 0.7])


class OffensivePlayCallModel(TypedModel[OffPlayCallContext, PlayCall]):
    """Selects the offensive play call for a play."""

    def __init__(self) -> None:
        super().__init__(name="off_play_call")

    @abstractmethod
    def execute(self, context: OffPlayCallContext) -> PlayCall:
        ...
        # playbook = context.game_state.pos_team.off_playbook
        # if playbook is None:
        #     logger.error(
        #         f"Offensive playbook is None for team {context.game_state.pos_team.name}."
        #         f"The PlayCall Model should not be called if the offense has no playbook."
        #     )


class DefaultOffensivePlayCallModel(OffensivePlayCallModel):
    """Baseline offense play call: choose from requested play type in playbook."""

    def execute(self, context: OffPlayCallContext) -> PlayCall:
        # TODO: Implement a more sophisticated play-calling logic.
        playbook = context.game_state.pos_team.off_playbook
        if playbook is None:
            logger.error(
                f"Offensive playbook is None for team {context.game_state.pos_team.name}."
                f"The PlayCall Model should not be called if the offense has no playbook."
            )
            raise ModelExecutionError(
                "Offensive playbook is None, cannot select play call."
            )

        candidates = playbook.get_by_type(context.requested_play_type)
        if not candidates:
            # Fallback for sparse playbooks
            candidates = playbook.get_by_type(PlayTypeEnum.RUN) + playbook.get_by_type(
                PlayTypeEnum.PASS
            )
        return context.rng.choice(candidates)


class RushYardsGainedModel(TypedModel[RushYardsGainedContext, int]):
    """Determines rushing yards gained on a run play."""

    def __init__(self) -> None:
        super().__init__(name="rush_yards_gained")

    @abstractmethod
    def execute(self, context: RushYardsGainedContext) -> int: ...


class DefaultRushYardsGainedModel(RushYardsGainedModel):
    """Baseline rushing yards model using a simple random distribution."""

    def execute(self, context: RushYardsGainedContext) -> int:
        # Simple model: Yards gained is based on rusher's rushing skill plus some randomness
        return context.rng.randint(-1, 10)


class AirYardsModel(TypedModel[AirYardsContext, int]):
    """Determines intended air yards for a pass attempt."""

    def __init__(self) -> None:
        super().__init__(name="airyards")

    @abstractmethod
    def execute(self, context: AirYardsContext) -> int: ...


class DefaultAirYardsModel(AirYardsModel):
    """Baseline air-yards model using a simple random distribution."""

    def execute(self, context: AirYardsContext) -> int:
        return context.rng.randint(0, 10)  # TODO: make this more realistic


class CompletionModel(TypedModel[CompletionContext, bool]):
    """Determines whether a pass attempt is completed."""

    def __init__(self) -> None:
        super().__init__(name="completion")

    @abstractmethod
    def execute(self, context: CompletionContext) -> bool: ...


class DefaultCompletionModel(CompletionModel):
    """Baseline completion model with a fixed completion probability."""

    def execute(self, context: CompletionContext) -> bool:
        return context.rng.random() < 0.7  # default to 70% chance completion


class YardsAfterCatchModel(TypedModel[YardsAfterCatchContext, int]):
    """Determines yards after catch on a completed pass."""

    def __init__(self) -> None:
        super().__init__(name="yac")

    @abstractmethod
    def execute(self, context: YardsAfterCatchContext) -> int: ...


class DefaultYardsAfterCatchModel(YardsAfterCatchModel):
    """Baseline YAC model using a simple random distribution."""

    def execute(self, context: YardsAfterCatchContext) -> int:
        return context.rng.randint(0, 10)
