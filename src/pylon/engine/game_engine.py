import logging
from simpy import Environment
from typing import Any, List, Optional


from .drive_engine import DriveEngine
from ..state.game_state import GameState
from ..state.game_clock import GameClock
from ..models.registry import ModelRegistry, TypedModel
from ..rng import RNG
from ..domain.rules.base import LeagueRules
from ..domain.rules.nfl import NFLRules
from ..domain.team import Team
from ..state.scoreboard_state import Scoreboard
from .timeout import TimeoutManager
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
        env: Environment,
        home_team: Team,
        away_team: Team,
        user_models: Optional[List[TypedModel[Any, Any]]] = None,
        rng: RNG = RNG(),
        rules: LeagueRules = NFLRules(),  # type: ignore
    ) -> None:
        self.env = env
        self.models = ModelRegistry()
        self.rng = rng
        self.rules = rules
        self.game_state = GameState(
            home_team=home_team,
            away_team=away_team,
            clock=GameClock(
                self.env,
                self.rules.MINUTES_PER_QUARTER,
                self.rules.QUARTERS_PER_HALF * 2,
            ),
            scoreboard=Scoreboard(home_team=home_team, away_team=away_team),
            timeout_mgr=TimeoutManager(
                home_team=home_team,
                away_team=away_team,
                max_timeouts=self.rules.TIMEOUTS_PER_HALF,
            ),
        )
        self.user_models = user_models or []
        self._register_default_models()
        self._override_default_models(self.user_models)

    def run(self) -> None:
        self.env.process(self._game_loop())
        self.env.run()

    def _game_loop(self):
        self.game_state.start_game()  # Initialize game state
        # Apply the league-specific rules for starting the game. This is
        # typically where the opening kickoff is set up.
        self.rules.start_game(self.game_state, self.models, self.rng)

        while not self.game_state.is_game_over():
            drive_record = DriveEngine(
                self.env, self.game_state, self.models, self.rng, self.rules
            ).run()

            if self.game_state.is_end_of_half():
                self.rules.start_half(self.game_state, self.models, self.rng)

            self.game_state.add_drive(drive_record)
            yield self.env.timeout(0)  # allow SimPy scheduling

        self.game_state.end_game()

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
        self.models.register_model(DefaultDefensivePlayCallModel())

    def _override_default_models(self, models: List[TypedModel[Any, Any]]) -> None:
        for model in models:
            self.models.register_model(model, override=True)
