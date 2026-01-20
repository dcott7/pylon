from enum import auto, Enum
import logging
from typing import Dict, List, Optional, Set
import uuid

from .athlete import AthletePositionEnum, POSITION_TREE


logger = logging.getLogger(__name__)


class FormationInitializationError(Exception):
    """Raised when there is an error initializing a Formation."""

    pass


class PlayCallInitializationError(Exception):
    """Raised when there is an error initializing a PlayCall."""

    pass


class PlaySideEnum(Enum):
    OFFENSE = auto()
    DEFENSE = auto()


class PlayTypeEnum(Enum):
    # Offense
    RUN = auto()
    PASS = auto()
    RPO = auto()
    QB_KNEEL = auto()
    QB_SPIKE = auto()
    # Special Teams
    PUNT = auto()
    FIELD_GOAL = auto()
    KICKOFF = auto()
    EXTRA_POINT = auto()
    TWO_POINT_CONVERSION = auto()
    # Defense # TODO: Implement defensive play types
    DEFENSIVE_PLAY = auto()

    def is_kick(self) -> bool:
        return self in {
            PlayTypeEnum.PUNT,
            PlayTypeEnum.FIELD_GOAL,
            PlayTypeEnum.KICKOFF,
            PlayTypeEnum.EXTRA_POINT,
            PlayTypeEnum.TWO_POINT_CONVERSION,
        }


class Formation:
    """
    Formations describe how the players are aligned on the field. These can be
    used with any personnel package. For example, a "Shotgun Trips Right" formation
    can be used with a "11 Personnel" package (1 RB, 1 TE, 3 WR) or a "10 Personnel"
    package (1 RB, 0 TE, 4 WR).
    """

    def __init__(
        self,
        name: str,
        position_counts: Dict[
            AthletePositionEnum, int
        ],  # e.g. {AthletePositionEnum.QB: 1, AthletePositionEnum.WR: 3}
        tags: List[str],
        parent: Optional["Formation"] = None,
        subformations: Optional[Set["Formation"]] = None,
        uid: Optional[str] = None,
    ) -> None:
        self._uid = uid if uid else str(uuid.uuid4())
        self.name = name
        self._position_counts = position_counts
        self._tags = tags or []
        self.parent = parent
        self._subformations = subformations or set()
        if self.parent and self not in self.parent.subformations:
            self.parent.subformations.add(self)
        self._validate()

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def position_counts(self) -> Dict[AthletePositionEnum, int]:
        return self._position_counts

    @property
    def tags(self) -> List[str]:
        return self._tags

    @property
    def subformations(self) -> Set["Formation"]:
        return self._subformations

    def positions(self) -> List[AthletePositionEnum]:
        return list(self.position_counts.keys())

    def has_position(self, position: AthletePositionEnum) -> bool:
        return position in self.position_counts

    def get_position_count(self, position: AthletePositionEnum) -> int:
        return self.position_counts.get(position, 0)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def add_tag(self, tag: str) -> None:
        if tag in self._tags:
            logger.debug(f"Tag '{tag}' already present in formation {self.name}")
            return
        self._tags.append(tag)
        logger.debug(f"Added tag '{tag}' to formation {self.name}")

    def remove_tag(self, tag: str) -> None:
        if tag not in self._tags:
            logger.warning(f"Tag '{tag}' not found in formation {self.name}")
            return
        self._tags.remove(tag)
        logger.debug(f"Removed tag '{tag}' from formation {self.name}")

    def is_subformation_of(self, parent: "Formation") -> bool:
        """Check if this formation is a subformation of another."""
        current = self.parent
        while current is not None:
            if current.uid == parent.uid:
                return True
            current = current.parent
        return False

    def _validate(self) -> None:
        total_slots = sum(self.position_counts.values())
        # If there is a parent formation, this formation must define exactly 11 slots
        # Parent formations are allowed to have fewer than 11 slots (they can function as abstract formations)
        if self.parent is not None and total_slots != 11:
            msg = f"Formation '{self.name}' has a parent and defines {total_slots} slots (must be 11)"
            logger.error(msg)
            raise FormationInitializationError(msg)

    def __str__(self) -> str:
        return f"Formation(uid={self.uid}, name={self.name}, positions={len(self.position_counts)})"

    def __repr__(self) -> str:
        return self.__str__()


class PersonnelPackage:
    """
    Personnel packages refer to the types of skill players (running backs, tight
    ends, wide receivers) on the field. This is not about formation or alignment—just
    what types of players are on the field. For example, "11 Personnel" means 1 RB, 1 TE,
    and 3 WRs.
    """

    def __init__(
        self,
        name: str,
        counts: Dict[AthletePositionEnum, int],
        uid: Optional[str] = None,
    ) -> None:
        self._uid = uid if uid else str(uuid.uuid4())
        self.name = name
        self.counts = counts  # e.g., {RB: 1, TE: 2, WR: 2}

    @property
    def uid(self) -> str:
        return self._uid

    def __str__(self) -> str:
        return (
            f"PersonnelPackage(uid={self.uid}, name={self.name}, counts={self.counts})"
        )

    def __repr__(self) -> str:
        return self.__str__()


class PlayCall:
    """
    A PlayCall is a template for a play that can be executed during a game.
    """

    def __init__(
        self,
        name: str,
        play_type: PlayTypeEnum,
        formation: Formation,
        personnel_package: PersonnelPackage,
        side: PlaySideEnum,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        uid: Optional[str] = None,
    ) -> None:
        self._uid = uid if uid else str(uuid.uuid4())
        self.name = name
        self.play_type = play_type
        self.formation = formation
        self.personnel_package = personnel_package
        self.side = side
        self.description = description
        self._tags = tags if tags else []
        self._validate()

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def tags(self) -> List[str]:
        return self._tags

    def add_tag(self, tag: str) -> None:
        if tag not in self._tags:
            self._tags.append(tag)

    def _validate(self) -> None:
        if self.formation.parent is None:
            msg = (
                f"PlayCall '{self.name}' must use a subformation "
                f"(formation '{self.formation.name}' has no parent)"
            )
            logger.error(msg)
            raise PlayCallInitializationError(msg)

        # Select the correct subtree based on play side
        if self.side == PlaySideEnum.OFFENSE:
            valid_tree = POSITION_TREE.children[AthletePositionEnum.OFFENSE]
            side_label = "offensive"
        else:
            valid_tree = POSITION_TREE.children[AthletePositionEnum.DEFENSE]
            side_label = "defensive"

        # Validate each position in the formation
        for position in self.formation.positions():
            if not valid_tree.contains(position):
                msg = (
                    f"PlayCall '{self.name}' is {side_label} but formation "
                    f"'{self.formation.name}' includes invalid position '{position.name}'"
                )
                logger.error(msg)
                raise PlayCallInitializationError(msg)

    def __str__(self) -> str:
        return f"PlayCall(uid={self.uid}, name={self.name}, type={self.play_type.name})"

    def __repr__(self) -> str:
        return self.__str__()


class Playbook:
    """
    A Playbook contains a collection of PlayCalls that a team can use during a game.
    """

    def __init__(
        self,
        plays: Optional[List[PlayCall]] = None,
        uid: Optional[str] = None,
    ) -> None:
        self._uid = uid if uid else str(uuid.uuid4())
        self._plays = plays or []

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def plays(self) -> List[PlayCall]:
        return self._plays.copy()

    def add_play(self, play: PlayCall) -> None:
        self._plays.append(play)

    def get_by_tag(self, tag: str) -> List[PlayCall]:
        return [play for play in self._plays if tag in play.tags]

    def get_by_type(self, play_type: PlayTypeEnum) -> List[PlayCall]:
        return [play for play in self._plays if play.play_type == play_type]

    def __len__(self) -> int:
        return len(self._plays)

    def __str__(self) -> str:
        return f"Playbook(uid={self.uid}, plays={self.__len__()})"

    def __repr__(self) -> str:
        return self.__str__()
