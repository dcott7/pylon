"""
Team domain model for Pylon simulations.

Defines the Team abstraction representing a football team with its core components:

- Unique identity (UID) and name
- Offensive and defensive playbooks (collections of play templates)
- Roster of athletes (players on the team)

Key capabilities:
- Add players to the team's roster
- Add plays to the appropriate playbook (offensive or defensive)
- Access roster and playbooks through properties

Teams serve as the primary unit of organization in the simulation:
- Each game involves two teams (home and away)
- Teams own playbooks that define available plays
- Teams maintain rosters of athletes who participate in plays
- PlayExecutionData captures which athletes participated and their roles

Design notes:
- Team UIDs are auto-generated or provided explicitly for persistence/replay
- Playbooks are lazily initialized if not provided at construction
- Roster is mutable (can add players during setup)
"""

import logging
import uuid
from typing import List, Optional

from .athlete import Athlete, AthletePositionEnum
from .playbook import Playbook, PlayCall, PlaySideEnum


logger = logging.getLogger(__name__)


class Team:
    """
    Represents a football team with offensive and defensive playbooks
    and a roster of athletes. Teams can add players to their roster and
    add play templates to their playbooks. The Team class provides
    properties to access the roster and playbooks, and methods to
    manage them.
    """

    def __init__(
        self,
        name: str,
        off_playbook: Optional[Playbook] = None,
        def_playbook: Optional[Playbook] = None,
        roster: Optional[List[Athlete]] = None,
        uid: Optional[str] = None,
    ) -> None:
        # Keep uid stable across reloads (use provided UID when available)
        self._uid = uid or str(uuid.uuid4())
        self.name = name
        self._off_playbook = off_playbook or Playbook()
        self._def_playbook = def_playbook or Playbook()
        self._roster: List[Athlete] = roster or []

    # ==============================
    # Setters
    # ==============================
    def add_athlete(self, athlete: Athlete) -> None:
        logger.debug(f"Adding {athlete} to {self.name} roster")
        self._roster.append(athlete)

    def add_play_template(self, play: PlayCall) -> None:
        logger.debug(f"Adding {play} to {self.name} playbook")
        if play.side == PlaySideEnum.OFFENSE:
            self._off_playbook.add_play(play)
            return
        elif play.side == PlaySideEnum.DEFENSE:
            self._def_playbook.add_play(play)
            return

        logger.error(
            f"Play {play} has invalid side {play.side}, cannot add to playbook"
        )

    # ==============================
    # Getters
    # ==============================
    @property
    def roster(self) -> List[Athlete]:
        return self._roster

    @property
    def off_playbook(self) -> Playbook:
        return self._off_playbook

    @property
    def def_playbook(self) -> Playbook:
        return self._def_playbook

    @property
    def uid(self) -> str:
        return self._uid

    def get_athlete_by_uid(self, athlete_uid: str) -> Optional[Athlete]:
        for athlete in self._roster:
            if athlete.uid == athlete_uid:
                return athlete
        logger.warning(f"Athlete with UID {athlete_uid} not found in team {self.name}")
        return None

    def get_athletes_by_position(self, position: AthletePositionEnum) -> List[Athlete]:
        athletes_at_position = [
            athlete for athlete in self._roster if athlete.position == position
        ]
        if not athletes_at_position:
            logger.warning(
                f"No athletes found at position {position} in team {self.name}"
            )
        return athletes_at_position
