from abc import abstractmethod
import logging
from typing import Dict, List, Optional

from .model import TypedModel, ModelContext, ModelExecutionError
from ..state.game_state import GameState
from ..domain.playbook import PlayCall, PlayTypeEnum
from ..domain.athlete import Athlete, AthletePositionEnum
from ..engine.rng import RNG


logger = logging.getLogger(__name__)


# ==============================
# Defensive Model Contexts
# ==============================


class DefPlayCallContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        offensive_play_type: Optional[PlayTypeEnum] = None,
    ) -> None:
        super().__init__(game_state, rng)
        self.offensive_play_type = offensive_play_type


class SackContext(ModelContext):
    """Context for determining if a pass play results in a sack."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.off_personnel_assignments = off_personnel_assignments
        self.def_personnel_assignments = def_personnel_assignments


class SackYardsContext(ModelContext):
    """Context for determining yards lost on a sack."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.off_personnel_assignments = off_personnel_assignments
        self.def_personnel_assignments = def_personnel_assignments


class InterceptionReturnYardsContext(ModelContext):
    """Context for determining interception return yards (positive value)."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        interceptor: Athlete,
        off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.interceptor = interceptor
        self.off_personnel_assignments = off_personnel_assignments
        self.def_personnel_assignments = def_personnel_assignments


# ==============================
# Defensive Models
# ==============================


class DefensivePlayCallModel(TypedModel[DefPlayCallContext, PlayCall]):
    """Selects the defensive play call for a play."""

    def __init__(self) -> None:
        super().__init__(name="def_play_call")

    @abstractmethod
    def execute(self, context: DefPlayCallContext) -> PlayCall: ...


class DefaultDefensivePlayCallModel(DefensivePlayCallModel):
    """Baseline defensive play call model with simple type mapping and random choice."""

    # Map offensive special teams plays to their defensive counterparts
    DEFENSIVE_RESPONSE_MAP = {
        PlayTypeEnum.PUNT: PlayTypeEnum.PUNT_RETURN,
        PlayTypeEnum.FIELD_GOAL: PlayTypeEnum.FIELD_GOAL_BLOCK,
        PlayTypeEnum.KICKOFF: PlayTypeEnum.KICKOFF_RETURN,
        # TODO: Consider adding a specific defensive play type for PAT defense
        PlayTypeEnum.EXTRA_POINT: PlayTypeEnum.DEFENSIVE_PLAY,
        PlayTypeEnum.TWO_POINT_CONVERSION: PlayTypeEnum.DEFENSIVE_PLAY,
    }

    def execute(self, context: DefPlayCallContext) -> PlayCall:
        playbook = context.game_state.def_team.def_playbook

        if playbook is None:
            logger.error(
                f"Defensive playbook is None for team {context.game_state.def_team.name}."
                f"The PlayCall Model should not be called if the defense has no playbook."
            )
            raise ModelExecutionError(
                "Defensive playbook is None, cannot select play call."
            )

        off_type = context.offensive_play_type
        assert off_type is not None

        if off_type.is_special_teams():
            # Map the offensive special teams play to the corresponding defensive play type
            def_type = self.DEFENSIVE_RESPONSE_MAP.get(
                off_type, PlayTypeEnum.DEFENSIVE_PLAY
            )
            candidate_types = [def_type]
        else:
            # For non-special teams plays, the defense can call any defensive play type
            candidate_types = [PlayTypeEnum.DEFENSIVE_PLAY]

        candidates: List[PlayCall] = []
        for play_type in candidate_types:
            candidates.extend(playbook.get_by_type(play_type))

        if not candidates:
            # Fallback to generic defensive plays if specific type not available
            logger.warning(
                f"No defensive plays of type(s) {candidate_types} available, falling "
                "back to generic defensive plays"
            )
            candidates = playbook.get_by_type(PlayTypeEnum.DEFENSIVE_PLAY)

        return context.rng.choice(candidates)


class SackModel(TypedModel[SackContext, bool]):
    """Determines whether the quarterback is sacked on a pass play."""

    def __init__(self) -> None:
        super().__init__(name="sack")

    @abstractmethod
    def execute(self, context: SackContext) -> bool: ...


class DefaultSackModel(SackModel):
    """Baseline sack model using a fixed sack probability."""

    def __init__(self, base_sack_rate: float = 0.04) -> None:
        """
        Initialize with a base sack rate.
        """
        assert 0 <= base_sack_rate <= 1, "Base sack rate must be between 0 and 1"
        super().__init__()
        self.base_sack_rate = base_sack_rate

    def execute(self, context: SackContext) -> bool:
        is_sack = context.rng.random() < self.base_sack_rate

        if is_sack:
            logger.debug("Defense sacks the quarterback!")

        return is_sack


class SackYardsModel(TypedModel[SackYardsContext, int]):
    """Determines yards lost on a sack (positive value)."""

    def __init__(self) -> None:
        super().__init__(name="sack_yards")

    @abstractmethod
    def execute(self, context: SackYardsContext) -> int: ...


class DefaultSackYardsModel(SackYardsModel):
    """
    Default sack yards model using a weighted distribution.
    Returns positive value representing yards lost (e.g., 7 means 7 yards lost).
    """

    def execute(self, context: SackYardsContext) -> int:
        # Realistic distribution: most sacks are 5-8 yards
        # Weights: 5 yards (25%), 6 yards (35%), 7 yards (25%), 8 yards (15%)
        yards_lost = context.rng.choice([5, 6, 7, 8], weights=[0.25, 0.35, 0.25, 0.15])
        logger.debug(f"Sack yards lost: {yards_lost}")
        return yards_lost


class InterceptionContext(ModelContext):
    """Context for determining if an incomplete pass is intercepted."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        passer: Athlete,
        targetted: Athlete,
        air_yards: int,
        off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.passer = passer
        self.targetted = targetted
        self.air_yards = air_yards
        self.off_personnel_assignments = off_personnel_assignments
        self.def_personnel_assignments = def_personnel_assignments


class InterceptionModel(TypedModel[InterceptionContext, bool]):
    """Determines whether an incomplete pass is intercepted."""

    def __init__(self) -> None:
        super().__init__(name="interception")

    @abstractmethod
    def execute(self, context: InterceptionContext) -> bool: ...


class DefaultInterceptionModel(InterceptionModel):
    """Default interception model using a base probability."""

    def __init__(self, base_interception_rate: float = 0.025) -> None:
        assert 0 <= base_interception_rate <= 1, (
            "Base interception rate must be between 0 and 1"
        )
        super().__init__()
        self.base_interception_rate = base_interception_rate

    def execute(self, context: InterceptionContext) -> bool:
        is_interception = context.rng.random() < self.base_interception_rate

        if is_interception:
            logger.debug("Pass intercepted by the defense!")

        return is_interception


class InterceptionReturnYardsModel(TypedModel[InterceptionReturnYardsContext, int]):
    """Determines yards gained on an interception return (non-negative)."""

    def __init__(self) -> None:
        super().__init__(name="interception_return_yards")

    @abstractmethod
    def execute(self, context: InterceptionReturnYardsContext) -> int: ...


class DefaultInterceptionReturnYardsModel(InterceptionReturnYardsModel):
    """Default interception return yards model based on distance to endzone."""

    def execute(self, context: InterceptionReturnYardsContext) -> int:
        # Return yards can be anywhere from 0 to the distance to the endzone
        # from the interception spot
        yards = context.rng.randint(
            0, 100 - context.game_state.possession.ball_position
        )
        logger.debug(f"Interception return yards: {yards}")
        return yards
