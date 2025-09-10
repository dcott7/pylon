from enum import auto, Enum
import logging
from typing import List

from .athlete import Athlete, AthletePositionEnum
from .event import Event
from .situation import Situation


logger = logging.getLogger(__name__)


class PlayTypeEnum(Enum):
    RUN = auto()
    PASS = auto()
    PUNT = auto()
    FIELD_GOAL = auto()
    KICKOFF = auto()
    QB_SPIKE = auto()
    QB_KNEEL = auto()
    

class PlayTypeModifierEnum(Enum):
    NONE = auto()
    EXTRA_POINT = auto()
    TWO_POINT_CONVERSION = auto()


class LineupSlot:
    def __init__(self, position: AthletePositionEnum, athlete: Athlete) -> None:
        self.position = position
        self.athlete = athlete
       
    def __str__(self) -> str:
        return f"LineupSlot(position={self.position}, athlete={self.athlete})"
   
    def __repr__(self) -> str:
        return self.__str__()


class PlayResult:
    def __init__(self, yards_gained: int, is_touchdown: bool, is_turnover: bool) -> None:
        self.yards_gained = yards_gained
        self.is_touchdown = is_touchdown
        self.is_turnover = is_turnover
       
    def __str__(self) -> str:
        return f"PlayResult(yards_gained={self.yards_gained}, is_touchdown={self.is_touchdown}, is_turnover={self.is_turnover})"

    def __repr__(self) -> str:
        return self.__str__()

    
class Play:
    def __init__(self, play_type: PlayTypeEnum, modifier: PlayTypeModifierEnum) -> None:
        self.play_type = play_type
        self.modifier = modifier
        self.off_lineup: List[LineupSlot] = []
        self.def_lineup: List[LineupSlot] = []
        self.start_situation: Situation = None
        self.end_situation: Situation = None
        self.events = []
        self.result = None

    def add_event(self, event: Event) -> None:
        self.events.append(event)

    def set_result(self, result: PlayResult) -> None:
        self.result = result

    def __str__(self) -> str:
        return (
            f"Play(play_type={self.play_type}, modifier={self.modifier}, "
            f"start_situation={self.start_situation}, end_situation={self.end_situation}, "
            f"events={self.events}, result={self.result if self.result else 'N/A'})"
        )
        
    def __repr__(self):
        return self.__str__()