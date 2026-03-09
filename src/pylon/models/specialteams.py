from abc import abstractmethod
import logging
from typing import Dict, List

from .model import TypedModel, ModelContext
from ..state.game_state import GameState
from ..domain.athlete import Athlete, AthletePositionEnum
from ..engine.rng import RNG


logger = logging.getLogger(__name__)


# ==============================
# Special Teams Model Contexts
# ==============================


class FieldGoalContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        kicker: Athlete,
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments
        self.kicker = kicker


class PuntDistanceContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments


class PuntReturnDistanceContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        returner: Athlete,
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments
        self.returner = returner


class KickoffReturnDistanceContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        returner: Athlete,
    ) -> None:
        super().__init__(game_state, rng)
        self.returner = returner


class KickoffDistanceContext(ModelContext):
    """Context for determining how far a kickoff travels."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        kicker: Athlete,
    ) -> None:
        super().__init__(game_state, rng)
        self.kicker = kicker


class KickoffTouchbackDecisionContext(ModelContext):
    """Context for deciding whether to take a touchback or return."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        returner: Athlete,
        landing_spot: int,  # Where the ball lands (from receiving team's goal line)
    ) -> None:
        super().__init__(game_state, rng)
        self.returner = returner
        self.landing_spot = landing_spot


# ==============================
# Special Teams Models
# ==============================


class PuntDistanceModel(TypedModel[PuntDistanceContext, int]):
    """Determines punt distance in yards."""

    def __init__(self) -> None:
        super().__init__(name="punt_distance")

    @abstractmethod
    def execute(self, context: PuntDistanceContext) -> int: ...


class DefaultPuntDistanceModel(PuntDistanceModel):
    """Baseline punt distance model using a simple random distribution."""

    def execute(self, context: PuntDistanceContext) -> int:
        return context.rng.randint(0, 70)  # TODO: make this more realistic


class PuntReturnDistanceModel(TypedModel[PuntReturnDistanceContext, int]):
    """Determines punt return yards."""

    def __init__(self) -> None:
        super().__init__(name="punt_return_distance")

    @abstractmethod
    def execute(self, context: PuntReturnDistanceContext) -> int: ...


class DefaultPuntReturnDistanceModel(PuntReturnDistanceModel):
    """Baseline punt return distance model using a simple random distribution."""

    def execute(self, context: PuntReturnDistanceContext) -> int:
        return context.rng.randint(0, 30)  # TODO: make this more realistic


class FieldGoalModel(TypedModel[FieldGoalContext, bool]):
    """Determines whether a field goal/extra point attempt is good."""

    def __init__(self) -> None:
        super().__init__(name="field_goal_success")

    @abstractmethod
    def execute(self, context: FieldGoalContext) -> bool: ...


class DefaultFieldGoalModel(FieldGoalModel):
    """Baseline field goal model based on distance and a random roll."""

    def execute(self, context: FieldGoalContext) -> bool:
        distance = context.game_state.possession.ball_position
        kick_distance = 100 - distance + 17  # 17 yards added for end zone and snap
        roll = context.rng.randint(1, 100)

        if kick_distance < 20:
            kick_chance = 99
        elif distance < 30:
            kick_chance = 97
        elif kick_distance < 40:
            kick_chance = 92
        elif kick_distance < 50:
            kick_chance = 80
        elif kick_distance < 60:
            kick_chance = 70
        elif kick_distance < 70:
            kick_chance = 30
        else:
            logger.warning(
                f"Extremely long field goal attempt of {kick_distance} yards. "
                "Probability of success set to 0%."
            )
            kick_chance = 0  # almost impossible

        is_fg_good = roll <= kick_chance
        logger.debug(
            f"Field Goal Attempt: Distance={kick_distance}, "
            f"Chance={kick_chance}%, Roll={roll}, Success={is_fg_good}"
        )
        return is_fg_good


class KickoffReturnDistanceModel(TypedModel[KickoffReturnDistanceContext, int]):
    """Determines kickoff return yards."""

    def __init__(self) -> None:
        super().__init__(name="kickoff_return_distance")

    @abstractmethod
    def execute(self, context: KickoffReturnDistanceContext) -> int: ...


class DefaultKickoffReturnDistanceModel(KickoffReturnDistanceModel):
    """Baseline kickoff return distance model using a simple random distribution."""

    def execute(self, context: KickoffReturnDistanceContext) -> int:
        return context.rng.randint(0, 40)  # TODO: make this more realistic


class KickoffDistanceModel(TypedModel[KickoffDistanceContext, int]):
    """Determines kickoff distance in yards."""

    def __init__(self) -> None:
        super().__init__(name="kickoff_distance")

    @abstractmethod
    def execute(self, context: KickoffDistanceContext) -> int: ...


class DefaultKickoffDistanceModel(KickoffDistanceModel):
    """Baseline kickoff distance model: kickoffs travel 55-75 yards."""

    def execute(self, context: KickoffDistanceContext) -> int:
        # In NFL, kickoffs from 35 typically travel 60-70 yards
        # Landing in endzone (65+ yards) or at goal line area
        return context.rng.randint(55, 75)


class KickoffTouchbackDecisionModel(TypedModel[KickoffTouchbackDecisionContext, bool]):
    """Determines whether a returner takes a touchback on a kickoff."""

    def __init__(self) -> None:
        super().__init__(name="kickoff_touchback_decision")

    @abstractmethod
    def execute(self, context: KickoffTouchbackDecisionContext) -> bool: ...


class DefaultKickoffTouchbackDecisionModel(KickoffTouchbackDecisionModel):
    """Baseline touchback decision: take deep touchbacks, return near goal line."""

    def execute(self, context: KickoffTouchbackDecisionContext) -> bool:
        # If ball lands more than 5 yards deep in endzone, usually take touchback
        # If at goal line or just in endzone, more likely to return
        if context.landing_spot < -5:  # Deep in endzone
            return context.rng.random() < 0.9  # 90% take touchback
        elif context.landing_spot < 0:  # Shallow endzone
            return context.rng.random() < 0.6  # 60% take touchback
        else:  # Outside endzone
            return False  # Always return
