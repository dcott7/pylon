"""Scoreboard state container for tracking points by team during a game."""

import logging
from typing import Dict, Optional

from ..domain.team import Team


logger = logging.getLogger(__name__)


class ScoreboardStateError(Exception):
    pass


class Scoreboard:
    """
    Tracks the score of a football game.

    This is a passive state container. Scores are updated by external
    play/outcome events.

    Attributes:
        _scores (Dict[str, int]): Mapping from team UID to current score.
    """

    def __init__(self, home_team: Team, away_team: Team) -> None:
        self._home_team = home_team
        self._away_team = away_team
        self._scores: Dict[str, int] = {home_team.uid: 0, away_team.uid: 0}

    def _validate_team(self, team: Team) -> None:
        if team.uid not in self._scores:
            raise ScoreboardStateError(f"Team {team.name} is not part of this game")

    def add_points(self, team: Team, points: int) -> None:
        """Add points to a team's score, optionally with a description for logging."""
        self._validate_team(team)
        old_score = self._scores[team.uid]
        self._scores[team.uid] += points
        logger.info(
            f"{team.name} score updated: {old_score} -> {self._scores[team.uid]}"
        )

    # Query methods
    def current_score(self, team: Team) -> int:
        self._validate_team(team)
        return self._scores[team.uid]

    def score(self) -> Dict[str, int]:
        """Return a snapshot of current scores."""
        return self._scores.copy()

    def is_tied(self) -> bool:
        scores = list(self._scores.values())
        return scores[0] == scores[1]

    def leader(self) -> Optional[Team]:
        """Return the leading team, or None if tied."""
        home_score, away_score = list(self._scores.values())
        if home_score == away_score:
            return None

        return self._home_team if home_score > away_score else self._away_team

    def reset(self) -> None:
        """Reset both teams' scores to zero."""
        for team in self._scores:
            self._scores[team] = 0
        logger.info("Scoreboard reset to 0–0")
