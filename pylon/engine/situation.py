import logging

from .score import ScoreboardManager
from ..model.game.team import Team
from .clock import GameClock


logger = logging.getLogger(__name__)


class Situation:
    def __init__(
        self,
        score: ScoreboardManager,
        pos_team: Team,
        clock: GameClock,
        down: int = 1,
        distance: int = 10,
        yardline: int = 25,
    ) -> None:
        self.score = score
        self.possession_team = pos_team
        self.clock = clock
        self.down = down
        self.distance = distance
        self.yardline = yardline

    def __str__(self) -> str:
        return f"Situation(score={self.score}, pos_team={self.possession_team}, clock={self.clock}, down={self.down}, distance={self.distance}, yardline={self.yardline})"
   
    def __repr__(self) -> str:
        return self.__str__()