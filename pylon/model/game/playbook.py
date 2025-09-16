from enum import auto, Enum
import logging
from typing import Dict, List, Optional

from .team import Athlete, AthletePositionEnum


logger = logging.getLogger(__name__)


class Formation:
    """
    Formations describe how the players are aligned on the field. These can be
    used with any personnel package.
    """
    def __init__(
        self,
        name: str,
        position_counts: Dict[AthletePositionEnum, int],
        alignment: str,
        tags: List[str],
        parent: Optional["Formation"] = None
    ) -> None:
        self.name = name
        self.position_counts = position_counts  # e.g. {AthletePositionEnum.QB: 1, AthletePositionEnum.WR: 3}
        self.alignment = alignment # e.g. "I-Formation", "Trips", etc.
        self.tags = tags # e.g. ["pass-heavy", "spread", "goal-line"]
        self.parent = parent # e.g. Formation("Singleback", ...)
        self.subformations: List["Formation"] = []
       
        if parent:
           parent.subformations.append(self)

    def __str__(self) -> str:
        return f"Formation(name={self.name}, positions={self.position_counts})"


class Lineup:
    def __init__(self, formation: Formation) -> None:
        self.formation = formation
        self.assignments: Dict[AthletePositionEnum, List[Athlete]] = {
            pos: [] for pos in formation.position_counts
        }
       
    def assign_player(self, position: AthletePositionEnum, athlete: Athlete) -> bool:
        if position not in self.assignments:
            return False
        if len(self.assignments[position]) >= self.formation.position_counts[position]:
            return False
        self.assignments[position].append(athlete)
        return True

    def is_complete(self) -> bool:
        return all(
            len(players) == count
            for position, count in self.formation.position_counts.items()
            for players in [self.assignments[position]]
        )

    def __str__(self) -> str:
        return f"Lineup(formation={self.formation.name}, assignments={self.assignments})"
   
    def __repr__(self) -> str:
        return self.__str__()


class PersonnelPackage:
    """
    Personnel packages refer to the types of skill players (running backs, tight
    ends, wide receivers) on the field. This is not about formation or alignment—just
    who is on the field.
    """
    def __init__(self, name: str, counts: Dict[AthletePositionEnum, int]) -> None:
        self.name = name
        self.counts = counts  # e.g., {RB: 1, TE: 2, WR: 2}
       
    def __str__(self) -> str:
        return f"PersonnelPackage(name={self.name}, counts={self.counts})"
   
    def __repr__(self) -> str:
        return self.__str__()


class PlaySideEnum(Enum):
    OFFENSE = auto()
    DEFENSE = auto()
    SPECIAL = auto()


class PlayTypeEnum(Enum):
    # Offense
    RUN = auto()
    PASS = auto()
    PLAY_ACTION = auto()
    SCREEN = auto()
    QB_KNEEL = auto()
    QB_SPIKE = auto()
    # Special Teams
    PUNT = auto()
    FIELD_GOAL = auto()
    KICKOFF = auto()
    # Defense
    # COVERAGE = auto()
    # BLITZ = auto()
    # MAN = auto()
    # ZONE = auto()
   
   
class PlayTemplate:
    def __init__(
        self,
        name: str,
        play_type: PlayTypeEnum,
        formation: Formation,
        personnel: str,
        side: PlaySideEnum,
        tags: List[str] = [],
        description: str = "",
    ) -> None:
        self.name = name
        self.play_type = play_type
        self.formation = formation
        self.personnel = personnel
        self.side = side
        self.tags = tags  # e.g. ["short-yardage", "aggressive", "safe"]
        self.description = description

    def __str__(self) -> str:
        return f"PlayTemplate(name={self.name}, type={self.play_type.name}, formation={self.formation}, personnel={self.personnel}, side ={self.side})"
   

class Playbook:
    def __init__(self, templates: Optional[List[PlayTemplate]] = None) -> None:
        self.templates = templates if templates else []

    def add_template(self, template: PlayTemplate) -> None:
        self.templates.append(template)

    def get_by_tag(self, tag: str) -> List[PlayTemplate]:
        return [tpl for tpl in self.templates if tag in tpl.tags]

    def get_by_type(self, play_type: PlayTypeEnum) -> List[PlayTemplate]:
        return [tpl for tpl in self.templates if tpl.play_type == play_type]    