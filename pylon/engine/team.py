import logging
import uuid
from typing import List, Optional

from .athlete import Athlete


logger = logging.getLogger(__name__)


class Team:
    def __init__(
        self, 
        uid: Optional[str] = None, 
        name: str = "", 
        roster: List[Athlete] = []
    ) -> None:
        self.uid = uid if uid else str(uuid.uuid4())
        self.name = name
        self.roster = roster if roster else []
        
    def add_player(self, athlete: Athlete) -> None:
        logger.info(f"Adding {athlete} to {self.name} roster")
        self.roster.append(athlete)
        
    def __str__(self) -> None:
        return f"Team(uid={self.uid}, name={self.name}, roster={self.roster})"

    def __repr__(self) -> str:
        return self.__str__()