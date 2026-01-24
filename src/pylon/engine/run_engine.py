import logging

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_record import PlayExecutionData, PlayParticipantType
from ..domain.athlete import Athlete
from ..domain.playbook import PlayTypeEnum
from ..rng import RNG
from ..models.personnel import (
    RusherSelectionContext,
    RusherSelectionModel,
)
from ..models.offense import RushYardsGainedContext, RushYardsGainedModel


logger = logging.getLogger(__name__)


class RunPlayEngine:
    def __init__(
        self,
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        play_data: PlayExecutionData,
    ) -> None:
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.play_data = play_data

    def run(self) -> None:
        assert self.play_data.off_play_call is not None
        assert self.play_data.off_play_call.play_type == PlayTypeEnum.RUN

        rusher = self.get_rusher()
        yards_gained = self.get_yds_gained(rusher)

        # TODO: Add tackler, fumble, touchdown logic here
        self.play_data.set_yards_gained(yards_gained)
        logger.debug(f"Run Play Yards Gained: {yards_gained}")

        self.play_data.add_participant(rusher.uid, PlayParticipantType.RUSHER)

    def get_rusher(self) -> Athlete:
        rusher_select_model = self.models.get_typed(
            "rusher_selection",
            RusherSelectionModel,  # type: ignore
        )
        rusher = rusher_select_model.execute(
            RusherSelectionContext(
                self.game_state, self.rng, self.play_data.off_personnel_assignments
            )
        )
        logger.debug(f"Rusher selected: {rusher.first_name} {rusher.last_name}")
        return rusher

    def get_yds_gained(self, rusher: Athlete) -> int:
        assert self.play_data.off_play_call is not None

        rush_yards_model = self.models.get_typed(
            "rush_yards_gained",
            RushYardsGainedModel,  # type: ignore
        )
        yards_gained = rush_yards_model.execute(
            RushYardsGainedContext(
                self.game_state, self.rng, self.play_data.off_play_call, rusher
            )
        )
        logger.info(
            f"Rusher {rusher.first_name} {rusher.last_name} gained {yards_gained} yards"
        )
        return yards_gained
