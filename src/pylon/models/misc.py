from __future__ import annotations
from abc import abstractmethod
from enum import Enum
import logging
from typing import TYPE_CHECKING

from .model import TypedModel
from ..domain.team import Team
from ..rng import RNG

if TYPE_CHECKING:
    from ..state.game_state import GameState


logger = logging.getLogger(__name__)


class CoinTossChoice(Enum):
    KICK = "kick"
    RECEIVE = "receive"


class CoinTossContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class KickReceiveContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng
        self.coin_tosswinner = game_state.coin_toss_winner


class PlayTimeElapsedContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class PrePlayClockRunoffContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class PlayTimeElapsedModel(TypedModel[PlayTimeElapsedContext, int]):
    def __init__(self) -> None:
        super().__init__(name="play_time_elapsed")

    @abstractmethod
    def execute(self, context: PlayTimeElapsedContext) -> int: ...


class DefaultPlayTimeElapsedModel(PlayTimeElapsedModel):
    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: PlayTimeElapsedContext) -> int:
        return context.rng.randint(20, 40)


class PrePlayClockRunoffModel(TypedModel[PrePlayClockRunoffContext, int]):
    def __init__(self) -> None:
        super().__init__(name="preplay_clock_runoff")

    @abstractmethod
    def execute(self, context: PrePlayClockRunoffContext) -> int: ...


class DefaultPrePlayClockRunoffModel(PrePlayClockRunoffModel):
    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: PrePlayClockRunoffContext) -> int:
        return context.rng.randint(20, 40)


class CoinTossWinnerModel(TypedModel[CoinTossContext, Team]):
    def __init__(self) -> None:
        super().__init__(name="coin_toss_winner")

    @abstractmethod
    def execute(self, context: CoinTossContext) -> Team: ...


class DefaultCoinTossWinnerModel(CoinTossWinnerModel):
    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: CoinTossContext) -> Team:
        teams = [context.game_state.home_team, context.game_state.away_team]
        winner = context.rng.choice(teams)
        return winner


class KickReceiveChoiceModel(TypedModel[KickReceiveContext, CoinTossChoice]):
    def __init__(self) -> None:
        super().__init__(name="kick_receive_choice")

    @abstractmethod
    def execute(self, context: KickReceiveContext) -> CoinTossChoice: ...


class DefaultKickReceiveChoiceModel(KickReceiveChoiceModel):
    def __init__(self) -> None:
        super().__init__()

    def execute(self, context: KickReceiveContext) -> CoinTossChoice:
        # could set this to depend on the coin toss winner
        return context.rng.choice([CoinTossChoice.KICK, CoinTossChoice.RECEIVE])
