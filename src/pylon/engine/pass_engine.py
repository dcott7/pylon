"""Pass play engine: selects passer/receiver and computes pass outcomes."""

import logging

from sim.rng import RNG
from ..domain.athlete import Athlete
from ..domain.team import Team
from ..domain.playbook import PlayTypeEnum
from ..state.game_state import GameState
from ..state.play_record import PlayExecutionData, PlayParticipantType
from ..models.registry import ModelRegistry
from ..models.personnel import (
    PasserSelectionContext,
    TargettedSelectionContext,
    PasserSelectionModel,
    TargettedSelectionModel,
    OffensivePlayerAssignmentModel,
    DefensivePlayerAssignmentModel,
    PlayerAssignmentContext,
    SackerSelectionContext,
    SackerSelectionModel,
    InterceptorSelectionContext,
    InterceptorSelectionModel,
)
from ..models.offense import (
    AirYardsContext,
    CompletionContext,
    YardsAfterCatchContext,
    AirYardsModel,
    CompletionModel,
    YardsAfterCatchModel,
)
from ..models.defense import (
    SackContext,
    SackModel,
    SackYardsContext,
    SackYardsModel,
    InterceptionContext,
    InterceptionModel,
    InterceptionReturnYardsContext,
    InterceptionReturnYardsModel,
)
from ..models.possession import (
    FumbleContext,
    FumbleModel,
    FumbleRecoveryContext,
    FumbleRecoveryModel,
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
        assert self.play_data.play_type == PlayTypeEnum.PASS

        # Assign personnel for this pass play
        self.assign_personnel()

        passer = self.get_passer()
        self.play_data.add_participant(passer, PlayParticipantType.PASSER)

        # Check for sack before attempting the pass
        is_sack = self.is_sack()
        self.play_data.set_is_sack(is_sack)

        if is_sack:
            # Sack: negative yardage, no completion/interception
            sacker = self.get_sacker()
            self.play_data.add_participant(sacker, PlayParticipantType.TACKLER)

            sack_yards = self.get_sack_yards()
            self.play_data.set_yards_gained(-sack_yards)
            self.play_data.set_air_yards(0)
            self.play_data.set_is_complete(False)
            self.play_data.set_yards_after_catch(0)
            self.play_data.set_is_interception(False)
            logger.debug(f"Sack by {sacker.uid} for {sack_yards} yards lost.")

            # Check for fumble on sack
            is_fumble = self.is_fumble(passer)
            self.play_data.set_is_fumble(is_fumble)
            if is_fumble:
                recovering_team = self.get_fumble_recovery(passer)
                self.play_data.set_fumble_recovered_by_team(recovering_team)
                logger.debug(f"Fumble recovered by {recovering_team.name}")
            return

        # TODO: Add QB scramble optionality logic here in future enhancements
        # current assumption: if not a sack, the pass attempt proceeds (no QB scramble logic yet)

        # No sack: proceed with pass attempt
        targetted = self.get_targetted_receiver()
        self.play_data.add_participant(targetted, PlayParticipantType.RECEIVER)

        air_yards = self.get_airyards()
        self.play_data.set_air_yards(air_yards)

        is_complete = self.is_completed(passer, targetted, air_yards)
        self.play_data.set_is_complete(is_complete)

        yards_gained: int = 0
        if is_complete:
            yards_gained += air_yards
            yac = self.get_yac(targetted)
            yards_gained += yac
            self.play_data.set_yards_after_catch(yac)
            # Completed passes cannot be intercepted
            self.play_data.set_is_interception(False)

            # Check for fumble by receiver after catch
            is_fumble = self.is_fumble(targetted)
            self.play_data.set_is_fumble(is_fumble)
            if is_fumble:
                recovering_team = self.get_fumble_recovery(targetted)
                self.play_data.set_fumble_recovered_by_team(recovering_team)
                logger.debug(f"Fumble by receiver, recovered by {recovering_team.name}")
        else:  # not a completion, check for interception
            self.play_data.set_yards_after_catch(0)
            is_intercepted = self.is_intercepted(passer, targetted, air_yards)

            if is_intercepted:
                # Interception return yards are handled via model
                self.play_data.set_is_interception(True)

                interceptor = self.get_interceptor()
                self.play_data.add_participant(
                    interceptor, PlayParticipantType.INTERCEPTOR
                )
                return_yards = self.get_interception_return_yards(interceptor)
                yards_gained = -return_yards
                logger.debug("Pass was intercepted.")

                # Check for fumble by interceptor during return
                is_fumble = self.is_fumble(interceptor)
                self.play_data.set_is_fumble(is_fumble)
                if is_fumble:
                    recovering_team = self.get_fumble_recovery(interceptor)
                    self.play_data.set_fumble_recovered_by_team(recovering_team)
                    logger.debug(
                        f"Fumble by interceptor, recovered by {recovering_team.name}"
                    )

            else:  # not an interception, incomplete pass
                self.play_data.set_is_interception(False)
                self.play_data.set_is_fumble(False)
                # clock stops on incompletions
                self.play_data.set_is_clock_running(False)
                logger.debug("Pass was incomplete.")

        self.play_data.set_yards_gained(yards_gained)
        logger.debug(f"Pass Play Yards Gained: {yards_gained}")

    def assign_personnel(self) -> None:
        """Assign offensive and defensive personnel for the pass play."""
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

    def get_sacker(self) -> Athlete:
        sacker_select_model = self.models.get_typed(
            "sacker_selection",
            SackerSelectionModel,  # type: ignore
        )
        sacker = sacker_select_model.execute(
            SackerSelectionContext(
                self.game_state,
                self.rng,
                self.play_data.def_personnel_assignments,
            )
        )
        logger.debug(f"Sacker selected: {sacker.first_name} {sacker.last_name}")
        return sacker

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

    def is_sack(self) -> bool:
        """Determine if the defense sacks the quarterback."""
        sack_model = self.models.get_typed(
            "sack",
            SackModel,  # type: ignore
        )
        is_sack = sack_model.execute(
            SackContext(
                self.game_state,
                self.rng,
                self.play_data.off_personnel_assignments,
                self.play_data.def_personnel_assignments,
            )
        )
        return is_sack

    def get_sack_yards(self) -> int:
        """
        Calculate yards lost on a sack.
        Returns positive value representing yards lost (e.g., 7 means 7 yards lost).
        """
        sack_yards_model = self.models.get_typed(
            "sack_yards",
            SackYardsModel,  # type: ignore
        )
        yards_lost = sack_yards_model.execute(
            SackYardsContext(
                self.game_state,
                self.rng,
                self.play_data.off_personnel_assignments,
                self.play_data.def_personnel_assignments,
            )
        )
        return yards_lost

    def is_intercepted(
        self, passer: Athlete, targetted: Athlete, air_yards: int
    ) -> bool:
        """
        Determine if an incomplete pass is intercepted.
        """
        interception_model = self.models.get_typed(
            "interception",
            InterceptionModel,  # type: ignore
        )
        is_interception = interception_model.execute(
            InterceptionContext(
                self.game_state,
                self.rng,
                passer,
                targetted,
                air_yards,
                self.play_data.off_personnel_assignments,
                self.play_data.def_personnel_assignments,
            )
        )
        return is_interception

    def get_interception_return_yards(self, interceptor: Athlete) -> int:
        """Determine interception return yards (positive value)."""
        return_yards_model = self.models.get_typed(
            "interception_return_yards",
            InterceptionReturnYardsModel,  # type: ignore
        )
        return_yards = return_yards_model.execute(
            InterceptionReturnYardsContext(
                self.game_state,
                self.rng,
                interceptor,
                self.play_data.off_personnel_assignments,
                self.play_data.def_personnel_assignments,
            )
        )
        return return_yards

    def get_interceptor(self) -> Athlete:
        """Select a defensive player to record the interception."""
        interceptor_select_model = self.models.get_typed(
            "interceptor_selection",
            InterceptorSelectionModel,  # type: ignore
        )
        interceptor = interceptor_select_model.execute(
            InterceptorSelectionContext(
                self.game_state,
                self.rng,
                self.play_data.def_personnel_assignments,
            )
        )
        logger.debug(
            f"Interceptor selected: {interceptor.first_name} {interceptor.last_name}"
        )
        return interceptor

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

    def get_fumble_recovery(self, fumbler: Athlete) -> Team:
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
