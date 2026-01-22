import logging
from typing import Dict, List
from simpy import Environment

from ..domain.team import Team
from ..domain.rules.base import LeagueRules
from ..rng import RNG
from .run_engine import RunPlayEngine
from .pass_engine import PassPlayEngine
from .punt_engine import PuntPlayEngine
from .kickoff_engine import KickoffPlayEngine
from .field_goal_engine import FieldGoalPlayEngine
from ..state.game_state import GameState
from ..state.play_record import PlayRecord, PlayExecutionData
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
    Engine to simulate a single play within a game.
    """

    def __init__(
        self,
        env: Environment,
        game_state: GameState,
        models: ModelRegistry,
        rng: RNG,
        rules: LeagueRules,
    ) -> None:
        self.env = env
        self.game_state = game_state
        self.models = models
        self.rng = rng
        self.rules = rules

    def run(self) -> PlayRecord:
        # initialize a play record
        play_record = PlayRecord(self.game_state)
        play_data = PlayExecutionData()

        if self.game_state.has_pending_kickoff():
            self._run_kickoff(play_data)
            self.game_state.update(play_data)
            play_record.set_end_state(self.game_state)
            return play_record

        if play_record.start_is_clock_running:
            # how much time does the team run off before the play starts?
            self.set_preplay_clock_runoff(play_record)

        self.set_play_calls(play_record)
        self.set_personnel_assignments(play_record)
        self.execute_play_based_on_type(play_record)
        self.set_play_time_elapsed(play_record)

        play_record.finalize()  # set the end state based on play results
        self.rules.on_play_end(
            self.game_state, play_record
        )  # update game state based on play outcome

        return play_record

    def set_preplay_clock_runoff(self, play_record: PlayRecord) -> None:
        preplay_runoff_model = self.models.get_typed(
            "preplay_clock_runoff",
            PrePlayClockRunoffModel,  # type: ignore
        )
        preplay_runoff = preplay_runoff_model.execute(
            PrePlayClockRunoffContext(self.game_state, self.rng)
        )
        play_record.preplay_clock_runoff = preplay_runoff

    def set_play_calls(self, play_record: PlayRecord) -> None:
        off_play_call = self.get_off_playcall(play_record)
        play_record.off_play_call = off_play_call

        def_play_call = self.get_def_playcall(play_record)
        play_record.def_play_call = def_play_call

    def set_play_time_elapsed(self, play_record: PlayRecord) -> None:
        time_elapsed_model = self.models.get_typed(
            "play_time_elapsed",
            PlayTimeElapsedModel,  # type: ignore
        )
        time_elapsed = time_elapsed_model.execute(
            PlayTimeElapsedContext(
                self.game_state, self.rng
            )  # TODO: exposes more context
        )
        play_record.time_elapsed = time_elapsed

    def set_personnel_assignments(self, play_record: PlayRecord) -> None:
        off_personnel_assignments = self.get_off_play_personnel(play_record)
        play_record.off_personnel_assignments = off_personnel_assignments

        def_personnel_assignments = self.get_def_play_personnel(play_record)
        play_record.def_personnel_assignments = def_personnel_assignments

    def get_off_playcall(self, play_record: PlayRecord) -> PlayCall:
        off_play_call_model = self.models.get_typed(
            "off_play_call",
            OffensivePlayCallModel,  # type: ignore
        )
        off_play_call = off_play_call_model.execute(
            OffPlayCallContext(self.game_state, self.rng)
        )

        self._validate_playcall(off_play_call, PlaySideEnum.OFFENSE)
        play_record.off_play_call = off_play_call
        logger.info(f"Offensive play called: {off_play_call}")
        return off_play_call

    def get_def_playcall(self, play_record: PlayRecord) -> PlayCall:
        def_play_call_model = self.models.get_typed(
            "def_play_call",
            DefensivePlayCallModel,  # type: ignore
        )
        def_play_call = def_play_call_model.execute(
            DefPlayCallContext(self.game_state, self.rng)
        )

        self._validate_playcall(def_play_call, PlaySideEnum.DEFENSE)
        play_record.def_play_call = def_play_call
        logger.info(f"Defensive play called: {def_play_call}")
        return def_play_call

    def _validate_playcall(
        self, play_call: PlayCall, expected_type: PlaySideEnum
    ) -> None:
        if play_call.side != expected_type:
            raise PlayExecutionError(f"Invalid expected play side: {expected_type}")
        # other checks?

    def get_off_play_personnel(
        self, play_record: PlayRecord
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        assert play_record.off_play_call is not None

        play_personnel_model = self.models.get_typed(
            "offensive_play_personnel_assignment",
            OffensivePlayerAssignmentModel,  # type: ignore
        )
        personnel_assignments = play_personnel_model.execute(
            PlayerAssignmentContext(
                self.game_state, self.rng, play_record.off_play_call
            )
        )
        self.validate_off_personnel(personnel_assignments)  # ensure validity
        play_record.off_personnel_assignments = personnel_assignments
        logger.debug(f"Personnel assignments for play: {personnel_assignments}")
        return personnel_assignments

    def get_def_play_personnel(
        self, play_record: PlayRecord
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        assert play_record.def_play_call is not None

        play_personnel_model = self.models.get_typed(
            "defensive_play_personnel_assignment",
            DefensivePlayerAssignmentModel,  # type: ignore
        )
        personnel_assignments = play_personnel_model.execute(
            PlayerAssignmentContext(
                self.game_state, self.rng, play_record.def_play_call
            )
        )
        self.validate_def_personnel(personnel_assignments)  # ensure validity
        play_record.def_personnel_assignments = personnel_assignments
        logger.debug(f"Personnel assignments for play: {personnel_assignments}")
        return personnel_assignments

    def execute_play_based_on_type(self, play_record: PlayRecord) -> None:
        """Execute the play based on its type."""

        play_record.assert_is_ready_to_execute()

        assert play_record.off_play_call is not None
        assert play_record.def_play_call is not None
        assert play_record.off_personnel_assignments
        assert play_record.def_personnel_assignments

        if play_record.off_play_call.play_type == PlayTypeEnum.RUN:
            RunPlayEngine(  # TODO: remove GameState parameter from RunPlayEngine
                self.env, self.game_state, self.models, self.rng, play_record
            ).run()

        elif play_record.off_play_call.play_type == PlayTypeEnum.PASS:
            PassPlayEngine(  # TODO: remove GameState parameter from PassPlayEngine
                self.env, self.game_state, self.models, self.rng, play_record
            ).run()

        elif play_record.off_play_call.play_type == PlayTypeEnum.PUNT:
            PuntPlayEngine(  # TODO: remove GameState parameter from PuntPlayEngine
                self.env, self.game_state, self.models, self.rng, play_record
            ).run()

        elif play_record.off_play_call.play_type == PlayTypeEnum.FIELD_GOAL:
            FieldGoalPlayEngine(  # TODO: remove GameState parameter from PuntPlayEngine
                self.env, self.game_state, self.models, self.rng, play_record
            ).run()

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

        KickoffPlayEngine(
            self.env, self.game_state, self.models, self.rng, play_data
        ).run()
