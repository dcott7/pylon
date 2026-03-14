from abc import abstractmethod
from typing import Dict, List
import logging

from .model import TypedModel, ModelExecutionError, ModelContext
from ..state.game_state import GameState
from ..domain.playbook import PlayCall, PlayTypeEnum
from ..domain.athlete import Athlete, AthletePositionEnum, POSITION_TREE
from ..domain.team import Team
from ...sim.rng import RNG


logger = logging.getLogger(__name__)


# ==============================
# Personnel Errors
# ==============================


class InvalidPersonnelError(Exception):
    pass


# ==============================
# Personnel Model Contexts
# ==============================


class PlayerSelectionContext(ModelContext):
    """
    Base context for selecting a player for a specific role from personnel
    already assigned to the field (e.g. passer, rusher, target).
    """

    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        personnel_assignments: Dict[AthletePositionEnum, List[Athlete]],
    ) -> None:
        super().__init__(game_state, rng)
        self.personnel_assignments = personnel_assignments


class PlaceKickerSelectionContext(ModelContext):
    pass


class KickoffReturnerSelectionContext(ModelContext):
    pass


class KickerSelectionContext(PlayerSelectionContext):
    pass


class PasserSelectionContext(PlayerSelectionContext):
    pass


class SackerSelectionContext(PlayerSelectionContext):
    pass


class PunterSelectionContext(PlayerSelectionContext):
    pass


class PuntReturnerSelectionContext(PlayerSelectionContext):
    pass


class TargettedSelectionContext(PlayerSelectionContext):
    pass


class InterceptorSelectionContext(PlayerSelectionContext):
    pass


class RusherSelectionContext(PlayerSelectionContext):
    pass


class PlayerAssignmentContext(ModelContext):
    def __init__(
        self,
        game_state: GameState,
        rng: RNG,
        play_call: PlayCall | None,
        play_type: PlayTypeEnum | None = None,
    ) -> None:
        super().__init__(game_state, rng)
        self.play_call = play_call
        self.play_type = play_type


# ==============================
# Personnel Models
# ==============================


class OffensivePlayerAssignmentModel(
    TypedModel[PlayerAssignmentContext, Dict[AthletePositionEnum, List[Athlete]]]
):
    """
    Determines which offensive players are assigned to the play and on the field.
    This is used for selecting players for specific roles during play execution (e.g.
    passer, rusher, targetted, kicker). This is called for typical offensive plays as
    well as special teams plays (field goals, punts, kickoffs).
    """

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

        # Fallback path for playbook-optional simulations.
        if context.play_call is None:
            return self._fallback_assignments(team, context.play_type)

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

    def _fallback_assignments(
        self, team: Team, play_type: PlayTypeEnum | None
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        if play_type is None:
            raise ModelExecutionError(
                "play_type is required when play_call is None for offensive assignments"
            )

        # Minimal viable offensive personnel by play type.
        if play_type.is_field_goal():
            fallback_counts = {
                AthletePositionEnum.K: 1,
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.LT: 1,
                AthletePositionEnum.LG: 1,
                AthletePositionEnum.C: 1,
                AthletePositionEnum.RG: 1,
                AthletePositionEnum.RT: 1,
                AthletePositionEnum.TE: 3,
                AthletePositionEnum.RB: 1,
            }
        elif play_type.is_punt():
            fallback_counts = {
                AthletePositionEnum.P: 1,
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.LT: 1,
                AthletePositionEnum.LG: 1,
                AthletePositionEnum.C: 1,
                AthletePositionEnum.RG: 1,
                AthletePositionEnum.RT: 1,
                AthletePositionEnum.TE: 2,
                AthletePositionEnum.WR: 2,
            }
        else:
            fallback_counts = {
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.LT: 1,
                AthletePositionEnum.LG: 1,
                AthletePositionEnum.C: 1,
                AthletePositionEnum.RG: 1,
                AthletePositionEnum.RT: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.TE: 1,
                AthletePositionEnum.WR: 3,
            }

        assignments: Dict[AthletePositionEnum, List[Athlete]] = {}
        selected: List[Athlete] = []

        def pick(position: AthletePositionEnum, count: int) -> List[Athlete]:
            chosen: List[Athlete] = []
            node = POSITION_TREE.find_node(position)
            if node is None:
                raise ModelExecutionError(f"Unknown offensive position: {position}")

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
                    f"Not enough players for fallback position {position.name}: "
                    f"needed {count}, available {len(chosen)}"
                )

            selected.extend(chosen)
            return chosen

        for pos, count in fallback_counts.items():
            assignments[pos] = pick(pos, count)

        if len(selected) != 11:
            raise ModelExecutionError(
                f"Selected {len(selected)} offensive fallback players (expected 11)"
            )

        return assignments


class DefensivePlayerAssignmentModel(
    TypedModel[PlayerAssignmentContext, Dict[AthletePositionEnum, List[Athlete]]]
):
    """Assigns defensive players to positions for a play."""

    def __init__(self) -> None:
        super().__init__(name="defensive_play_personnel_assignment")

    @abstractmethod
    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]: ...


class DefaultDefensivePlayerAssignmentModel(DefensivePlayerAssignmentModel):
    """Baseline defensive assignment model using the PositionTree and play personnel."""

    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        team = context.game_state.def_team

        if context.play_call is None:
            return self._fallback_assignments(team)

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

    def _fallback_assignments(
        self, team: Team
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        fallback_counts: Dict[AthletePositionEnum, int] = {
            AthletePositionEnum.EDGE: 2,
            AthletePositionEnum.DT: 2,
            AthletePositionEnum.LB: 3,
            AthletePositionEnum.CB: 2,
            AthletePositionEnum.FS: 1,
            AthletePositionEnum.SS: 1,
        }

        assignments: Dict[AthletePositionEnum, List[Athlete]] = {}
        selected_all: List[Athlete] = []

        for position, count in fallback_counts.items():
            selected: List[Athlete] = []

            node = POSITION_TREE.find_node(position)
            if node is None:
                raise ModelExecutionError(f"Unknown position in tree: {position}")

            while node is not None and len(selected) < count:
                valid_positions = node.all_positions()
                candidates = [
                    p
                    for p in team.roster
                    if p.position in valid_positions
                    and p not in selected
                    and p not in selected_all
                ]
                needed = count - len(selected)
                selected.extend(candidates[:needed])
                node = node.parent

            if len(selected) < count:
                raise ModelExecutionError(
                    f"Not enough players to fill fallback position {position.name}: "
                    f"required {count}, available {len(selected)}"
                )

            assignments[position] = selected
            selected_all.extend(selected)

        return assignments


class RusherSelectionModel(TypedModel[RusherSelectionContext, Athlete]):
    """Selects the rusher for a run play."""

    def __init__(self) -> None:
        super().__init__(name="rusher_selection")

    @abstractmethod
    def execute(self, context: RusherSelectionContext) -> Athlete: ...


class DefaultRusherSelectionModel(RusherSelectionModel):
    """Baseline rusher selection: random RB from assigned personnel."""

    def execute(self, context: RusherSelectionContext) -> Athlete:
        # Simple model: Select a random running back from the personnel
        # that are involved in the play
        options = context.personnel_assignments.get(AthletePositionEnum.RB, [])
        return context.rng.choice(options)


class PasserSelectionModel(TypedModel[PasserSelectionContext, Athlete]):
    """Selects the passer for a pass play."""

    def __init__(self) -> None:
        super().__init__(name="passer_selection")

    @abstractmethod
    def execute(self, context: PasserSelectionContext) -> Athlete: ...


class DefaultPasserSelectionModel(PasserSelectionModel):
    """Baseline passer selection: first QB in assigned personnel."""

    def execute(self, context: PasserSelectionContext) -> Athlete:
        qbs = context.personnel_assignments.get(AthletePositionEnum.QB, [])
        if len(qbs) < 1:
            msg = "No Athletes assigned to QB."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return qbs[0]


class SackerSelectionModel(TypedModel[SackerSelectionContext, Athlete]):
    """Selects the defender credited with a sack."""

    def __init__(self) -> None:
        super().__init__(name="sacker_selection")

    @abstractmethod
    def execute(self, context: SackerSelectionContext) -> Athlete: ...


class DefaultSackerSelectionModel(SackerSelectionModel):
    """Baseline sacker selection: random defender from assigned personnel."""

    def execute(self, context: SackerSelectionContext) -> Athlete:
        players = [
            p for _, players in context.personnel_assignments.items() for p in players
        ]
        return context.rng.choice(players)


class TargettedSelectionModel(TypedModel[TargettedSelectionContext, Athlete]):
    """Selects the targeted receiver on a pass play."""

    def __init__(self) -> None:
        super().__init__(name="targetted_selection")

    @abstractmethod
    def execute(self, context: TargettedSelectionContext) -> Athlete: ...


class InterceptorSelectionModel(TypedModel[InterceptorSelectionContext, Athlete]):
    """Selects the defender credited with an interception."""

    def __init__(self) -> None:
        super().__init__(name="interceptor_selection")

    @abstractmethod
    def execute(self, context: InterceptorSelectionContext) -> Athlete: ...


class DefaultInterceptorSelectionModel(InterceptorSelectionModel):
    """Baseline interceptor selection: random defender from assigned personnel."""

    def execute(self, context: InterceptorSelectionContext) -> Athlete:
        players = [
            p for _, players in context.personnel_assignments.items() for p in players
        ]
        return context.rng.choice(players)


class DefaultTargettedSelectionModel(TargettedSelectionModel):
    """Baseline target selection: first eligible WR/RB/TE in assignments."""

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
    """Selects the punter for a punt play."""

    def __init__(self) -> None:
        super().__init__(name="punter_selection")

    @abstractmethod
    def execute(self, context: PunterSelectionContext) -> Athlete: ...


class DefaultPunterSelectionModel(PunterSelectionModel):
    """Baseline punter selection: first P in assigned personnel."""

    def execute(self, context: PunterSelectionContext) -> Athlete:
        punters = context.personnel_assignments.get(AthletePositionEnum.P, [])
        if len(punters) < 1:
            msg = "No Athletes assigned to Punter."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return punters[0]


class PuntReturnerSelectionModel(TypedModel[PuntReturnerSelectionContext, Athlete]):
    """Selects the punt returner."""

    def __init__(self) -> None:
        super().__init__(name="punt_returner_selection")

    @abstractmethod
    def execute(self, context: PuntReturnerSelectionContext) -> Athlete: ...


class DefaultPuntReturnerSelectionModel(PuntReturnerSelectionModel):
    """Baseline punt returner selection: first KR in assigned personnel."""

    def execute(self, context: PuntReturnerSelectionContext) -> Athlete:
        returners = context.personnel_assignments.get(AthletePositionEnum.KR, [])
        if len(returners) < 1:
            msg = "No Athletes assigned to Kick Returner."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return returners[0]


class KickerSelectionModel(TypedModel[KickerSelectionContext, Athlete]):
    """Selects the kicker for a kick play."""

    def __init__(self) -> None:
        super().__init__(name="kicker_selection")

    @abstractmethod
    def execute(self, context: KickerSelectionContext) -> Athlete: ...


class DefaultKickerSelectionModel(KickerSelectionModel):
    """Baseline kicker selection: first K in assigned personnel."""

    def execute(self, context: KickerSelectionContext) -> Athlete:
        kickers = context.personnel_assignments.get(AthletePositionEnum.K, [])
        if len(kickers) < 1:
            msg = "No Athletes assigned to Kicker."
            logger.error(msg)
            raise InvalidPersonnelError(msg)

        return kickers[0]


class PlaceKickerSelectionModel(TypedModel[PlaceKickerSelectionContext, Athlete]):
    """Selects the place kicker from the kicking team's roster."""

    def __init__(self) -> None:
        super().__init__(name="place_kicker_selection")

    @abstractmethod
    def execute(self, context: PlaceKickerSelectionContext) -> Athlete: ...


class DefaultPlaceKickerSelectionModel(PlaceKickerSelectionModel):
    """Baseline place kicker selection: first K from the defending team roster."""

    def execute(self, context: PlaceKickerSelectionContext) -> Athlete:
        # For kickoffs, select from the kicking team's roster (def_team)
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
    """Selects the kickoff returner from the receiving team's roster."""

    def __init__(self) -> None:
        super().__init__(name="kickoff_returner_selection")

    @abstractmethod
    def execute(self, context: KickoffReturnerSelectionContext) -> Athlete: ...


class DefaultKickoffReturnerSelectionModel(KickoffReturnerSelectionModel):
    """Baseline kickoff returner selection: first available KR, then WR, then RB."""

    def execute(self, context: KickoffReturnerSelectionContext) -> Athlete:
        # For kickoffs, select from the receiving team's roster (pos_team)
        # Prefer KR, then WR, then RB
        preferred_positions = [
            AthletePositionEnum.KR,
            AthletePositionEnum.WR,
            AthletePositionEnum.RB,
        ]

        for position in preferred_positions:
            returners = [
                a for a in context.game_state.pos_team.roster if a.position == position
            ]
            if returners:
                return returners[0]

        msg = "No Athletes available for Kick Returner (tried KR, WR, RB)."
        logger.error(msg)
        raise InvalidPersonnelError(msg)
