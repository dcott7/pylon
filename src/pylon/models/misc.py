from __future__ import annotations
from abc import abstractmethod
from enum import Enum
import logging
from typing import TYPE_CHECKING

from .model import TypedModel, ModelContext
from ..domain.team import Team
from ...sim.rng import RNG

if TYPE_CHECKING:
    from ..state.game_state import GameState


logger = logging.getLogger(__name__)


class CoinTossChoice(Enum):
    KICK = "kick"
    RECEIVE = "receive"


# ==============================
# Miscellaneous Model Contexts
# ==============================


class CoinTossContext(ModelContext):
    pass


class PlayTimeElapsedContext(ModelContext):
    pass


class PrePlayClockRunoffContext(ModelContext):
    pass


class KickReceiveContext(ModelContext):
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        super().__init__(game_state, rng)
        self.coin_tosswinner = game_state.coin_toss_winner


# ==============================
# Miscellaneous Models
# ==============================


class PlayTimeElapsedModel(TypedModel[PlayTimeElapsedContext, int]):
    """Determines the amount of time elapsed on a play."""

    def __init__(self) -> None:
        super().__init__(name="play_time_elapsed")

    @abstractmethod
    def execute(self, context: PlayTimeElapsedContext) -> int: ...


class DefaultPlayTimeElapsedModel(PlayTimeElapsedModel):
    """Baseline play time model using a simple random range."""

    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: PlayTimeElapsedContext) -> int:
        return context.rng.randint(20, 40)


class PrePlayClockRunoffModel(TypedModel[PrePlayClockRunoffContext, int]):
    """Determines pre-snap clock runoff in seconds."""

    def __init__(self) -> None:
        super().__init__(name="preplay_clock_runoff")

    @abstractmethod
    def execute(self, context: PrePlayClockRunoffContext) -> int: ...


class DefaultPrePlayClockRunoffModel(PrePlayClockRunoffModel):
    """Baseline pre-play runoff model using a simple random range."""

    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: PrePlayClockRunoffContext) -> int:
        return context.rng.randint(20, 40)


class CoinTossWinnerModel(TypedModel[CoinTossContext, Team]):
    """Determines the coin toss winner."""

    def __init__(self) -> None:
        super().__init__(name="coin_toss_winner")

    @abstractmethod
    def execute(self, context: CoinTossContext) -> Team: ...


class DefaultCoinTossWinnerModel(CoinTossWinnerModel):
    """Baseline coin toss model using a random choice between teams."""

    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: CoinTossContext) -> Team:
        teams = [context.game_state.home_team, context.game_state.away_team]
        winner = context.rng.choice(teams)
        return winner


class KickReceiveChoiceModel(TypedModel[KickReceiveContext, CoinTossChoice]):
    """Determines whether the coin toss winner kicks or receives."""

    def __init__(self) -> None:
        super().__init__(name="kick_receive_choice")

    @abstractmethod
    def execute(self, context: KickReceiveContext) -> CoinTossChoice: ...


class DefaultKickReceiveChoiceModel(KickReceiveChoiceModel):
    """Baseline kick/receive choice model using a random selection."""

    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: KickReceiveContext) -> CoinTossChoice:
        # could set this to depend on the coin toss winner
        return context.rng.choice([CoinTossChoice.KICK, CoinTossChoice.RECEIVE])
