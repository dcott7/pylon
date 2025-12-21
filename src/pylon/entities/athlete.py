import logging
import uuid
from enum import auto, Enum
from typing import Optional


logger = logging.getLogger(__name__)


class AthletePositionEnum(Enum):

    # Offense
    QB = auto()
    RB = auto()
    WR = auto()
    TE = auto()
    G = auto()
    T = auto()
    C = auto()
    # Defense
    DT = auto()
    DE = auto()
    MLB = auto()
    OLB = auto()
    CB = auto()
    FS = auto()
    SS = auto()
    # Special Teams
    KR = auto()
    P = auto()
    K = auto()
    LS = auto()


class Athlete:
    def __init__(
        self,
        first_name: str,
        last_name: str,
        position: AthletePositionEnum,
        uid: Optional[str] = None,
    ) -> None:
        self._uid = uid or str(uuid.uuid4())
        self._first_name = first_name
        self._last_name = last_name
        self._position = position

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def position(self) -> AthletePositionEnum:
        return self._position

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return (
            f"Athlete({self.full_name}, {self.position.name}, uid={self.uid})"
        )

    def __repr__(self) -> str:
        return self.__str__()
