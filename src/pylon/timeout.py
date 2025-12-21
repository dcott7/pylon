import logging
from typing import Dict

from .entities.team import Team


logger = logging.getLogger(__name__)


class TimeoutManager:
    MAX_TIMEOUTS = 3  # TODO: Make this configurable per league rules

    def __init__(self, home_team: Team, away_team: Team) -> None:
        self.timeouts: Dict[str, int] = {
            home_team.uid: self.MAX_TIMEOUTS,
            away_team.uid: self.MAX_TIMEOUTS,
        }
        logger.debug(
            f"Initialized TimeoutManager with teams {home_team} vs {away_team}, "
            f"{self.MAX_TIMEOUTS} each"
        )

    def use_timeout(self, team: Team) -> None:
        """Consume a timeout for a team if available."""
        if self.timeouts[team.uid] > 0:
            self.timeouts[team.uid] -= 1
            logger.info(
                f"{team} used a timeout. Remaining: {self.timeouts[team.uid]}"
            )
        else:
            logger.warning(
                f"{team} attempted to use a timeout but has none left"
            )

    def add_timeout(self, team: Team) -> None:
        """Add back a timeout (cannot exceed MAX_TIMEOUTS)."""
        if self.timeouts[team.uid] < self.MAX_TIMEOUTS:
            self.timeouts[team.uid] += 1
            logger.info(
                f"{team} gained a timeout. Now has {self.timeouts[team.uid]}"
            )
        else:
            logger.debug(
                f"{team} already has the maximum ({self.MAX_TIMEOUTS}) timeouts"
            )

    def reset_timeouts(self) -> None:
        """Reset all teams to the maximum allowed timeouts."""
        for team in self.timeouts:
            self.timeouts[team] = self.MAX_TIMEOUTS
        logger.info("Timeouts reset for all teams")

    def num_timeouts(self, team: Team) -> int:
        """Return the number of timeouts left for a team."""
        count = self.timeouts[team.uid]
        logger.debug(f"{team} has {count} timeouts remaining")
        return count

    def has_timeout(self, team: Team) -> bool:
        """Return True if the team has at least one timeout left."""
        has_one = self.num_timeouts(team) > 0
        logger.debug(f"{team} has timeout available? {has_one}")
        return has_one

    def get_all_timeouts(self) -> Dict[str, int]:
        """Return a copy of all teams’ timeouts."""
        snapshot = self.timeouts.copy()
        logger.debug(f"All timeouts: {snapshot}")
        return snapshot

    def __str__(self) -> str:
        return " | ".join(
            f"{team}: {count}" for team, count in self.timeouts.items()
        )

    def __repr__(self) -> str:
        return f"TimeoutManager({self.timeouts})"
