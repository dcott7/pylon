from enum import auto, Enum
import logging
from typing import Optional
import uuid


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
    OLB = auto()
    CB = auto()
    FS = auto()
    SS = auto()
    KR = auto()
    P = auto()
    K = auto()
    LS = auto()
    

class Athlete:
    def __init__(
        self,
        uid: Optional[str] = None,
        first_name: str = "",
        last_name: str = "",
        position: AthletePositionEnum = None
    ) -> None:
        self.uid = uid if uid else str(uuid.uuid4())
        self.first_name = first_name
        self.last_name = last_name
        self.position = position

    def __str__(self) -> str:
        return f"Athlete(uid={self.uid}, first_name={self.first_name}, last_name={self.last_name})"
   
    def __repr__(self) -> str:
        return self.__str__()