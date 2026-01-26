from __future__ import annotations
from enum import Enum
import logging
from typing import Dict, List, Optional
import uuid


logger = logging.getLogger(__name__)


class AthletePositionEnum(Enum):
    """
    Enumeration of all football positions used in the simulation.

    The enum includes both specific positions (e.g., QB, LT, CB)
    and generic grouping positions (e.g., SKILL, OLINE, DB).
    These grouping positions are used by formation validators,
    personnel selection models, and fallback logic when a more
    specific position is not available.
    """

    # Offense
    OFFENSE = "OFFENSE"  # generic offense position
    QB = "QB"
    SKILL = "SKILL"  # generic skill position
    RB = "RB"
    WR = "WR"
    TE = "TE"
    OLINE = "OLINE"  # generic offensive line position
    T = "T"  # generic tackle position
    G = "G"  # generic guard position
    LT = "LT"
    LG = "LG"
    C = "C"
    RG = "RG"
    RT = "RT"
    # Defense
    DEFENSE = "DEFENSE"  # generic defense position
    DLINE = "DLINE"  # generic defensive line position
    DT = "DT"
    EDGE = "EDGE"  # generic edge rusher position
    RE = "RE"
    LE = "LE"
    LB = "LB"  # generic linebacker position
    MLB = "MLB"
    OLB = "OLB"  # generic outside linebacker position
    LOLB = "LOLB"
    ROLB = "ROLB"
    DB = "DB"  # generic defensive back position
    CB = "CB"
    S = "S"  # generic safety position
    FS = "FS"
    SS = "SS"
    # Special Teams
    SPECIAL_TEAMS = "SPECIAL_TEAMS"  # generic special teams position
    RETURNER = "RETURNER"  # generic returner position
    KR = "KR"
    P = "P"
    K = "K"
    LS = "LS"
    # Fallback
    UNKNOWN = "UNKNOWN"


class PositionTree:
    """
    A tree structure representing athlete positions and their hierarchy. This
    allows for easy traversal and querying of position relationships. Each node
    in the tree represents a position and can have multiple child positions. This
    allows for grouping of positions (e.g., SKILL, OLINE) and defining parent-child
    relationships between positions. This also allows us to have fallback logic when
    a specific position is not available by traversing up the tree to more generic
    positions. For example, if a WR is not available, we can fallback to SKILL, then
    OFFENSE.
    """

    def __init__(
        self,
        position: Optional[AthletePositionEnum],
        children: Optional[Dict[AthletePositionEnum, "PositionTree"]] = None,
        parent: Optional["PositionTree"] = None,
    ):
        self.position = position
        self.children = children or {}
        self.parent = parent

        for child in self.children.values():
            child.parent = self

    # ==============================
    # Tree Operations
    # ==============================
    def is_leaf(self) -> bool:
        """Check if the current node is a leaf node (has no children)."""
        return len(self.children) == 0

    def find_node(self, pos: AthletePositionEnum) -> Optional["PositionTree"]:
        """Find and return the node corresponding to the given position."""
        if self.position == pos:
            return self
        for child in self.children.values():
            result = child.find_node(pos)
            if result is not None:
                return result
        return None

    def all_positions(self) -> List[AthletePositionEnum]:
        """Get a list of all positions in the subtree rooted at this node."""
        if self.position is not None and self.is_leaf():
            return [self.position]

        positions: List[AthletePositionEnum] = []
        for child in self.children.values():
            positions.extend(child.all_positions())
        return positions

    def contains(self, pos: AthletePositionEnum) -> bool:
        """Check if the subtree contains the specified position."""
        if self.position == pos:
            return True
        return any(child.contains(pos) for child in self.children.values())

    def is_child_of(self, parent: AthletePositionEnum) -> bool:
        """Check if the current node is a child of the specified parent position."""
        pos = self.parent
        while pos is not None:
            if pos.position == parent:
                return True
            pos = pos.parent
        return False


class Athlete:
    """
    Domain model representing an athlete in the simulation. This class
    encapsulates the athlete's personal information and position. An
    athlete is uniquely identified by a UUID and assigned a specific position
    from the AthletePositionEnum. Atheltes will be on a team roster and
    can participate in a play during a game as a PlayParticipant.
    """

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

    # ==============================
    # Getters
    # ==============================
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

    # ==============================
    # String Representations
    # ==============================
    def __str__(self) -> str:
        return f"Athlete({self.full_name}, {self.position.name}, uid={self.uid})"

    def __repr__(self) -> str:
        return self.__str__()


POSITION_TREE = PositionTree(
    None,
    children={
        AthletePositionEnum.OFFENSE: PositionTree(
            AthletePositionEnum.OFFENSE,
            children={
                AthletePositionEnum.QB: PositionTree(AthletePositionEnum.QB),
                AthletePositionEnum.SKILL: PositionTree(
                    AthletePositionEnum.SKILL,
                    children={
                        AthletePositionEnum.RB: PositionTree(AthletePositionEnum.RB),
                        AthletePositionEnum.WR: PositionTree(AthletePositionEnum.WR),
                        AthletePositionEnum.TE: PositionTree(AthletePositionEnum.TE),
                    },
                ),
                AthletePositionEnum.OLINE: PositionTree(
                    AthletePositionEnum.OLINE,
                    children={
                        AthletePositionEnum.T: PositionTree(
                            AthletePositionEnum.T,
                            children={
                                AthletePositionEnum.LT: PositionTree(
                                    AthletePositionEnum.LT
                                ),
                                AthletePositionEnum.RT: PositionTree(
                                    AthletePositionEnum.RT
                                ),
                            },
                        ),
                        AthletePositionEnum.G: PositionTree(
                            AthletePositionEnum.G,
                            children={
                                AthletePositionEnum.LG: PositionTree(
                                    AthletePositionEnum.LG
                                ),
                                AthletePositionEnum.RG: PositionTree(
                                    AthletePositionEnum.RG
                                ),
                            },
                        ),
                        AthletePositionEnum.C: PositionTree(AthletePositionEnum.C),
                    },
                ),
            },
        ),
        AthletePositionEnum.DEFENSE: PositionTree(
            AthletePositionEnum.DEFENSE,
            children={
                AthletePositionEnum.DLINE: PositionTree(
                    AthletePositionEnum.DLINE,
                    children={
                        AthletePositionEnum.EDGE: PositionTree(
                            AthletePositionEnum.EDGE,
                            children={
                                AthletePositionEnum.RE: PositionTree(
                                    AthletePositionEnum.RE
                                ),
                                AthletePositionEnum.LE: PositionTree(
                                    AthletePositionEnum.LE
                                ),
                            },
                        ),
                        AthletePositionEnum.DT: PositionTree(AthletePositionEnum.DT),
                    },
                ),
                AthletePositionEnum.LB: PositionTree(
                    AthletePositionEnum.LB,
                    children={
                        AthletePositionEnum.MLB: PositionTree(AthletePositionEnum.MLB),
                        AthletePositionEnum.OLB: PositionTree(
                            AthletePositionEnum.OLB,
                            children={
                                AthletePositionEnum.LOLB: PositionTree(
                                    AthletePositionEnum.LOLB
                                ),
                                AthletePositionEnum.ROLB: PositionTree(
                                    AthletePositionEnum.ROLB
                                ),
                            },
                        ),
                    },
                ),
                AthletePositionEnum.DB: PositionTree(
                    AthletePositionEnum.DB,
                    children={
                        AthletePositionEnum.CB: PositionTree(AthletePositionEnum.CB),
                        AthletePositionEnum.S: PositionTree(
                            AthletePositionEnum.S,
                            children={
                                AthletePositionEnum.FS: PositionTree(
                                    AthletePositionEnum.FS
                                ),
                                AthletePositionEnum.SS: PositionTree(
                                    AthletePositionEnum.SS
                                ),
                            },
                        ),
                    },
                ),
            },
        ),
        AthletePositionEnum.SPECIAL_TEAMS: PositionTree(
            AthletePositionEnum.SPECIAL_TEAMS,
            children={
                AthletePositionEnum.RETURNER: PositionTree(
                    AthletePositionEnum.RETURNER,
                    children={
                        AthletePositionEnum.KR: PositionTree(AthletePositionEnum.KR),
                    },
                ),
                AthletePositionEnum.K: PositionTree(AthletePositionEnum.K),
                AthletePositionEnum.P: PositionTree(AthletePositionEnum.P),
                AthletePositionEnum.LS: PositionTree(AthletePositionEnum.LS),
            },
        ),
    },
)
