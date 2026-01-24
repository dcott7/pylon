import logging
from typing import Dict, List

from ..domain.team import Team
from ..domain.rules.base import LeagueRules
from ..rng import RNG
from .run_engine import RunPlayEngine
from .pass_engine import PassPlayEngine
from .punt_engine import PuntPlayEngine
from .kickoff_engine import KickoffPlayEngine
from .field_goal_engine import FieldGoalPlayEngine
from ..state.game_state import GameState
from ..state.play_record import PlayExecutionData
from ..models.registry import ModelRegistry
from ..domain.playbook import PlayTypeEnum, PlayCall, PlaySideEnum
from ..domain.athlete import Athlete, AthletePositionEnum
from ..models.misc import (
    PlayTimeElapsedModel,
    PlayTimeElapsedContext,
    PrePlayClockRunoffModel,
    PrePlayClockRunoffContext,
)
from ..models.offense import OffensivePlayCallModel, OffPlayCallContext
from ..models.defense import DefensivePlayCallModel, DefPlayCallContext
from ..models.personnel import (
    OffensivePlayerAssignmentModel,
    DefensivePlayerAssignmentModel,
    PlayerAssignmentContext,
)


logger = logging.getLogger(__name__)


class PlayEngineError(Exception):
    pass


class PlayExecutionError(PlayEngineError):
    pass


class PlayEngine:
    """
    Engine to simulate a single play within a game. The PlayEngine
    is responsible for coordinating the various models to execute
    the play and generate a PlayExecutionData object that will be
    used to update the game state.
    """

    def __init__(
        self,
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        rules: LeagueRules,
    ) -> None:
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.rules = rules

    # ==============================
    # Main Execution
    # ==============================
    def run(self) -> PlayExecutionData:
        play_data = PlayExecutionData()

        if self.game_state.has_pending_kickoff():
            self._run_kickoff(play_data)
            return play_data

        if self.game_state.clock.clock_is_running:
            # how much time does the team run off before the play starts?
            self.set_preplay_clock_runoff(play_data)

        self.set_play_calls(play_data)
        self.set_personnel_assignments(play_data)
        self.execute_play_based_on_type(play_data)
        self.set_play_time_elapsed(play_data)

        return play_data

    def execute_play_based_on_type(self, play_data: PlayExecutionData) -> None:
        """Execute the play based on its type."""

        play_data.assert_is_ready_to_execute()

        assert play_data.off_play_call is not None
        assert play_data.def_play_call is not None
        assert play_data.off_personnel_assignments
        assert play_data.def_personnel_assignments

        if play_data.off_play_call.play_type == PlayTypeEnum.RUN:
            RunPlayEngine(  # TODO: remove GameState parameter from RunPlayEngine
                self.game_state, self.models, self.rng, play_data
            ).run()

        elif play_data.off_play_call.play_type == PlayTypeEnum.PASS:
            PassPlayEngine(  # TODO: remove GameState parameter from PassPlayEngine
                self.game_state, self.models, self.rng, play_data
            ).run()

        elif play_data.off_play_call.play_type == PlayTypeEnum.PUNT:
            PuntPlayEngine(  # TODO: remove GameState parameter from PuntPlayEngine
                self.game_state, self.models, self.rng, play_data
            ).run()

        elif play_data.off_play_call.play_type == PlayTypeEnum.FIELD_GOAL:
            FieldGoalPlayEngine(  # TODO: remove GameState parameter from PuntPlayEngine
                self.game_state, self.models, self.rng, play_data
            ).run()

    # ==============================
    # Setters
    # ==============================
    def set_preplay_clock_runoff(self, play_data: PlayExecutionData) -> None:
        preplay_runoff_model = self.models.get_typed(
            "preplay_clock_runoff",
            PrePlayClockRunoffModel,  # type: ignore
        )
        preplay_runoff = preplay_runoff_model.execute(
            PrePlayClockRunoffContext(self.game_state, self.rng)
        )
        play_data.set_preplay_clock_runoff(preplay_runoff)

    def set_play_calls(self, play_data: PlayExecutionData) -> None:
        off_play_call = self.get_off_playcall(play_data)
        play_data.set_off_play_call(off_play_call)

        def_play_call = self.get_def_playcall(play_data)
        play_data.set_def_play_call(def_play_call)

    def set_play_time_elapsed(self, play_data: PlayExecutionData) -> None:
        time_elapsed_model = self.models.get_typed(
            "play_time_elapsed",
            PlayTimeElapsedModel,  # type: ignore
        )
        time_elapsed = time_elapsed_model.execute(
            PlayTimeElapsedContext(
                self.game_state, self.rng
            )  # TODO: exposes more context
        )
        play_data.set_time_elapsed(time_elapsed)

    def set_personnel_assignments(self, play_data: PlayExecutionData) -> None:
        off_personnel_assignments = self.get_off_play_personnel(play_data)
        play_data.set_off_personnel_assignments(off_personnel_assignments)

        def_personnel_assignments = self.get_def_play_personnel(play_data)
        play_data.set_def_personnel_assignments(def_personnel_assignments)

    # ==============================
    # Getters (mainly models)
    # ==============================
    def get_off_playcall(self, play_data: PlayExecutionData) -> PlayCall:
        off_play_call_model = self.models.get_typed(
            "off_play_call",
            OffensivePlayCallModel,  # type: ignore
        )
        off_play_call = off_play_call_model.execute(
            OffPlayCallContext(self.game_state, self.rng)
        )

        self._validate_playcall(off_play_call, PlaySideEnum.OFFENSE)
        return off_play_call

    def get_def_playcall(self, play_data: PlayExecutionData) -> PlayCall:
        def_play_call_model = self.models.get_typed(
            "def_play_call",
            DefensivePlayCallModel,  # type: ignore
        )
        def_play_call = def_play_call_model.execute(
            DefPlayCallContext(self.game_state, self.rng)
        )

        self._validate_playcall(def_play_call, PlaySideEnum.DEFENSE)
        return def_play_call

    def get_off_play_personnel(
        self, play_data: PlayExecutionData
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        assert play_data.off_play_call is not None

        play_personnel_model = self.models.get_typed(
            "offensive_play_personnel_assignment",
            OffensivePlayerAssignmentModel,  # type: ignore
        )
        personnel_assignments = play_personnel_model.execute(
            PlayerAssignmentContext(self.game_state, self.rng, play_data.off_play_call)
        )
        self.validate_off_personnel(personnel_assignments)  # ensure validity
        return personnel_assignments

    def get_def_play_personnel(
        self, play_data: PlayExecutionData
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        assert play_data.def_play_call is not None

        play_personnel_model = self.models.get_typed(
            "defensive_play_personnel_assignment",
            DefensivePlayerAssignmentModel,  # type: ignore
        )
        personnel_assignments = play_personnel_model.execute(
            PlayerAssignmentContext(self.game_state, self.rng, play_data.def_play_call)
        )
        self.validate_def_personnel(personnel_assignments)  # ensure validity
        return personnel_assignments

    # ==============================
    # Validators
    # ==============================
    def _validate_playcall(
        self, play_call: PlayCall, expected_type: PlaySideEnum
    ) -> None:
        if play_call.side != expected_type:
            raise PlayExecutionError(f"Invalid expected play side: {expected_type}")
        # other checks?

    def validate_off_personnel(
        self, personnel_assignments: Dict[AthletePositionEnum, List[Athlete]]
    ):
        self._validate_personnel(personnel_assignments, self.game_state.pos_team)

    def validate_def_personnel(
        self, personnel_assignments: Dict[AthletePositionEnum, List[Athlete]]
    ):
        self._validate_personnel(personnel_assignments, self.game_state.def_team)

    def _validate_personnel(
        self,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
        team: Team,
    ) -> None:
        """
        Validate that the teams have enough personnel to run
        plays and those players are on the team's roster.
        """
        total_players = 0
        for _, players in personnel_assignments.items():
            for player in players:
                total_players += 1
                if player not in team.roster:
                    msg = (
                        f"Player {player.first_name} {player.last_name} "
                        f"not on team {team.name} roster"
                    )
                    logger.error(msg)
                    raise PlayExecutionError(msg)

        if total_players > 11:
            msg = (
                f"Too many players assigned for the play: "
                f"assigned {total_players}, maximum allowed is 11"
            )
            logger.error(msg)
            raise PlayExecutionError(msg)

        if total_players < 11:
            msg = (
                f"Not enough players assigned for the play: "
                f"assigned {total_players}, minimum required is 11"
            )
            logger.error(msg)
            raise PlayExecutionError(msg)

    def _run_kickoff(self, play_data: PlayExecutionData) -> None:
        self.game_state.consume_pending_kickoff()

        KickoffPlayEngine(self.game_state, self.models, self.rng, play_data).run()
