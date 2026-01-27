"""Kickoff engine: simulates kickoff distance, return, and touchback logic."""

import logging

from ..state.game_state import GameState
from ..models.registry import ModelRegistry
from ..state.play_record import PlayParticipantType, PlayExecutionData
from ..domain.athlete import Athlete
from ..domain.rules.base import LeagueRules
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
    KickoffDistanceModel,
    KickoffDistanceContext,
    KickoffTouchbackDecisionModel,
    KickoffTouchbackDecisionContext,
)


logger = logging.getLogger(__name__)


class KickoffPlayEngine:
    def __init__(
        self,
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        play_execution_data: PlayExecutionData,
        rules: LeagueRules,
    ) -> None:
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.play_data = play_execution_data
        self.rules = rules

    def run(self) -> None:
        # we should not have any play call for a kickoff
        assert self.play_data.off_play_call is None

        kicker = self.get_kicker()
        returner = self.get_returner()

        kickoff_spot = self.game_state.possession.ball_position

        # Determine how far the kickoff travels
        kickoff_distance = self.get_kickoff_distance(kicker)
        logger.debug(f"Kickoff travels {kickoff_distance} yards")

        # Calculate where ball lands (from kicking team's perspective)
        # If kickoff_distance >= (100 - kickoff_spot), ball reaches/enters endzone
        distance_to_goal = 100 - kickoff_spot

        if kickoff_distance >= distance_to_goal:
            # Ball enters the endzone
            yards_into_endzone = kickoff_distance - distance_to_goal
            landing_spot_from_receiving_goal = -yards_into_endzone
            logger.debug(f"Kickoff reaches endzone, {yards_into_endzone} yards deep")

            # Decide if returner takes touchback or attempts return
            take_touchback = self.get_touchback_decision(
                returner, landing_spot_from_receiving_goal
            )

            if take_touchback:
                logger.debug("Returner takes touchback")
                # Get league's touchback spot
                touchback_spot = self.rules.get_touchback_spot(is_kickoff=True)

                # Calculate yards gained: from kickoff_spot to receiving team's touchback_spot
                # After field flip, receiving team will be at touchback_spot
                net_yards = distance_to_goal - touchback_spot

                self.play_data.add_participant(kicker.uid, PlayParticipantType.KICKER)
                self.play_data.set_yards_gained(net_yards)
                self.play_data.set_is_possession_change(True)
                self.play_data.set_is_turnover(False)
                self.play_data.set_is_clock_running(
                    False
                )  # Clock doesn't run on touchback
                self.play_data.set_is_fg_attempt(False)
                return
        else:
            # Ball lands before endzone
            landing_spot_from_receiving_goal = distance_to_goal - kickoff_distance
            logger.debug(
                f"Kickoff lands at receiving team's {landing_spot_from_receiving_goal} yard line"
            )

        # Ball is being returned (either landed short or returner chose to return from endzone)
        return_distance = self.get_return_distance(returner)
        logger.debug(f"Return distance: {return_distance} yards")

        # Calculate final spot (from receiving team's goal line)
        # If ball landed at their 9 and return is 30 yards, they end up at their 39
        final_spot_from_receiving_goal = (
            landing_spot_from_receiving_goal + return_distance
        )

        # Convert to yards_gained for possession update:
        # From kicking team perspective before flip:
        # Kicker at 35, ball ends at (100 - final_spot) = (100 - 39) = 61
        # yards_gained = 61 - 35 = 26
        # After flip, receiving team ball position = 39
        final_spot_from_kicking_goal = 100 - final_spot_from_receiving_goal
        net_yards = final_spot_from_kicking_goal - kickoff_spot

        self.play_data.add_participant(kicker.uid, PlayParticipantType.KICKER)
        self.play_data.add_participant(returner.uid, PlayParticipantType.RETURNER)
        self.play_data.set_yards_gained(net_yards)
        self.play_data.set_is_possession_change(True)
        self.play_data.set_is_turnover(False)
        self.play_data.set_is_clock_running(True)  # Clock runs after kickoff return
        self.play_data.set_is_fg_attempt(False)

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
        return distance

    def get_kickoff_distance(self, kicker: Athlete) -> int:
        """Get how far the kickoff travels."""
        kickoff_distance_model = self.models.get_typed(
            "kickoff_distance",
            KickoffDistanceModel,  # type: ignore
        )
        distance = kickoff_distance_model.execute(
            KickoffDistanceContext(
                game_state=self.game_state,
                rng=self.rng,
                kicker=kicker,
            )
        )
        return distance

    def get_touchback_decision(self, returner: Athlete, landing_spot: int) -> bool:
        """Determine if returner takes touchback or attempts return."""
        touchback_decision_model = self.models.get_typed(
            "kickoff_touchback_decision",
            KickoffTouchbackDecisionModel,  # type: ignore
        )
        take_touchback = touchback_decision_model.execute(
            KickoffTouchbackDecisionContext(
                game_state=self.game_state,
                rng=self.rng,
                returner=returner,
                landing_spot=landing_spot,
            )
        )
        return take_touchback
