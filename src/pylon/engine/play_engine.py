"""Play-level orchestrator: selects calls, assigns personnel, and records outcomes."""

import logging
from typing import Dict, List

from ..domain.team import Team
from ..domain.rules.base import LeagueRules
from ...sim.rng import RNG
from .run_engine import RunPlayEngine
from .pass_engine import PassPlayEngine
from .punt_engine import PuntPlayEngine
from .kickoff_engine import KickoffPlayEngine
from .field_goal_engine import FieldGoalPlayEngine
from ..state.game_state import GameState
from ..state.play_record import PlayExecutionData
from ..models.registry import ModelRegistry
from ..domain.playbook import (
    PlayTypeEnum,
    PlayCall,
    PlaySideEnum,
)
from ..domain.athlete import Athlete, AthletePositionEnum
from ..models.misc import (
    PlayTimeElapsedModel,
    PlayTimeElapsedContext,
    PrePlayClockRunoffModel,
    PrePlayClockRunoffContext,
)
from ..models.offense import (
    PlayTypeModel,
    PlayTypeContext,
    OffensivePlayCallModel,
    OffPlayCallContext,
)
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

        # How much time does the team run off before the snap?
        if self.game_state.clock.clock_is_running:
            self.set_preplay_clock_runoff(play_data)
        else:
            play_data.set_preplay_clock_runoff(0)

        # Get offensive and defensive play calls
        self.set_play_calls(play_data)
        self.execute_play_based_on_type(play_data)
        self.set_play_time_elapsed(play_data)

        # Set whether clock is running after the play (for now, assume it keeps running)
        play_data.set_is_clock_running(self.game_state.clock.clock_is_running)

        # TODO: These should be set by the specific play engines, not here
        # For now, default to no possession change or turnover
        if play_data.is_possession_change is None:
            play_data.set_is_possession_change(False)
        if play_data.is_turnover is None:
            play_data.set_is_turnover(False)

        return play_data

    def execute_play_based_on_type(self, play_data: PlayExecutionData) -> None:
        """Execute the play based on its type."""
        assert play_data.play_type is not None

        if play_data.play_type.is_run():
            RunPlayEngine(self.game_state, self.models, self.rng, play_data).run()

        elif play_data.play_type.is_pass():
            PassPlayEngine(self.game_state, self.models, self.rng, play_data).run()

        elif play_data.play_type.is_punt():
            PuntPlayEngine(self.game_state, self.models, self.rng, play_data).run()

        elif play_data.play_type.is_field_goal():
            FieldGoalPlayEngine(self.game_state, self.models, self.rng, play_data).run()

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
        play_type = self.get_play_type()
        play_data.set_play_type(play_type)

        off_playbook = self.game_state.pos_team.off_playbook
        if off_playbook is None or len(off_playbook) == 0:
            logger.warning(
                "Skipping offensive play-call model because offense has no playbook or no plays."
            )
            off_play_call = None
        else:
            off_play_call = self.get_off_playcall(play_type)
        play_data.set_off_play_call(off_play_call)

        def_playbook = self.game_state.def_team.def_playbook
        if def_playbook is None or len(def_playbook) == 0:
            logger.warning(
                "Skipping defensive play-call model because defense has no playbook or no plays."
            )
            def_play_call = None
        else:
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

    # ==============================
    # Getters (mainly models)
    # ==============================
    def get_play_type(self) -> PlayTypeEnum:
        play_type_model = self.models.get_typed(
            "play_type",
            PlayTypeModel,  # type: ignore
        )
        return play_type_model.execute(PlayTypeContext(self.game_state, self.rng))

    def get_off_playcall(self, play_type: PlayTypeEnum) -> PlayCall:
        off_play_call_model = self.models.get_typed(
            "off_play_call",
            OffensivePlayCallModel,  # type: ignore
        )
        off_play_call = off_play_call_model.execute(
            OffPlayCallContext(self.game_state, self.rng, play_type)
        )

        self._validate_playcall(off_play_call, PlaySideEnum.OFFENSE)
        return off_play_call

    def get_def_playcall(self, play_data: PlayExecutionData) -> PlayCall:
        assert play_data.play_type is not None

        def_play_call_model = self.models.get_typed(
            "def_play_call",
            DefensivePlayCallModel,  # type: ignore
        )
        # We pass the offensive play type to the defensive play call model so it
        # can condition its call on the offense's call. This is mainly done to
        # prevent the defense from calling a punt return (or something similarly
        # unrealistic) if the offense calls a run or pass. In the future, we may
        # want to pass more information about the offensive call. For now, just the
        # play type is sufficient.
        def_play_call = def_play_call_model.execute(
            DefPlayCallContext(self.game_state, self.rng, play_data.play_type)
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

    def _set_kickoff_playcalls(self, play_data: PlayExecutionData) -> None:
        play_data.set_play_type(PlayTypeEnum.KICKOFF)
        off_playbook = self.game_state.pos_team.off_playbook
        if off_playbook is None or len(off_playbook) == 0:
            logger.warning(
                "Cannot set kickoff offensive play call: offense has no playbook or no plays."
            )
            play_data.set_off_play_call(None)
        else:
            off_kickoff_plays = off_playbook.get_by_type(PlayTypeEnum.KICKOFF)
            if not off_kickoff_plays:
                logger.warning(
                    "No KICKOFF plays found in offensive playbook; kickoff will run without offensive play call."
                )
                play_data.set_off_play_call(None)
            else:
                if len(off_kickoff_plays) > 1:
                    logger.warning(
                        "Multiple kickoff plays found in offensive playbook; using the first one."
                    )
                # TODO: we should really have the kickoff play call model select from the
                # available kickoff plays rather than just taking the first one.
                play_data.set_off_play_call(off_kickoff_plays[0])

        def_playbook = self.game_state.def_team.def_playbook
        if def_playbook is None or len(def_playbook) == 0:
            logger.warning(
                "Cannot set kickoff defensive play call: defense has no playbook or no plays."
            )
            play_data.set_def_play_call(None)
        else:
            def_kickoff_plays = def_playbook.get_by_type(PlayTypeEnum.KICKOFF_RETURN)
            if not def_kickoff_plays:
                logger.warning(
                    "No KICKOFF_RETURN plays found in defensive playbook; kickoff will run without defensive play call."
                )
                play_data.set_def_play_call(None)
            else:
                if len(def_kickoff_plays) > 1:
                    logger.warning(
                        "Multiple kickoff plays found in defensive playbook; using the first one."
                    )
                # TODO: we should really have the kickoff play call model select from the
                # available kickoff plays rather than just taking the first one.
                play_data.set_def_play_call(def_kickoff_plays[0])

    def _run_kickoff(self, play_data: PlayExecutionData) -> None:
        self._set_kickoff_playcalls(play_data)

        self.game_state.consume_pending_kickoff()

        # Kickoffs don't have pre-play clock runoff
        play_data.set_preplay_clock_runoff(0)

        KickoffPlayEngine(
            self.game_state, self.models, self.rng, play_data, self.rules
        ).run()

        # Set time elapsed for the kickoff play
        self.set_play_time_elapsed(play_data)
