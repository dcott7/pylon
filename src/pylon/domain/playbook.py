from enum import Enum
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
    OFFENSE = "OFFENSE"
    DEFENSE = "DEFENSE"


class PlayTypeEnum(Enum):
    """
    Play types represent the general category of a play call. They can be
    used to filter and organize plays within a playbook.
    """

    # Offense
    RUN = "RUN"
    PASS = "PASS"
    RPO = "RPO"
    QB_KNEEL = "QB_KNEEL"
    QB_SPIKE = "QB_SPIKE"
    # Special Teams
    PUNT = "PUNT"
    FIELD_GOAL = "FIELD_GOAL"
    KICKOFF = "KICKOFF"
    EXTRA_POINT = "EXTRA_POINT"
    TWO_POINT_CONVERSION = "TWO_POINT_CONVERSION"
    # Defense # TODO: Implement defensive play types
    DEFENSIVE_PLAY = "DEFENSIVE_PLAY"

    def is_kick(self) -> bool:
        return self in {
            PlayTypeEnum.PUNT,
            PlayTypeEnum.FIELD_GOAL,
            PlayTypeEnum.KICKOFF,
            PlayTypeEnum.EXTRA_POINT,
            PlayTypeEnum.TWO_POINT_CONVERSION,
        }

    def is_pass(self) -> bool:
        return self == PlayTypeEnum.PASS

    def is_run(self) -> bool:
        return self == PlayTypeEnum.RUN

    def is_rpo(self) -> bool:
        return self == PlayTypeEnum.RPO

    def is_special_teams(self) -> bool:
        return self.is_kick()  # same as is_kick for now


class Formation:
    """
    Formations describe how the players are aligned on the field. These can be
    used with any personnel package. For example, a "Shotgun Trips Right" formation
    can be used with a "11 Personnel" package (1 RB, 1 TE, 3 WR) or a "10 Personnel"
    package (1 RB, 0 TE, 4 WR). Formations can have subformations, which are more
    specific versions of a base formation. For example, "Shotgun Trips Right" could
    be a base formation, and "Shotgun Trips Right Bunch" could be a subformation.
    Parent formations are abstract templates (e.g., “Shotgun”, “Trips”, “Bunch”).
    Subformations are concrete alignments with exactly 11 positions.
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

    # ==============================
    # Setters
    # ==============================
    def add_tag(self, tag: str) -> None:
        if tag in self._tags:
            logger.debug(f"Tag '{tag}' already present in formation {self.name}")
            return
        self._tags.append(tag)
        logger.debug(f"Added tag '{tag}' to formation {self.name}")

    # ==============================
    # Getters
    # ==============================
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

    @property
    def positions(self) -> List[AthletePositionEnum]:
        return list(self.position_counts.keys())

    def position_count(self, position: AthletePositionEnum) -> int:
        return self.position_counts.get(position, 0)

    # ==============================
    # Utility Methods
    # ==============================
    def has_position(self, position: AthletePositionEnum) -> bool:
        return position in self.position_counts

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def is_subformation_of(self, parent: "Formation") -> bool:
        """Check if this formation is a subformation of another."""
        current = self.parent
        while current is not None:
            if current.uid == parent.uid:
                return True
            current = current.parent
        return False

    # ==============================
    # Validators
    # ==============================
    def _validate(self) -> None:
        self._valiate_positions()
        self._validate_position_counts()

    def _validate_position_counts(self) -> None:
        total_slots = sum(self.position_counts.values())
        # If there is a parent formation, this formation must define exactly 11 slots
        # Parent formations are allowed to have fewer than 11 slots (they can function
        # as abstract formations)
        if self.parent is not None and total_slots != 11:
            msg = (
                f"Formation '{self.name}' has a parent and defines "
                f"{total_slots} slots (must be 11)"
            )
            logger.error(msg)
            raise FormationInitializationError(msg)

    def _valiate_positions(self) -> None:
        for pos, _ in self.position_counts.items():
            if POSITION_TREE.find_node(pos) is None:
                logger.error(f"Unknown position {pos} in formation '{self.name}'")
                raise FormationInitializationError(f"Unknown position {pos}")


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
    A PlayCall is a template for a play that can be executed during a game. It
    includes information about the formation, personnel package, side (offense or
    defense), and type of play. PlayCalls can also have tags for categorization and
    filtering. They must use a subformation (a formation with a parent) to ensure
    specificity (this may change in the future).
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

    # ==============================
    # Setters
    # ==============================
    def add_tag(self, tag: str) -> None:
        if tag not in self._tags:
            self._tags.append(tag)

    # ==============================
    # Getters
    # ==============================
    @property
    def uid(self) -> str:
        return self._uid

    @property
    def tags(self) -> List[str]:
        return self._tags

    # ==============================
    # Validators
    # ==============================
    def _validate(self) -> None:
        self._validate_parent()
        self._validate_personnel()

    def _validate_parent(self) -> None:
        """Ensure that the formation used is a subformation (has a parent)."""
        if self.formation.parent is None:
            msg = (
                f"PlayCall '{self.name}' must use a subformation "
                f"(formation '{self.formation.name}' has no parent)"
            )
            logger.error(msg)
            raise PlayCallInitializationError(msg)

    def _validate_personnel(self) -> None:
        """Ensure that the formation and personnel package are compatible."""
        if self.side == PlaySideEnum.OFFENSE:
            valid_tree = POSITION_TREE.children[AthletePositionEnum.OFFENSE]
            side_label = "offensive"
        else:
            valid_tree = POSITION_TREE.children[AthletePositionEnum.DEFENSE]
            side_label = "defensive"

        # Validate each position in the formation
        for position in self.formation.positions:
            if not valid_tree.contains(position):
                msg = (
                    f"PlayCall '{self.name}' is {side_label} but formation "
                    f"'{self.formation.name}' includes invalid position '{position.name}'"
                )
                logger.error(msg)
                raise PlayCallInitializationError(msg)


class Playbook:
    """
    A Playbook contains a collection of PlayCalls that a team can use during a game.
    The Playbook allows for adding new plays and retrieving plays based on various
    criteria such as name, UID, tags, and play type. It serves as a repository of
    strategies and tactics that a team can employ.
    """

    def __init__(
        self,
        plays: Optional[List[PlayCall]] = None,
        uid: Optional[str] = None,
    ) -> None:
        self._uid = uid if uid else str(uuid.uuid4())
        self._plays = plays or []

    # ==============================
    # Setters
    # ==============================
    def add_play(self, play: PlayCall) -> None:
        self._plays.append(play)

    # ==============================
    # Getters
    # ==============================
    @property
    def uid(self) -> str:
        return self._uid

    @property
    def plays(self) -> List[PlayCall]:
        return self._plays.copy()

    def get_by_name(self, name: str) -> List[PlayCall]:
        return [play for play in self._plays if play.name == name]

    def get_by_uid(self, uid: str) -> Optional[PlayCall]:
        for play in self._plays:
            if play.uid == uid:
                return play
        return None

    def get_by_tag(self, tag: str) -> List[PlayCall]:
        return [play for play in self._plays if tag in play.tags]

    def get_by_type(self, play_type: PlayTypeEnum) -> List[PlayCall]:
        return [play for play in self._plays if play.play_type == play_type]

    def __len__(self) -> int:
        return len(self._plays)
