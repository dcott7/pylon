import logging

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_record import PlayParticipantType, PlayExecutionData
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
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        play_execution_data: PlayExecutionData,
    ) -> None:
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.play_data = play_execution_data

    def run(self) -> None:
        # we should not have any play call for a kickoff
        assert self.play_data.off_play_call is None

        kicker = self.get_kicker()
        returner = self.get_returner()
        # TODO: implement onside kickoffs, kickoff distance, touchback, etc.
        # distance from the returning team's goal line
        return_distance = self.get_return_distance(returner)

        self.play_data.add_participant(kicker.uid, PlayParticipantType.KICKER)
        self.play_data.add_participant(returner.uid, PlayParticipantType.RETURNER)
        # current distance is from where the kicking team is kicking off from (usually their 35)
        # the kicking team is in possession of the ball at that spot prior to the kickoff
        self.play_data.set_yards_gained(-return_distance)
        self.play_data.set_is_possession_change(True)

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
