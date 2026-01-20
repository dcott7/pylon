import logging
import uuid
from typing import List, Optional

from .athlete import Athlete
from .playbook import Playbook, PlayCall, PlaySideEnum


logger = logging.getLogger(__name__)


class Team:
    def __init__(
        self,
        name: str,
        off_playbook: Optional[Playbook] = None,
        def_playbook: Optional[Playbook] = None,
        roster: Optional[List[Athlete]] = None,
        uid: Optional[str] = None,
    ) -> None:
        self.uid = uid or str(uuid.uuid4())
        self.name = name
        self._off_playbook = off_playbook or Playbook()
        self._def_playbook = def_playbook or Playbook()
        self._roster: List[Athlete] = roster or []

    @property
    def roster(self) -> List[Athlete]:
        return self._roster

    @property
    def off_playbook(self) -> Playbook:
        return self._off_playbook

    @property
    def def_playbook(self) -> Playbook:
        return self._def_playbook

    def add_player(self, athlete: Athlete) -> None:
        logger.debug(f"Adding {athlete} to {self.name} roster")
        self._roster.append(athlete)

    def add_play_template(self, play: PlayCall) -> None:
        logger.debug(f"Adding {play} to {self.name} playbook")
        if play.side == PlaySideEnum.OFFENSE:
            self._off_playbook.add_play(play)
        elif play.side == PlaySideEnum.DEFENSE:
            self._def_playbook.add_play(play)
        else:
            logger.error(
                f"Play {play} has invalid side {play.side}, cannot add to playbook"
            )

    def __repr__(self) -> str:
        return f"Team({self.name}, Roster Size: {len(self._roster)})"

    def __str__(self) -> str:
        n_offensive = len(self.off_playbook)
        n_defensive = len(self.def_playbook)
        return (
            f"{self.name} (Roster: {len(self._roster)} players, "
            f"{n_offensive} offensive plays, {n_defensive} defensive plays)"
        )
