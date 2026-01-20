import logging
from simpy import Environment

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_state import PlayState, PlayParticipantType
from ..domain.athlete import Athlete
from ..domain.playbook import PlayTypeEnum
from ..rng import RNG
from ..models.personnel import (
    PunterSelectionContext,
    PunterSelectionModel,
    PuntReturnerSelectionContext,
    PuntReturnerSelectionModel,
)
from ..models.specialteams import (
    PuntDistanceContext,
    PuntDistanceModel,
    PuntReturnDistanceContext,
    PuntReturnDistanceModel,
)


logger = logging.getLogger(__name__)


class PuntPlayEngine:
    def __init__(
        self,
        env: Environment,
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        play_state: PlayState,
    ) -> None:
        self.env = env
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.play_state = play_state

    def run(self) -> None:
        assert self.play_state.off_play_call is not None
        assert self.play_state.off_play_call.play_type == PlayTypeEnum.PUNT

        punter = self.get_punter()
        punt_distance = self.get_punt_distance()
        returner = self.get_returner()
        return_distance = self.get_return_distance(returner)
        # TODO: Add logic for touchback, fair catch, etc.

        self.play_state.add_participant(punter.uid, PlayParticipantType.PUNTER)
        self.play_state.add_participant(returner.uid, PlayParticipantType.RETURNER)
        self.play_state.yards_gained = punt_distance - return_distance
        self.play_state.is_possession_change = True

    def get_punter(self) -> Athlete:
        punter_select_model = self.models.get_typed(
            "punter_selection",
            PunterSelectionModel,  # type: ignore
        )
        punter = punter_select_model.execute(
            PunterSelectionContext(
                self.game_state, self.rng, self.play_state.off_personnel_assignments
            )
        )
        logger.debug(f"Punter selected: {punter.first_name} {punter.last_name}")
        return punter

    def get_returner(self) -> Athlete:
        returner_select_model = self.models.get_typed(
            "punt_returner_selection",
            PuntReturnerSelectionModel,  # type: ignore
        )
        returner = returner_select_model.execute(
            PuntReturnerSelectionContext(
                self.game_state, self.rng, self.play_state.off_personnel_assignments
            )
        )
        logger.debug(f"Returner selected: {returner.first_name} {returner.last_name}")
        return returner

    def get_punt_distance(self) -> int:
        punt_dist_model = self.models.get_typed(
            "punt_distance",
            PuntDistanceModel,  # type: ignore
        )
        punt_distance = punt_dist_model.execute(
            PuntDistanceContext(
                self.game_state, self.rng, self.play_state.off_personnel_assignments
            )
        )
        logger.debug(f"Punt Distance: {punt_distance}")
        return punt_distance

    def get_return_distance(self, returner: Athlete) -> int:
        return_distance_model = self.models.get_typed(
            "punt_return_distance",
            PuntReturnDistanceModel,  # type: ignore
        )
        return_distance = return_distance_model.execute(
            PuntReturnDistanceContext(
                self.game_state,
                self.rng,
                self.play_state.off_personnel_assignments,
                returner,
            )
        )
        logger.debug(f"Return Distance: {return_distance}")
        return return_distance
