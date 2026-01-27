from abc import abstractmethod
from typing import Dict, List
import logging

from .model import TypedModel, ModelExecutionError
from ..state.game_state import GameState
from ..domain.playbook import PlayCall
from ..domain.athlete import Athlete, AthletePositionEnum, POSITION_TREE
from ..rng import RNG


logger = logging.getLogger(__name__)


class InvalidPersonnelError(Exception):
    pass


class PlaceKickerSelectionContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class KickoffReturnerSelectionContext:
    def __init__(self, game_state: GameState, rng: RNG) -> None:
        self.game_state = game_state
        self.rng = rng


class KickerSelectionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class PlayerAssignmentContext:
    def __init__(self, game_state: GameState, rng: RNG, play_call: PlayCall) -> None:
        self.game_state = game_state
        self.rng = rng
        self.play_call = play_call


class PasserSelectionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class PunterSelectionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class PuntReturnerSelectionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class TargettedSelectionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class RusherSelectionContext:
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        self.game_state = game_state
        self.rng = rng
        self.personnel_assignments = personnel_assignments


class OffensivePlayerAssignmentModel(
    TypedModel[PlayerAssignmentContext, Dict[AthletePositionEnum, List[Athlete]]]
):
    def __init__(self) -> None:
        super().__init__(name="offensive_play_personnel_assignment")

    @abstractmethod
    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]: ...


class DefaultOffensivePlayerAssignmentModel(OffensivePlayerAssignmentModel):
    """
    Assigns exactly 11 offensive players to formation slots using the PositionTree.

    Selection order:
    1. QB and Offensive Line (1LT, 1LG, 1C, 1RG, 1RT)
    2. Skill players from personnel package (RB/TE/WR)

    Formation is used ONLY for alignment, never for player selection.
    """

    BASE_OFFENSE: Dict[AthletePositionEnum, int] = {
        AthletePositionEnum.QB: 1,
        AthletePositionEnum.LT: 1,
        AthletePositionEnum.LG: 1,
        AthletePositionEnum.C: 1,
        AthletePositionEnum.RG: 1,
        AthletePositionEnum.RT: 1,
    }

    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        team = context.game_state.pos_team
        play = context.play_call
        formation = play.formation

        # Ensure formation defines exactly 11 slots
        total_slots = sum(formation.position_counts.values())
        if total_slots != 11:
            msg = (
                f"Formation '{formation.name}' defines {total_slots} slots (must be 11)"
            )
            logger.error(msg)
            raise ModelExecutionError(msg)

        selected: List[Athlete] = []

        # pick players using PositionTree
        def pick(position: AthletePositionEnum, count: int) -> List[Athlete]:
            chosen: List[Athlete] = []

            # Start at the leaf node for this position
            node = POSITION_TREE.children[AthletePositionEnum.OFFENSE].find_node(
                position
            )
            if node is None:
                raise ModelExecutionError(f"Unknown offensive position: {position}")

            # Walk upward until enough players are found (e.g. RT->T-->OLINE)
            while node is not None and len(chosen) < count:
                valid_positions = node.all_positions()

                candidates = [
                    p
                    for p in team.roster
                    if p.position in valid_positions
                    and p not in selected
                    and p not in chosen
                ]

                needed = count - len(chosen)
                chosen.extend(candidates[:needed])

                node = node.parent

            if len(chosen) < count:
                raise ModelExecutionError(
                    f"Not enough players for {position.name}: "
                    f"needed {count}, available {len(chosen)}"
                )

            selected.extend(chosen)
            return chosen

        # pick the qb and offensive line first
        for pos, count in self.BASE_OFFENSE.items():
            pick(pos, count)

        # pick skill players from personnel package (rb/te/wr)
        for pos, count in play.personnel_package.counts.items():
            pick(pos, count)

        # validate total count
        if len(selected) != 11:
            raise ModelExecutionError(
                f"Selected {len(selected)} offensive players (expected 11)"
            )

        # ensure we have no duplicates of athletes
        if len(set(selected)) != 11:
            raise ModelExecutionError("Duplicate players selected")

        # Dictionary to hold formation assignments
        assignments: Dict[AthletePositionEnum, List[Athlete]] = {
            pos: [] for pos in formation.position_counts
        }

        unused = selected.copy()

        for pos, count in formation.position_counts.items():
            # Natural position first
            natural = [p for p in unused if p.position == pos]
            take = natural[:count]
            assignments[pos].extend(take)
            for p in take:
                unused.remove(p)

            # flex using PositionTree if needed
            while len(assignments[pos]) < count:
                node = POSITION_TREE.children[AthletePositionEnum.OFFENSE].find_node(
                    pos
                )
                if node is None:
                    raise ModelExecutionError(f"Unknown offensive position: {pos}")

                # walk up the tree until we find a match
                filled = False
                while node is not None and not filled:
                    valid_positions = node.all_positions()
                    for p in unused:
                        if p.position in valid_positions:
                            assignments[pos].append(p)
                            unused.remove(p)
                            filled = True
                            break
                    node = node.parent

                if not filled:
                    msg = (
                        f"Cannot fill formation slot {pos.name} "
                        f"({len(assignments[pos])}/{count})"
                    )
                    logger.error(msg)
                    raise ModelExecutionError(msg)

        return assignments


class DefensivePlayerAssignmentModel(
    TypedModel[PlayerAssignmentContext, Dict[AthletePositionEnum, List[Athlete]]]
):
    def __init__(self) -> None:
        super().__init__(name="defensive_play_personnel_assignment")

    @abstractmethod
    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]: ...


class DefaultDefensivePlayerAssignmentModel(DefensivePlayerAssignmentModel):
    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        team = context.game_state.def_team
        play = context.play_call

        assignments: Dict[AthletePositionEnum, List[Athlete]] = {}

        for position, count in play.personnel_package.counts.items():
            selected: List[Athlete] = []

            node = POSITION_TREE.find_node(position)
            if node is None:
                raise ModelExecutionError(f"Unknown position in tree: {position}")

            # Walk upward until we find enough players
            while node is not None and len(selected) < count:
                valid_positions = node.all_positions()

                candidates = [
                    p
                    for p in team.roster
                    if p.position in valid_positions and p not in selected
                ]

                needed = count - len(selected)
                selected.extend(candidates[:needed])

                node = node.parent

            # If we still don't have enough players, error
            if len(selected) < count:
                msg = (
                    f"Not enough players to fill position {position.name}: "
                    f"required {count}, available {len(selected)}"
                )
                logger.error(msg)
                raise ModelExecutionError(msg)

            assignments[position] = selected

        return assignments


class RusherSelectionModel(TypedModel[RusherSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="rusher_selection")

    @abstractmethod
    def execute(self, context: RusherSelectionContext) -> Athlete: ...


class DefaultRusherSelectionModel(RusherSelectionModel):
    def execute(self, context: RusherSelectionContext) -> Athlete:
        # Simple model: Select a random running back from the personnel
        # that are involved in the play
        options = context.personnel_assignments.get(AthletePositionEnum.RB, [])
        return context.rng.choice(options)


class PasserSelectionModel(TypedModel[PasserSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="passer_selection")

    @abstractmethod
    def execute(self, context: PasserSelectionContext) -> Athlete: ...


class DefaultPasserSelectionModel(PasserSelectionModel):
    def execute(self, context: PasserSelectionContext) -> Athlete:
        qbs = context.personnel_assignments.get(AthletePositionEnum.QB, [])
        if len(qbs) < 1:
            msg = "No Athletes assigned to QB."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return qbs[0]


class TargettedSelectionModel(TypedModel[TargettedSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="targetted_selection")

    @abstractmethod
    def execute(self, context: TargettedSelectionContext) -> Athlete: ...


class DefaultTargettedSelectionModel(TargettedSelectionModel):
    def execute(self, context: TargettedSelectionContext) -> Athlete:
        targettable: List[Athlete] = []
        targettable.extend(
            context.personnel_assignments.get(AthletePositionEnum.WR, [])
        )
        targettable.extend(
            context.personnel_assignments.get(AthletePositionEnum.RB, [])
        )
        targettable.extend(
            context.personnel_assignments.get(AthletePositionEnum.TE, [])
        )

        return targettable[0]


class PunterSelectionModel(TypedModel[PunterSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="punter_selection")

    @abstractmethod
    def execute(self, context: PunterSelectionContext) -> Athlete: ...


class DefaultPunterSelectionModel(PunterSelectionModel):
    def execute(self, context: PunterSelectionContext) -> Athlete:
        punters = context.personnel_assignments.get(AthletePositionEnum.P, [])
        if len(punters) < 1:
            msg = "No Athletes assigned to Punter."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return punters[0]


class PuntReturnerSelectionModel(TypedModel[PuntReturnerSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="punt_returner_selection")

    @abstractmethod
    def execute(self, context: PuntReturnerSelectionContext) -> Athlete: ...


class DefaultPuntReturnerSelectionModel(PuntReturnerSelectionModel):
    def execute(self, context: PuntReturnerSelectionContext) -> Athlete:
        returners = context.personnel_assignments.get(AthletePositionEnum.KR, [])
        if len(returners) < 1:
            msg = "No Athletes assigned to Kick Returner."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return returners[0]


class KickerSelectionModel(TypedModel[KickerSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="kicker_selection")

    @abstractmethod
    def execute(self, context: KickerSelectionContext) -> Athlete: ...


class DefaultKickerSelectionModel(KickerSelectionModel):
    def execute(self, context: KickerSelectionContext) -> Athlete:
        kickers = context.personnel_assignments.get(AthletePositionEnum.K, [])
        if len(kickers) < 1:
            msg = "No Athletes assigned to Kicker."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return kickers[0]


class PlaceKickerSelectionModel(TypedModel[PlaceKickerSelectionContext, Athlete]):
    def __init__(self) -> None:
        super().__init__(name="place_kicker_selection")

    @abstractmethod
    def execute(self, context: PlaceKickerSelectionContext) -> Athlete: ...


class DefaultPlaceKickerSelectionModel(PlaceKickerSelectionModel):
    def execute(self, context: PlaceKickerSelectionContext) -> Athlete:
        kickers = [
            k
            for k in context.game_state.def_team.roster
            if k.position == AthletePositionEnum.K
        ]
        if len(kickers) < 1:
            msg = "No Athletes assigned to Place Kicker."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return kickers[0]


class KickoffReturnerSelectionModel(
    TypedModel[KickoffReturnerSelectionContext, Athlete]
):
    def __init__(self) -> None:
        super().__init__(name="kickoff_returner_selection")

    @abstractmethod
    def execute(self, context: KickoffReturnerSelectionContext) -> Athlete: ...


class DefaultKickoffReturnerSelectionModel(KickoffReturnerSelectionModel):
    def execute(self, context: KickoffReturnerSelectionContext) -> Athlete:
        returners = [
            a
            for a in context.game_state.pos_team.roster
            if a.position == AthletePositionEnum.WR
            or a.position == AthletePositionEnum.RB
        ]
        if len(returners) < 1:
            msg = "No Athletes assigned to Kick Returner."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return returners[0]
