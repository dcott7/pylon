from enum import auto, Enum
import logging


logger = logging.getLogger(__name__)


class AthletePositionEnum(Enum):
    QB = auto()
    RB = auto()
    WR = auto()
    TE = auto()
    G = auto()
    T = auto()
    C = auto()
    DT = auto()
    DE = auto()
    MLB = auto()
    OLLB = auto()
    CB = auto()
    FS = auto()
    SS = auto()
    

class Athlete:
    def __init__(self, name) -> None:
        self.name = name

    def __str__(self) -> str:
        return f"Athlete(name={self.name})"
   
    def __repr__(self) -> str:
        return self.__str__()