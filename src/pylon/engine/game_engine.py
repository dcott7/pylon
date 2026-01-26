import logging
from typing import Any, List, Optional

from .drive_engine import DriveEngine
from ..state.game_state import GameState, GameExecutionData
from ..models.registry import ModelRegistry, TypedModel
from ..rng import RNG
from ..domain.rules.base import LeagueRules
from ..domain.rules.nfl import NFLRules
from ..domain.team import Team
from ..models.personnel import (
    DefaultPasserSelectionModel,
    DefaultRusherSelectionModel,
    DefaultOffensivePlayerAssignmentModel,
    DefaultDefensivePlayerAssignmentModel,
    DefaultPunterSelectionModel,
    DefaultTargettedSelectionModel,
    DefaultPuntReturnerSelectionModel,
    DefaultKickoffReturnerSelectionModel,
    DefaultKickerSelectionModel,
    DefaultPlaceKickerSelectionModel,
)
from ..models.offense import (
    DefaultOffensivePlayCallModel,
    DefaultAirYardsModel,
    DefaultCompletionModel,
    DefaultRushYardsGainedModel,
    DefaultYardsAfterCatchModel,
)
from ..models.defense import DefaultDefensivePlayCallModel
from ..models.specialteams import (
    DefaultPuntDistanceModel,
    DefaultPuntReturnDistanceModel,
    DefaultKickoffReturnDistanceModel,
    DefaultKickoffDistanceModel,
    DefaultKickoffTouchbackDecisionModel,
)
from ..models.misc import (
    DefaultPlayTimeElapsedModel,
    DefaultPrePlayClockRunoffModel,
    DefaultCoinTossWinnerModel,
    DefaultKickReceiveChoiceModel,
)


logger = logging.getLogger(__name__)


class GameEngine:
    """
    Main game engine responsible for managing the game loop and integrating
    various models, and for updating the GameState based on play outcomes.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        user_models: Optional[List[TypedModel[Any, Any]]] = None,
        rng: RNG = RNG(),
        rules: LeagueRules = NFLRules(),  # type: ignore
        max_drives: Optional[int] = 100,
    ) -> None:
        self.models = ModelRegistry()
        self.rng = rng
        self.rules = rules
        self.max_drives = max_drives
        self.game_state = GameState(
            home_team=home_team,
            away_team=away_team,
            minutes_per_quarter=self.rules.MINUTES_PER_QUARTER,
            quarters_per_half=self.rules.QUARTERS_PER_HALF,
            max_timeouts=self.rules.TIMEOUTS_PER_HALF,
        )
        self.user_models = user_models or []
        self._register_default_models()
        self._override_default_models(self.user_models)

    def run(self) -> None:
        self._game_loop()

    def _game_loop(self):
        game_data = GameExecutionData()
        # implementation is tbd...
        game_data.start_game()  # Initialize game state
        # Apply the league-specific rules for starting the game. This is
        # typically where the opening kickoff is set up.
        self.rules.start_game(self.game_state, self.models, self.rng)

        drive_count = 0
        while not self.rules.is_game_over(self.game_state):
            drive_record = DriveEngine(
                self.game_state, self.models, self.rng, self.rules
            ).run()
            drive_count += 1
            if self.max_drives is not None and drive_count >= self.max_drives:
                logger.info("Maximum drives reached. Ending game.")
                break

            if self.rules.is_half_over(self.game_state):
                # possible scheduling of post halftime kickoff, etc.
                self.rules.start_half(self.game_state, self.models, self.rng)

            game_data.add_drive(drive_record)

        # implementation is tbd...
        game_data.end_game()

    def _register_default_models(self) -> None:
        self.models.register_model(DefaultOffensivePlayCallModel())
        self.models.register_model(DefaultAirYardsModel())
        self.models.register_model(DefaultCompletionModel())
        self.models.register_model(DefaultPasserSelectionModel())
        self.models.register_model(DefaultTargettedSelectionModel())
        self.models.register_model(DefaultRusherSelectionModel())
        self.models.register_model(DefaultRushYardsGainedModel())
        self.models.register_model(DefaultYardsAfterCatchModel())
        self.models.register_model(DefaultOffensivePlayerAssignmentModel())
        self.models.register_model(DefaultDefensivePlayerAssignmentModel())
        self.models.register_model(DefaultPunterSelectionModel())
        self.models.register_model(DefaultPuntReturnerSelectionModel())
        self.models.register_model(DefaultPuntDistanceModel())
        self.models.register_model(DefaultPuntReturnDistanceModel())
        self.models.register_model(DefaultKickerSelectionModel())
        self.models.register_model(DefaultPlayTimeElapsedModel())
        self.models.register_model(DefaultPrePlayClockRunoffModel())
        self.models.register_model(DefaultCoinTossWinnerModel())
        self.models.register_model(DefaultKickReceiveChoiceModel())
        self.models.register_model(DefaultPlaceKickerSelectionModel())
        self.models.register_model(DefaultKickoffReturnerSelectionModel())
        self.models.register_model(DefaultKickoffReturnDistanceModel())
        self.models.register_model(DefaultKickoffDistanceModel())
        self.models.register_model(DefaultKickoffTouchbackDecisionModel())
        self.models.register_model(DefaultDefensivePlayCallModel())

    def _override_default_models(self, models: List[TypedModel[Any, Any]]) -> None:
        for model in models:
            self.models.register_model(model, override=True)
