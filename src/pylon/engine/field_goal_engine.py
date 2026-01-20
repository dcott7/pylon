import logging
from simpy import Environment

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_state import PlayState, PlayParticipantType
from ..domain.athlete import Athlete
from ..domain.playbook import PlayTypeEnum
from ..rng import RNG
from ..models.personnel import KickerSelectionContext, KickerSelectionModel
from ..models.specialteams import FieldGoalContext, FieldGoalModel


logger = logging.getLogger(__name__)


class FieldGoalPlayEngine:
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
        assert self.play_state.off_play_call.play_type == PlayTypeEnum.FIELD_GOAL

        kicker = self.get_kicker()
        is_fg_good = self.is_fg_good(kicker)

        yards_gained: int = 0
        if is_fg_good:
            yards_gained = self.play_state.start_yardline  # yards to goal line
            logger.debug(
                f"Field Goal is GOOD. Yards Gained: {yards_gained} "
                "(field goal distance)"
            )

        self.play_state.yards_gained = yards_gained
        logger.debug(f"Field Goal Play Yards Gained: {yards_gained}")
        self.play_state.add_participant(kicker.uid, PlayParticipantType.KICKER)

    def get_kicker(self) -> Athlete:
        kicker_select_model = self.models.get_typed(
            "kicker_selection",
            KickerSelectionModel,  # type: ignore
        )
        kicker = kicker_select_model.execute(
            KickerSelectionContext(
                self.game_state, self.rng, self.play_state.off_personnel_assignments
            )
        )
        logger.debug(f"Kicker selected: {kicker.first_name} {kicker.last_name}")
        return kicker

    def is_fg_good(self, kicker: Athlete) -> bool:
        fg_model = self.models.get_typed(
            "field_goal_success",
            FieldGoalModel,  # type: ignore
        )
        is_fg_good = fg_model.execute(
            FieldGoalContext(
                self.game_state,
                self.rng,
                self.play_state.off_personnel_assignments,
                kicker,
            )
        )
        logger.debug(
            f"Field Goal Success: {is_fg_good} with kicker {kicker.first_name} {kicker.last_name}"
        )
        return is_fg_good
