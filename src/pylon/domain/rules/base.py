from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
import logging
from typing import TYPE_CHECKING

from ...domain.team import Team
from ...models.registry import ModelRegistry
from ...rng import RNG

if TYPE_CHECKING:
    from ...state.game_state import GameState
    from ...state.drive_state import DriveState
    from ...state.play_state import PlayState


logger = logging.getLogger(__name__)


class LeagueRulesError(Exception):
    pass


class KickoffSetup:
    def __init__(
        self, kicking_team: Team, receiving_team: Team, kickoff_spot: int
    ) -> None:
        assert kickoff_spot >= 1
        assert kickoff_spot <= 99
        assert kicking_team != receiving_team
        self.kicking_team = kicking_team
        self.receiving_team = receiving_team
        self.kickoff_spot = kickoff_spot


class ExtraPointSetup:
    def __init__(self, kicking_team: Team, spot: int) -> None:
        assert spot >= 1
        assert spot <= 99
        self.kicking_team = kicking_team
        self.spot = spot


class ScoringTypeEnum(Enum):
    NONE = "none"
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    SAFETY = "safety"
    EXTRA_POINT_KICK = "extra_point_kick"
    EXTRA_POINT_TWO_POINT = "extra_point_two_point"


class LeagueRules(ABC):
    MINUTES_PER_QUARTER: int
    QUARTERS_PER_HALF: int
    TIMEOUTS_PER_HALF: int

    @abstractmethod
    def start_game(
        self,
        game_state: "GameState",
        models: ModelRegistry,
        rng: RNG,
    ) -> None:
        """Called at the start of the game."""
        ...

    @abstractmethod
    def start_half(
        self,
        game_state: "GameState",
        models: ModelRegistry,
        rng: RNG,
    ) -> None:
        """Called at the start of each half."""
        ...

    @abstractmethod
    def on_drive_end(
        self,
        game_state: "GameState",
        drive_state: "DriveState",
    ) -> None: ...

    @abstractmethod
    def on_play_end(
        self,
        game_state: "GameState",
        play_state: "PlayState",
    ) -> None: ...
