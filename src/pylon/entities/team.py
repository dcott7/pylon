import logging
import uuid
from typing import List, Optional

from .athlete import Athlete
from .playbook import Playbook, PlayCall


logger = logging.getLogger(__name__)


class Team:
    def __init__(
        self,
        name: str,
        playbook: Optional[Playbook] = None,
        roster: Optional[List[Athlete]] = None,
        uid: Optional[str] = None,
    ) -> None:
        self.uid = uid or str(uuid.uuid4())
        self.name = name
        self._playbook = playbook or Playbook()
        self._roster: List[Athlete] = roster or []

    @property
    def roster(self) -> List[Athlete]:
        return self._roster

    @property
    def playbook(self) -> Playbook:
        return self._playbook

    def add_player(self, athlete: Athlete) -> None:
        logger.debug(f"Adding {athlete} to {self.name} roster")
        self._roster.append(athlete)

    def add_play_template(self, play: PlayCall) -> None:
        logger.debug(f"Adding {play} to {self.name} playbook")
        self._playbook.add_play(play)

    def __repr__(self) -> str:
        return f"Team({self.name}, Roster Size: {len(self._roster)})"

    def __str__(self) -> str:
        return f"{self.name} (Roster: {len(self._roster)} players, {len(self.playbook)} plays)"
