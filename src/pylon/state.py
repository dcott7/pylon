from enum import auto, Enum
import logging
from typing import Dict, Optional

from .clock import GameClock
from .scoreboard import Scoreboard
from .entities.team import Team
from .timeout import TimeoutManager


logger = logging.getLogger(__name__)


class GameStatusEnum(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()


class PossessionState:
    """
    Immutable snapshot of the possession state.

    Attributes:
        pos_team (Team): The team currently in possession of the ball.
        ball_position (int): The current position of the ball on the field (yard line) relative to the offense's end zone.
        down (int): The current down (1 to 4).
        distance (int): The yards to go for a first down.
    """

    def __init__(
        self, pos_team: Team, ball_position: int, down: int, distance: int
    ) -> None:
        self._pos_team = pos_team
        self._ball_position = ball_position
        self._down = down
        self._distance = distance

    @property
    def pos_team(self) -> Team:
        return self._pos_team

    @property
    def ball_position(self) -> int:
        return self._ball_position

    @property
    def down(self) -> int:
        return self._down

    @property
    def distance(self) -> int:
        return self._distance


class GameState:
    """
    Authoritative game state owned by the GameEngine.

    This object does NOT enforce rules.
    Mutation is restricted to the engine and rule processors.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        clock: GameClock,
        scoreboard: Scoreboard,
        timeout_mgr: TimeoutManager,
    ) -> None:
        self._game_status = GameStatusEnum.NOT_STARTED
        self._home_team = home_team
        self._away_team = away_team
        self._clock = clock
        self._scoreboard = scoreboard
        self._timeout_mgr = timeout_mgr
        self.overtime_start_time: Optional[int] = None
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
        raise ValueError(f"Team {team} is not part of this game")

    @property
    def possession(self) -> PossessionState:
        return self._possession

    @property
    def defending_team(self) -> Team:
        return (
            self._away_team
            if self.possession.pos_team == self._home_team
            else self._home_team
        )

    @property
    def game_status(self) -> GameStatusEnum:
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
