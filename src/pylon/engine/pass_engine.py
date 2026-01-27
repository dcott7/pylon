"""Pass play engine: selects passer/receiver and computes pass outcomes."""

import logging

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_record import PlayExecutionData, PlayParticipantType
from ..domain.athlete import Athlete
from ..domain.playbook import PlayTypeEnum
from ..rng import RNG
from ..models.personnel import (
    PasserSelectionContext,
    TargettedSelectionContext,
    PasserSelectionModel,
    TargettedSelectionModel,
)
from ..models.offense import (
    AirYardsContext,
    CompletionContext,
    YardsAfterCatchContext,
    AirYardsModel,
    CompletionModel,
    YardsAfterCatchModel,
)


logger = logging.getLogger(__name__)


class PassPlayEngine:
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
        assert self.play_data.off_play_call.play_type == PlayTypeEnum.PASS

        passer = self.get_passer()
        targetted = self.get_targetted_receiver()
        air_yards = self.get_airyards()
        is_complete = self.is_completed(passer, targetted, air_yards)

        yards_gained: int = 0
        if is_complete:
            yards_gained += air_yards
            yards_gained += self.get_yac(targetted)

        # TODO: Add interception logic
        # else:
        #     is_intercepted = self.is_intercepted(passer, targetted, air_yards)
        #     if is_intercepted:
        #         self.play_record.is_turnover = True
        #         logger.debug("Pass was intercepted.")
        #     else:
        #         self.play_record.is_clock_running = False  # incomplete pass stops clock
        #         logger.debug("Pass was incomplete.")

        self.play_data.set_yards_gained(yards_gained)
        logger.debug(f"Pass Play Yards Gained: {yards_gained}")
        # TODO: Add logic for tackler, fumble etc.
        self.play_data.add_participant(passer.uid, PlayParticipantType.PASSER)
        self.play_data.add_participant(targetted.uid, PlayParticipantType.RECEIVER)

    def get_passer(self) -> Athlete:
        passer_select_model = self.models.get_typed(
            "passer_selection",
            PasserSelectionModel,  # type: ignore
        )
        passer = passer_select_model.execute(
            PasserSelectionContext(
                self.game_state, self.rng, self.play_data.off_personnel_assignments
            )
        )
        logger.debug(f"Passer selected: {passer.first_name} {passer.last_name}")
        return passer

    def get_targetted_receiver(self) -> Athlete:
        targetted_select_model = self.models.get_typed(
            "targetted_selection",
            TargettedSelectionModel,  # type: ignore
        )
        targetted = targetted_select_model.execute(
            TargettedSelectionContext(
                self.game_state, self.rng, self.play_data.off_personnel_assignments
            )
        )
        logger.debug(
            f"Targetted selected: {targetted.first_name} {targetted.last_name}"
        )
        return targetted

    def get_airyards(self) -> int:
        airyard_model = self.models.get_typed(
            "airyards",
            AirYardsModel,  # type: ignore
        )
        airyards = airyard_model.execute(
            AirYardsContext(
                self.game_state, self.rng, self.play_data.off_personnel_assignments
            )
        )
        logger.debug(f"Air Yards: {airyards}")
        return airyards

    def is_completed(self, passer: Athlete, targetted: Athlete, air_yards: int) -> bool:
        completion_model = self.models.get_typed(
            "completion",
            CompletionModel,  # type: ignore
        )
        complete = completion_model.execute(
            CompletionContext(
                self.game_state,
                self.rng,
                self.play_data.off_personnel_assignments,
                passer,
                targetted,
                air_yards,
            )
        )
        logger.debug(
            f"Completion: {complete} from {passer.first_name} {passer.last_name} "
            f"to {targetted.first_name} {targetted.last_name}"
        )
        return complete

    def get_yac(self, receiver: Athlete) -> int:
        yac_model = self.models.get_typed(
            "yac",
            YardsAfterCatchModel,  # type: ignore
        )
        yac = yac_model.execute(
            YardsAfterCatchContext(
                self.game_state,
                self.rng,
                self.play_data.off_personnel_assignments,
            )
        )
        logger.debug(f"Yards After Catch: {yac}")
        return yac
