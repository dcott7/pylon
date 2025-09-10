import logging
from typing import Dict

from .team import Team


logger = logging.getLogger(__name__)


class ScoreboardManager:
    def __init__(self, home_team: Team, away_team: Team) -> None:
        self.scores: Dict[Team, int] = {home_team: 0, away_team: 0}
        logger.debug(f"Initialized ScoreboardManager with teams {home_team} vs {away_team}")

    # --- Scoring methods ---
    def touchdown(self, team: Team) -> None:
        logger.debug(f"{team} scored a touchdown (6 points)")
        self.update_score(team, 6)

    def field_goal(self, team: Team) -> None:
        logger.debug(f"{team} scored a field goal (3 points)")
        self.update_score(team, 3)

    def extra_point(self, team: Team) -> None:
        logger.debug(f"{team} scored an extra point (1 point)")
        self.update_score(team, 1)

    def two_point_conversion(self, team: Team) -> None:
        logger.debug(f"{team} completed a two-point conversion (2 points)")
        self.update_score(team, 2)

    def safety(self, team: Team) -> None:
        logger.debug(f"{team} scored a safety (2 points)")
        self.update_score(team, 2)

    # --- Score handling ---
    def update_score(self, team: Team, points: int) -> None:
        if team not in self.scores:
            logger.error(f"Attempted to update score for unknown team: {team}")
            raise ValueError(f"Team {team} is not part of this game")

        old_score = self.scores[team]
        self.scores[team] += points
        logger.info(f"{team} score updated: {old_score} -> {self.scores[team]} (+{points})")

    def get_score(self) -> Dict[Team, int]:
        logger.debug(f"Current scores: {self.scores}")
        return self.scores.copy()

    def is_tied(self) -> bool:
        scores = list(self.scores.values())
        tied = scores[0] == scores[1]
        logger.debug(f"Game tied? {tied} ({scores[0]} - {scores[1]})")
        return tied

    def get_leader(self) -> Team | None:
        """Return the leading team, or None if tied."""
        teams = list(self.scores.keys())
        values = list(self.scores.values())

        if values[0] == values[1]:
            logger.debug("No leader, game is tied")
            return None

        leader = teams[0] if values[0] > values[1] else teams[1]
        logger.debug(f"Leader is {leader}")
        return leader

    def reset(self) -> None:
        """Reset both teams’ scores to zero."""
        logger.info("Resetting ScoreboardManager to 0–0")
        for team in self.scores:
            self.scores[team] = 0

    def __str__(self) -> str:
        return f"ScoreboardManager: " + " vs ".join(f"{team} {score}" for team, score in self.scores.items())
