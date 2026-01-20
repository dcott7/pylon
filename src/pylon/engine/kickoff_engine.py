import logging
from simpy import Environment

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_state import PlayState, PlayParticipantType
from ..domain.athlete import Athlete
from ..rng import RNG
from ..models.personnel import (
    PlaceKickerSelectionModel,
    PlaceKickerSelectionContext,
    KickoffReturnerSelectionContext,
    KickoffReturnerSelectionModel,
)
from ..models.specialteams import (
    KickoffReturnDistanceModel,
    KickoffReturnDistanceContext,
)


logger = logging.getLogger(__name__)


class KickoffPlayEngine:
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
        # we should not have any play call for a kickoff
        assert self.play_state.off_play_call is None

        kicker = self.get_kicker()
        returner = self.get_returner()
        # TODO: implement onside kickoffs, kickoff distance, touchback, etc.
        # distance from the returning team's goal line
        return_distance = self.get_return_distance(returner)

        self.play_state.add_participant(kicker.uid, PlayParticipantType.KICKER)
        self.play_state.add_participant(returner.uid, PlayParticipantType.RETURNER)
        # current distance is from where the kicking team is kicking off from (usually their 35)
        # the kicking team is in possession of the ball at that spot prior to the kickoff
        self.play_state.yards_gained = (
            -return_distance
        )  # this will change once we implement kickoff distance
        self.play_state.is_possession_change = True

    def get_kicker(self) -> Athlete:
        kicker_select_model = self.models.get_typed(
            "place_kicker_selection",
            PlaceKickerSelectionModel,  # type: ignore
        )
        kicker = kicker_select_model.execute(
            PlaceKickerSelectionContext(self.game_state, self.rng)
        )
        logger.debug(f"Kicker selected: {kicker.first_name} {kicker.last_name}")
        return kicker

    def get_returner(self) -> Athlete:
        returner_select_model = self.models.get_typed(
            "kickoff_returner_selection",
            KickoffReturnerSelectionModel,  # type: ignore
        )
        returner = returner_select_model.execute(
            KickoffReturnerSelectionContext(self.game_state, self.rng)
        )
        logger.debug(f"Returner selected: {returner.first_name} {returner.last_name}")
        return returner

    def get_return_distance(self, returner: Athlete) -> int:
        kickoff_return_distance_model = self.models.get_typed(
            "kickoff_return_distance",
            KickoffReturnDistanceModel,  # type: ignore
        )
        distance = kickoff_return_distance_model.execute(
            KickoffReturnDistanceContext(
                game_state=self.game_state,
                rng=self.rng,
                returner=returner,
            )
        )
        logger.debug(f"Kickoff return distance: {distance} yards")
        return distance
