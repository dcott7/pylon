from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from ...models.registry import ModelRegistry
from ...rng import RNG
from ...state.game_state import GameState

# We prviously called the models to determine coin toss and kick receive choices,
# but those responsibilities should be moved out of the LeagueRules (I would think).

from .base import LeagueRules, LeagueRulesError  # , KickoffSetup, ExtraPointSetup
# from ...models.misc import (
#     CoinTossWinnerModel,
#     CoinTossContext,
#     CoinTossChoice,
#     KickReceiveContext,
#     KickReceiveChoiceModel,
# )

if TYPE_CHECKING:
    from pylon.state.drive_record import DriveRecord
    from pylon.state.play_record import PlayRecord, ScoringTypeEnum


logger = logging.getLogger(__name__)


class NFLRules(LeagueRules):
    MINUTES_PER_QUARTER = 15
    QUARTERS_PER_HALF = 2
    TIMEOUTS_PER_HALF = 3
    KICKOFF_SPOT = 35
    EXTRA_POINT_SPOT = 15

    SCORING_VALUES = {
        ScoringTypeEnum.TOUCHDOWN: 6,
        ScoringTypeEnum.FIELD_GOAL: 3,
        ScoringTypeEnum.SAFETY: 2,
        ScoringTypeEnum.EXTRA_POINT_KICK: 1,
        ScoringTypeEnum.EXTRA_POINT_TWO_POINT: 2,
    }

    def start_game(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        """Return a KickoffSetup describing the opening kickoff."""
        raise NotImplementedError

    def start_half(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        """Return a KickoffSetup describing the kickoff to start the half."""
        raise NotImplementedError

    def is_game_over(self, game_state: "GameState") -> bool:
        """Return True if the game should end."""
        raise NotImplementedError

    def is_half_over(self, game_state: "GameState") -> bool:
        """Return True if the half should end."""
        raise NotImplementedError

    def is_drive_over(self, game_state: "GameState") -> bool:
        """Return True if the drive should end."""
        raise NotImplementedError

    def on_drive_end(
        self, game_state: "GameState", drive_record: "DriveRecord"
    ) -> None:
        """Return a DriveEndDecision describing what should happen next."""
        raise NotImplementedError

    def on_play_end(self, game_state: "GameState", play_record: "PlayRecord") -> None:
        """Return a PlayEndDecision describing what should happen next."""
        raise NotImplementedError
