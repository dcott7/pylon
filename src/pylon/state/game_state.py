from __future__ import annotations
from enum import auto, Enum
import logging
from typing import TYPE_CHECKING, Dict, Optional, List

from .game_clock import GameClock
from .possession_state import PossessionState
from .scoreboard_state import Scoreboard
from ..domain.team import Team
from ..domain.rules.base import KickoffSetup, ExtraPointSetup
from ..engine.timeout import TimeoutManager
from ..models.misc import CoinTossChoice

if TYPE_CHECKING:
    from .drive_state import DriveState
    from .play_state import PlayState


logger = logging.getLogger(__name__)


class GameStateError(Exception):
    pass


class GameStateConsistencyError(GameStateError):
    pass


class GameStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()


class GameState:
    """
    Authoritative, mutable, live game state owned by the GameEngine.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        clock: GameClock,
        scoreboard: Scoreboard,
        timeout_mgr: TimeoutManager,
    ) -> None:
        self._game_status = GameStatus.NOT_STARTED
        self._home_team = home_team
        self._away_team = away_team
        self._clock = clock
        self._scoreboard = scoreboard
        self._timeout_mgr = timeout_mgr
        self._coin_toss_winner: Optional[Team] = None
        self._coin_toss_winner_choice: Optional[CoinTossChoice] = None
        self._pending_kickoff: Optional[KickoffSetup] = None
        self._pending_extra_point: Optional[ExtraPointSetup] = None
        self.ot_possessions: Dict[str, int] = {
            self._home_team.uid: 0,
            self._away_team.uid: 0,
        }  # team uid -> number of OT possessions
        self.first_ot_possession_complete: bool
        # default starting possession
        self._possession = PossessionState(
            pos_team=home_team,
            ball_position=35,  # kickoff yard line (TODO: this should be configurable)
            down=1,
            distance=10,
        )
        self.last_drive: Optional["DriveState"] = None
        self.drives: List["DriveState"] = []

    # ===============================
    # Life Cycle Methods
    # ===============================
    def start_game(self) -> None:
        if self._game_status != GameStatus.NOT_STARTED:
            logger.error("Attempted to start a game that has already started")

            raise GameStateError("Game already started")
        self._game_status = GameStatus.IN_PROGRESS
        logger.info("Game started")

    def end_game(self) -> None:
        if self._game_status != GameStatus.IN_PROGRESS:
            logger.error("Attempted to end a game that is not in progress")
            raise GameStateError("Game not in progress")

        self._game_status = GameStatus.COMPLETE
        logger.info("Game ended")

    def is_game_over(self) -> bool:
        if self.clock.is_expired():
            return True
        # TODO: add overtime rules, mercy rule, etc.
        return False

    def is_end_of_half(self) -> bool:
        if self.clock.current_quarter in [2, 4] and self.clock.time_remaining <= 0:
            return True
        return False

    def is_drive_over(self) -> bool:
        if (
            self.is_game_over()
            or self.is_end_of_half()
            or self.last_play_was_scoring()
            or self.possession_changed()
            or self.last_play_was_kick()
        ):
            return True

        return False

    # ===============================
    # Core State Manipulation
    # ===============================

    def update_possession(self, play_state: "PlayState") -> None:
        assert play_state.end_pos_team is not None
        assert play_state.end_yardline is not None
        assert play_state.end_down is not None
        assert play_state.end_distance is not None
        self._possession.update_possession(play_state.end_pos_team)
        self._possession.update_down(play_state.end_down)
        self._possession.update_distance(play_state.end_distance)
        self._possession.update_ball_position(play_state.end_yardline)
        if play_state.is_possession_change:
            self._possession.flip_field()

    def add_drive(self, drive_state: "DriveState") -> None:
        if not drive_state.is_finalized():
            msg = "Attempted to add unfinalized DriveState to GameState."
            logger.error(msg)
            raise GameStateError(msg)

        self.last_drive = drive_state
        self._assert_consistency()  # ensure consistency between GameState and DriveState

        self.drives.append(drive_state)
        logger.debug(f"Drive {drive_state.uid} added to game state.")

    def set_possession(self, team: Team) -> None:
        self._possession.set_possession(team)
        logger.debug(f"Possession set to team: {team.name}")

    # ===============================
    # Pending phase transitions
    # ===============================
    def set_pending_kickoff(self, kickoff_setup: KickoffSetup) -> None:
        self.possession.set_state(
            kickoff_setup.kicking_team, kickoff_setup.kickoff_spot, down=0, distance=0
        )
        self._pending_kickoff = kickoff_setup

    def consume_pending_kickoff(self) -> KickoffSetup:
        if self._pending_kickoff is None:
            msg = "No pending kickoff to consume."
            logger.error(msg)
            raise GameStateError(msg)

        ko = self._pending_kickoff
        self._pending_kickoff = None
        return ko

    def has_pending_kickoff(self) -> bool:
        return self._pending_kickoff is not None

    def set_pending_extra_point(self, extra_point_setup: ExtraPointSetup) -> None:
        self.possession.set_state(
            extra_point_setup.kicking_team,
            extra_point_setup.spot,
            down=0,
            distance=extra_point_setup.spot,
        )
        self._pending_extra_point = extra_point_setup

    def consume_pending_extra_point(self) -> ExtraPointSetup:
        if self._pending_extra_point is None:
            msg = "No pending extra point attempt to consume."
            logger.error(msg)
            raise GameStateError(msg)

        ep = self._pending_extra_point
        self._pending_extra_point = None
        return ep

    def has_pending_extra_point(self) -> bool:
        return self._pending_extra_point is not None

    # ===============================
    # Derived state queries
    # ===============================
    def opponent(self, team: Team) -> Team:
        if team == self._home_team:
            return self._away_team
        elif team == self._away_team:
            return self._home_team

        msg = f"Team {team.name} is not part of this game."
        logger.error(msg)
        raise GameStateError(msg)

    def leading_team(self) -> Team | None:
        return self._scoreboard.leader()

    def lead(self, team: Team) -> int:
        scores = self.scoreboard.score()
        teams = list(scores.keys())
        values = list(scores.values())

        if values[0] == values[1]:
            return 0

        if teams[0] == team:
            return values[0] - values[1]
        elif teams[1] == team:
            return values[1] - values[0]

        logger.error(f"Team {team} is not part of this game")
        raise GameStateError(f"Team {team} is not part of this game")

    def last_play_was_scoring(self) -> bool:
        if self.last_drive is None or self.last_drive.last_play is None:
            return False

        return self.last_drive.last_play.is_scoring_play

    def last_play_was_kick(self) -> bool:
        if self.last_drive is None or self.last_drive.last_play is None:
            return False

        return (
            self.last_drive.last_play.off_play_call is not None
            and self.last_drive.last_play.off_play_call.play_type.is_kick()
        )

    def possession_changed(self) -> bool:
        if self.last_drive is None or self.last_drive.last_play is None:
            return False

        return self.last_drive.last_play.is_possession_change

    def set_coin_toss_winner(self, team: Team) -> None:
        if self._coin_toss_winner is not None:
            logger.error("Attempted to set coin toss winner more than once")
            raise GameStateError("Coin toss winner already set")

        self._coin_toss_winner = team
        logger.info(f"Coin toss winner set to team: {team.name}")

    def set_coin_toss_winner_choice(self, choice: CoinTossChoice) -> None:
        if self._coin_toss_winner is None:
            logger.error("Attempted to set coin toss winner choice before winner")
            raise GameStateError("Coin toss winner not set")

        self._coin_toss_winner_choice = choice
        logger.info(
            f"Coin toss winner {self._coin_toss_winner.name} chose to {choice.name}"
        )

    # ===============================
    # Accessors
    # ===============================

    @property
    def possession(self) -> PossessionState:
        return self._possession

    @property
    def pos_team(self) -> Team:
        return self._possession.pos_team

    @property
    def def_team(self) -> Team:
        return (
            self._away_team
            if self.possession.pos_team == self._home_team
            else self._home_team
        )

    @property
    def game_status(self) -> GameStatus:
        return self._game_status

    @property
    def home_team(self) -> Team:
        return self._home_team

    @property
    def away_team(self) -> Team:
        return self._away_team

    @property
    def clock(self) -> GameClock:
        return self._clock

    @property
    def scoreboard(self) -> Scoreboard:
        return self._scoreboard

    @property
    def timeout_mgr(self) -> TimeoutManager:
        return self._timeout_mgr

    @property
    def coin_toss_winner(self) -> Optional[Team]:
        return self._coin_toss_winner

    @property
    def coin_toss_winner_choice(self) -> Optional[CoinTossChoice]:
        return self._coin_toss_winner_choice

    # ===============================
    # Internal Consistency Checks
    # ===============================

    def _assert_consistency(self) -> None:
        """Assert internal consistency between GameState and DriveState/PlayState."""
        assert self.last_drive is not None
        ld = self.last_drive

        if ld.end_pos_team != self.possession.pos_team:
            msg = (
                f"End possession team {ld.end_pos_team} does not match current "
                f"possession team {self.possession.pos_team}."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_def_team != self.def_team:
            msg = (
                f"End defense team {ld.end_def_team} does not match current "
                f"defense team {self.def_team}."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_yardline != self.possession.ball_position:
            msg = (
                f"End yardline ({ld.end_yardline}) does not match current "
                f"ball position ({self.possession.ball_position})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_time != self.clock.time_remaining:
            msg = (
                f"End time ({ld.end_time}) does not match current clock "
                f"time ({self.clock.time_remaining})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_quarter != self.clock.current_quarter:
            msg = (
                f"End quarter ({ld.end_quarter}) does not match current "
                f"quarter ({self.clock.current_quarter})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_pos_team_score != self.scoreboard.current_score(
            self.possession.pos_team
        ):
            msg = (
                f"End possession team score ({ld.end_pos_team_score}) does not "
                f"match current score ({self.scoreboard.current_score(self.possession.pos_team)})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)

        if ld.end_def_team_score != self.scoreboard.current_score(self.def_team):
            msg = (
                f"End possession team score ({ld.end_pos_team_score}) does not "
                f"match current score ({self.scoreboard.current_score(self.possession.pos_team)})."
            )
            logger.error(msg)
            raise GameStateConsistencyError(msg)


class GameStateUpdater:
    """Applies PlayState updates to the GameState."""

    def __init__(self, game_state: GameState) -> None:
        self._game_state = game_state

    def apply_play(self, play_state: "PlayState") -> None:
        self._update_clock(play_state)
        if play_state.is_scoring_play:
            self._update_scoreboard(play_state)
        self._update_possession(play_state)
        self._update_timeouts(play_state)

    def _update_clock(self, play_state: "PlayState") -> None:
        assert play_state.end_quarter is not None
        assert play_state.end_time is not None
        assert play_state.end_is_clock_running is not None
        assert play_state.time_elapsed is not None
        assert play_state.end_is_clock_running is not None

        # consume the time elapsed for this play
        self._game_state.clock.env.timeout(play_state.time_elapsed)
        self._game_state.clock.clock_is_running = play_state.end_is_clock_running

    def _update_scoreboard(self, play_state: "PlayState") -> None:
        assert play_state.is_scoring_play
        assert play_state.scoring_team is not None
        assert play_state.end_pos_team_score is not None
        self._game_state.scoreboard.add_points(
            play_state.scoring_team,
            play_state.end_pos_team_score - play_state.start_pos_team_score,
        )

    def _update_possession(self, play_state: "PlayState") -> None:
        self._game_state.update_possession(play_state)

    def _update_timeouts(self, play_state: "PlayState") -> None:
        # TODO: implement timeout updates
        pass
