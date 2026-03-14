"""Run play engine: handles execution of rushing plays including yardage outcomes."""

import logging

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_record import PlayExecutionData, PlayParticipantType
from ..domain.athlete import Athlete
from ..domain.playbook import PlayTypeEnum
from ...sim.rng import RNG
from ..models.personnel import (
    RusherSelectionContext,
    RusherSelectionModel,
    OffensivePlayerAssignmentModel,
    DefensivePlayerAssignmentModel,
    PlayerAssignmentContext,
)
from ..models.offense import RushYardsGainedContext, RushYardsGainedModel
from ..models.possession import (
    FumbleContext,
    FumbleModel,
    FumbleRecoveryContext,
    FumbleRecoveryModel,
)


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
        assert self.play_data.play_type == PlayTypeEnum.RUN

        # Assign personnel for this run play
        self.assign_personnel()

        rusher = self.get_rusher()
        yards_gained = self.get_yds_gained(rusher)

        # Set run-specific analytics
        self.play_data.set_yards_gained(yards_gained)
        self.play_data.set_run_gap("C")  # TODO: Determine actual gap (A, B, C, etc.)

        # Check for fumble by rusher
        is_fumble = self.is_fumble(rusher)
        self.play_data.set_is_fumble(is_fumble)
        if is_fumble:
            recovering_team = self.get_fumble_recovery(rusher)
            self.play_data.set_fumble_recovered_by_team(recovering_team)
            logger.debug(f"Fumble by rusher, recovered by {recovering_team.name}")

        logger.debug(f"Run Play Yards Gained: {yards_gained}")

        self.play_data.add_participant(rusher.uid, PlayParticipantType.RUSHER)

    def assign_personnel(self) -> None:
        """Assign offensive and defensive personnel for the run play."""
        off_personnel_model = self.models.get_typed(
            "offensive_play_personnel_assignment",
            OffensivePlayerAssignmentModel,  # type: ignore
        )
        off_personnel = off_personnel_model.execute(
            PlayerAssignmentContext(
                self.game_state,
                self.rng,
                self.play_data.off_play_call,
                play_type=self.play_data.play_type,
            )
        )
        self.play_data.set_off_personnel_assignments(off_personnel)

        def_personnel_model = self.models.get_typed(
            "defensive_play_personnel_assignment",
            DefensivePlayerAssignmentModel,  # type: ignore
        )
        def_personnel = def_personnel_model.execute(
            PlayerAssignmentContext(
                self.game_state,
                self.rng,
                self.play_data.def_play_call,
                play_type=self.play_data.play_type,
            )
        )
        self.play_data.set_def_personnel_assignments(def_personnel)

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

    def is_fumble(self, ball_carrier: Athlete) -> bool:
        """Determine if a ball carrier fumbles."""
        fumble_model = self.models.get_typed(
            "fumble",
            FumbleModel,  # type: ignore
        )
        is_fumble = fumble_model.execute(
            FumbleContext(
                self.game_state,
                self.rng,
                ball_carrier,
            )
        )
        return is_fumble

    def get_fumble_recovery(self, fumbler: Athlete):
        """Determine which team recovers a fumble."""
        from ..domain.team import Team

        recovery_model = self.models.get_typed(
            "fumble_recovery",
            FumbleRecoveryModel,  # type: ignore
        )
        recovering_team: Team = recovery_model.execute(
            FumbleRecoveryContext(
                self.game_state,
                self.rng,
                fumbler,
                self.play_data.off_personnel_assignments,
                self.play_data.def_personnel_assignments,
            )
        )
        return recovering_team
