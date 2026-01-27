"""
Abstract base rules and configurations for football simulations.

This module defines the LeagueRules interface that all league implementations must follow.
It also provides supporting data classes for configuring special plays like kickoffs and
extra points.

Key concepts:
- LeagueRules is the decision-maker for game flow: it decides what should happen according
  to the rule set, but does not mutate GameState directly.
- GameEngine and specific play engines call into LeagueRules to determine when transitions
  should occur (game start, halves, drive end, game end, etc.).
- Concrete implementations (e.g., NFLRules) override these methods to define league-specific
  behavior (quarter lengths, field dimensions, scoring, etc.).

Supporting classes:
- FirstDownRule: Configuration for first down yardage and down limits
- KickoffSetup: Configuration for kickoff plays
- ExtraPointSetup: Configuration for extra point attempts
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, Dict

from ...domain.team import Team
from ...models.registry import ModelRegistry
from ...rng import RNG

if TYPE_CHECKING:
    from ...state.game_state import GameState
    from ...state.drive_record import DriveRecord
    from ...state.play_record import PlayRecord, ScoringTypeEnum, PlayExecutionData


logger = logging.getLogger(__name__)


class LeagueRulesError(Exception):
    """
    Exception raised when a rule constraint is violated or an invalid state is encountered
    during rule evaluation.
    """

    pass


class FirstDownRule:
    """
    Configuration for first down rules.

    Encapsulates the yardage needed for a first down and the maximum number of downs
    allowed in a possession. Provides utilities for determining first down and turnover
    on downs scenarios.

    Attributes:
        first_down_yards: Number of yards needed to gain a first down (default: 10).
        max_downs: Maximum number of downs before turnover on downs (default: 4).
    """

    def __init__(self, first_down_yards: int = 10, max_downs: int = 4) -> None:
        assert first_down_yards > 0
        assert max_downs > 0
        self.first_down_yards = first_down_yards
        self.max_downs = max_downs

    def is_first_down(self, yards_gained: int, distance: int) -> bool:
        """
        Determine if a play resulted in a first down.

        Args:
            yards_gained: Yards gained on the play.
            distance: Yards needed for a first down.

        Returns:
            True if yards_gained >= distance, False otherwise.
        """
        return yards_gained >= distance

    def is_turnover_on_downs(
        self, current_down: int, yards_gained: int, distance: int
    ) -> bool:
        """
        Determine if a play resulted in a turnover on downs.

        Args:
            current_down: The current down (1-based).
            yards_gained: Yards gained on the play.
            distance: Yards needed for a first down.

        Returns:
            True if the play is on the last down and did not achieve a first down.
        """
        return current_down >= self.max_downs and yards_gained < distance


class KickoffSetup:
    """
    Configuration for a kickoff play.

    Stores the teams involved and the field position where the kickoff occurs.
    Validates that teams are different and the spot is on a valid part of the field.

    Attributes:
        kicking_team: The team performing the kickoff.
        receiving_team: The team receiving the kickoff.
        kickoff_spot: Yard line where the kickoff occurs (1-99, where 1 is own goal line).
    """

    def __init__(
        self, kicking_team: Team, receiving_team: Team, kickoff_spot: int
    ) -> None:
        """
        Initialize a KickoffSetup.

        Args:
            kicking_team: The team performing the kickoff.
            receiving_team: The team receiving the kickoff.
            kickoff_spot: Yard line (1-99). Must be different from receiving team.

        Raises:
            AssertionError: If spot is outside 1-99 or teams are the same.
        """
        assert kickoff_spot >= 1
        assert kickoff_spot <= 99
        assert kicking_team != receiving_team
        self.kicking_team = kicking_team
        self.receiving_team = receiving_team
        self.kickoff_spot = kickoff_spot


class ExtraPointSetup:
    """
    Configuration for an extra point attempt after a touchdown.

    Stores the team attempting the extra point and the field position from which
    the attempt is made.

    Attributes:
        kicking_team: The team attempting the extra point.
        spot: Yard line where the extra point attempt occurs (1-99).
    """

    def __init__(self, kicking_team: Team, spot: int) -> None:
        """
        Initialize an ExtraPointSetup.

        Args:
            kicking_team: The team attempting the extra point.
            spot: Yard line for the attempt (1-99).

        Raises:
            AssertionError: If spot is outside 1-99.
        """
        assert spot >= 1
        assert spot <= 99
        self.kicking_team = kicking_team
        self.spot = spot


# This is not set and stone. It is a starting point for defining the interface. At
# the end of the day, there will need to be some type of interface between the
# GameStateUpdater and the LeagueRules to determine what happens and when. This is
# just a first pass at that interface. If you have ideas for how to improve it, please
# share!
# Also, please note that the return types and parameters of these methods are not
# fully fleshed out. They are placeholders to illustrate the intended functionality.
class LeagueRules(ABC):
    """
    Abstract base class defining the rulebook for a football league.

    LeagueRules is responsible for *deciding* what should happen according to
    the league's rule set. It does not mutate GameState directly. Instead,
    GameStateUpdater should call into LeagueRules to determine:

    - when the game starts and how the opening kickoff is configured
    - when halves start and how possession is determined
    - when a drive ends
    - when the game ends
    - how scoring values are assigned
    - what special transitions (kickoffs, extra points) should occur

    Concrete implementations (e.g., NFLRules, NCAARules) override these methods
    to define league-specific behavior.
    """

    MINUTES_PER_QUARTER: int
    QUARTERS_PER_HALF: int
    TIMEOUTS_PER_HALF: int
    KICKOFF_SPOT: int
    EXTRA_POINT_SPOT: int
    FIELD_LENGTH: int
    MAX_DOWNS: int
    FIRST_DOWN_YARDS: int
    KICKOFF_TOUCHBACK_SPOT: int
    DEFAULT_TOUCHBACK_SPOT: int
    SCORING_VALUES: Dict[ScoringTypeEnum, int]

    # ==============================
    # Getters
    # ==============================
    def get_scoring_value(self, scoring_type: ScoringTypeEnum) -> int:
        if scoring_type not in self.SCORING_VALUES:
            msg = f"Scoring type {scoring_type} not recognized."
            logger.error(msg)
            raise LeagueRulesError(msg)

        return self.SCORING_VALUES.get(scoring_type, 0)

    @abstractmethod
    def start_game(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        """Called at the start of the game."""
        ...

    @abstractmethod
    def start_half(
        self, game_state: "GameState", models: ModelRegistry, rng: RNG
    ) -> None:
        """Called at the start of each half."""
        ...

    @abstractmethod
    def is_game_over(self, game_state: "GameState") -> bool:
        """Determines if the game is over."""
        ...

    @abstractmethod
    def is_half_over(self, game_state: "GameState") -> bool:
        """Determines if the current half is over."""
        ...

    @abstractmethod
    def is_drive_over(
        self, game_state: "GameState", drive_possession_team: Team, play_count: int
    ) -> bool:
        """Determines if a drive is over.

        Args:
            game_state: Current game state
            drive_possession_team: Team that had possession at start of drive
            play_count: Number of plays run in this drive so far
        """
        ...

    # LeagueRules should only decide, not mutate. The GameStateUpdater
    # will call this method to let the rules decide what to do at the end of
    # each drive. This need a rework to better separate concerns.
    @abstractmethod
    def on_drive_end(
        self,
        game_state: "GameState",
        drive_record: "DriveRecord",
    ) -> None:
        """Called at the end of each drive."""
        ...

    # LeagueRules should only decide, not mutate. The GameStateUpdater
    # will call this method to let the rules decide what to do at the end of
    # each play. This need a rework to better separate concerns.
    @abstractmethod
    def on_play_end(
        self,
        game_state: "GameState",
        play_record: "PlayRecord",
    ) -> None:
        """Called at the end of each play."""
        ...

    @abstractmethod
    def is_first_down(self, yards_gained: int, distance: int) -> bool:
        """Determine if the yards gained is enough for a first down."""
        ...

    @abstractmethod
    def is_turnover_on_downs(
        self, current_down: int, yards_gained: int, distance: int
    ) -> bool:
        """Determine if the play results in a turnover on downs."""
        ...

    def is_touchdown(self, end_spot: int, possession_changed: bool) -> bool:
        """Determine if the play resulted in a touchdown."""
        # Offense reaches endzone without possession change
        if end_spot >= 100 and not possession_changed:
            return True
        # Defense returns turnover to endzone
        if end_spot <= 0 and possession_changed:
            return True
        return False

    def is_safety(self, end_spot: int, possession_changed: bool) -> bool:
        """Determine if the play resulted in a safety."""
        # Offense tackled in their own endzone
        return end_spot <= 0 and not possession_changed

    def is_touchback(
        self, end_spot: int, possession_changed: bool, is_kick: bool
    ) -> bool:
        """Determine if the play resulted in a touchback."""
        # Defense takes over in their endzone on a kick play
        return end_spot >= 100 and possession_changed and is_kick

    def get_next_down(self, current_down: int, yards_gained: int, distance: int) -> int:
        """Determine the next down number based on the play result."""
        if self.is_first_down(yards_gained, distance):
            return 1  # Reset to first down
        return current_down + 1

    def get_next_distance(
        self, ball_position: int, yards_gained: int, distance: int
    ) -> int:
        """Determine the next distance to go based on the play result."""
        if self.is_first_down(yards_gained, distance):
            # First down - reset distance
            return min(self.FIRST_DOWN_YARDS, ball_position)
        # Same series, reduce distance by yards gained
        return distance - yards_gained

    @abstractmethod
    def handle_post_score_possession(
        self, game_state: "GameState", play_data: "PlayExecutionData"
    ) -> None:
        """
        Called after a score to determine what happens next (typically a kickoff).
        LeagueRules should decide, GameStateUpdater will apply.
        """
        ...

    @abstractmethod
    def handle_touchback(
        self, game_state: "GameState", play_data: "PlayExecutionData"
    ) -> None:
        """
        Called when a touchback occurs to set up possession properly.
        LeagueRules should decide, GameStateUpdater will apply.
        """
        ...

    @abstractmethod
    def get_touchback_spot(self, is_kickoff: bool) -> int:
        """
        Returns the yard line where the ball is placed after a touchback.
        For NFL, this is the 25 yard line.
        """
        ...
