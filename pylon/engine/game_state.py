from enum import auto, Enum
import logging

from .clock import GameClock
from .score import ScoreboardManager
from ..model.game.team import Team
from .timeout import TimeoutManager


logger = logging.getLogger(__name__)


class GameStateException(Exception):
    pass


class GameStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETE = auto()


class GameState:
    REGULATION_MINUTES_PER_QUARTER = 15
    OVERTIME_MINUTES_PER_QUARTER = 10

    def __init__(self, home_team: Team, away_team: Team) -> None:
        self.game_status = GameStatus.NOT_STARTED
        self.ball_position = 999  # yard line
        self.down = 999
        self.distance = 999
        self.possession = home_team
        self.home_team = home_team
        self.away_team = away_team
        self.timeout_mgr = TimeoutManager(self.home_team, self.away_team)
        self.scoreboard_mgr = ScoreboardManager(self.home_team, self.away_team)
        self.clock = GameClock(minutes_per_quarter=self.REGULATION_MINUTES_PER_QUARTER)
        self.overtime = False
        logger.debug(
            f"Initialized GameState with teams {self.home_team} vs {self.away_team}"
        )

    def start_game(self) -> None:
        if self.game_status != GameStatus.NOT_STARTED:
            logger.error("Attempted to start game but it is already in progress or complete")
            raise GameStateException("Attempted to start game but it is already in progress or complete")
        self.game_status = GameStatus.IN_PROGRESS
        self.ball_position = 35  # kickoff yard line
        self.down = 1
        self.distance = 10
        logger.info(f"Game started: {self.home_team} vs {self.away_team}")

    def end_game(self) -> None:
        if self.game_status == GameStatus.COMPLETE:
            logger.error("Attempted to end game but it is already complete")
            raise GameStateException("Attempted to end game but it is already complete")
        self.game_status = GameStatus.COMPLETE
        logger.info("Game marked as complete")

    def is_tied(self) -> bool:
        tied = self.scoreboard_mgr.is_tied()
        logger.debug(f"Game tied? {tied}")
        return tied

    def is_over(self) -> bool:
        """Check if the game should be marked complete (end of regulation or OT)."""
        if self.game_status != GameStatus.IN_PROGRESS:
            return self.game_status == GameStatus.COMPLETE

        if self.clock.time_remaining() == 0:
            if self.clock.quarter >= 4:
                if self.is_tied():
                    # Go to overtime
                    self.overtime = True
                    self.clock = GameClock(minutes_per_quarter=self.OVERTIME_MINUTES_PER_QUARTER)
                    logger.info("Regulation ended in tie, starting overtime")
                    return False
                else:
                    self.end_game()
                    return True
        return False

    def get_score(self):
        score = self.scoreboard_mgr.get_score()
        logger.debug(f"Current score: {score}")
        return score

    def use_timeout(self, team: Team) -> None:
        self.timeout_mgr.use_timeout(team)

    def reset_timeouts(self) -> None:
        self.timeout_mgr.reset_timeouts()

    def get_timeouts(self):
        return self.timeout_mgr.get_all_timeouts()

    def set_possession(self, team: Team) -> None:
        if team not in (self.home_team, self.away_team):
            raise ValueError(f"Invalid possession: {team}")
        self.possession = team
        logger.debug(f"Possession set to {team}")

    def advance_down(self, yards_gained: int) -> None:
        """Update down, distance, and ball position after a play."""
        if self.possession is None:
            raise ValueError("No team has possession!")

        old_position = self.ball_position
        self.ball_position -= yards_gained  # moving towards 0 to score

        # Touchdown check
        if self.ball_position <= 0:
            self.ball_position = 0
            logger.info(f"TOUCHDOWN {self.possession}! Ball reached the end zone")
            self.scoreboard_mgr.touchdown(self.possession)

            # handle points after
            self.down = None
            self.distance = None
            self.ball_position = None
            return

        # Normal down/distance handling
        self.distance = max(0, self.distance - yards_gained)
        if self.distance <= 0:  # First down achieved
            self.down = 1
            self.distance = 10
            logger.info(f"First down for {self.possession} at {self.ball_position} yard line")
        else:
            self.down += 1
            if self.down > 4:  # Turnover on downs
                logger.info(f"Turnover on downs at {self.ball_position} yard line")
                self.down = 1
                self.distance = 10
                self.possession = (
                    self.away_team if self.possession == self.home_team else self.home_team
                )

        logger.debug(
            f"Ball moved from {old_position} to {self.ball_position}, "
            f"down={self.down}, distance={self.distance}"
        )


    def __str__(self) -> str:
        return (
            f"GameState(status={self.game_status.name}, "
            f"quarter={self.clock.quarter}, "
            f"time={self.clock.minutes()}:{self.clock.seconds():02}, "
            f"score={self.get_score()}, "
            f"possession={self.possession}, "
            f"down={self.down}, distance={self.distance}, "
            f"ball_pos={self.ball_position})"
        )

    def __repr__(self) -> str:
        return self.__str__()
