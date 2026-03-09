"""Models for ball possession changes (fumbles, recoveries)."""

from abc import abstractmethod
import logging
from typing import Dict, List

from .model import TypedModel, ModelContext
from ..state.game_state import GameState
from ..domain.athlete import Athlete, AthletePositionEnum
from ..domain.team import Team
from ..engine.rng import RNG


logger = logging.getLogger(__name__)


# ==============================
# Possession Model Contexts
# ==============================


class FumbleContext(ModelContext):
    """Context for determining if a ball carrier fumbles."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        ball_carrier: Athlete,
    ) -> None:
        super().__init__(game_state, rng)
        self.ball_carrier = ball_carrier


class FumbleRecoveryContext(ModelContext):
    """Context for determining which team recovers a fumble."""

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        fumbler: Athlete,
        off_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        def_personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.fumbler = fumbler
        self.off_personnel_assignments = off_personnel_assignments
        self.def_personnel_assignments = def_personnel_assignments


# ==============================
# Possession Models
# ==============================


class FumbleModel(TypedModel[FumbleContext, bool]):
    """Determines whether a ball carrier fumbles."""

    def __init__(self) -> None:
        super().__init__(name="fumble")

    @abstractmethod
    def execute(self, context: FumbleContext) -> bool: ...


class DefaultFumbleModel(FumbleModel):
    """
    Baseline fumble model using a fixed fumble probability.
    """

    def __init__(self, base_fumble_rate: float = 0.015) -> None:
        """
        Initialize with a base fumble rate.

        Args:
            base_fumble_rate: Probability of fumble (~1.5%, roughly NFL average)
        """
        assert 0 <= base_fumble_rate <= 1, "Base fumble rate must be between 0 and 1"
        super().__init__()
        self.base_fumble_rate = base_fumble_rate

    def execute(self, context: FumbleContext) -> bool:
        is_fumble = context.rng.random() < self.base_fumble_rate

        if is_fumble:
            logger.debug(
                f"{context.ball_carrier.first_name} {context.ball_carrier.last_name} "
                f"fumbles the ball!"
            )

        return is_fumble


class FumbleRecoveryModel(TypedModel[FumbleRecoveryContext, Team]):
    """Determines which team recovers a fumble."""

    def __init__(self) -> None:
        super().__init__(name="fumble_recovery")

    @abstractmethod
    def execute(self, context: FumbleRecoveryContext) -> Team: ...


class DefaultFumbleRecoveryModel(FumbleRecoveryModel):
    """
    Baseline fumble recovery model with slight advantage to offense.

    NFL stats show offense recovers ~47-48% of fumbles, defense ~52-53%.
    """

    def __init__(self, offense_recovery_rate: float = 0.47) -> None:
        """
        Initialize with offense recovery probability.

        Args:
            offense_recovery_rate: Probability offense recovers (~47%)
        """
        assert 0 <= offense_recovery_rate <= 1, (
            "Offense recovery rate must be between 0 and 1"
        )
        super().__init__()
        self.offense_recovery_rate = offense_recovery_rate

    def execute(self, context: FumbleRecoveryContext) -> Team:
        offense_recovers = context.rng.random() < self.offense_recovery_rate

        if offense_recovers:
            recovering_team = context.game_state.pos_team
            logger.debug(f"Fumble recovered by offense ({recovering_team.name})")
        else:
            recovering_team = context.game_state.def_team
            logger.debug(f"Fumble recovered by defense ({recovering_team.name})")

        return recovering_team
