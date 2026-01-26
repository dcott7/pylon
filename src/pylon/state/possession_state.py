import logging
from typing import Optional

from ..domain.team import Team


logger = logging.getLogger(__name__)


class PossessionState:
    """
    Mutable, authoritative possession state.

    Attributes:
        pos_team (Team): The team currently in possession of the ball.
        ball_position (int): The current position of the ball on the field (yard line) relative
            to the offense's end zone. An offense need to get to the 0 yard line to score.
        down (int): The current down (1 to 4).
        distance (int): The yards to go for a first down.
    """

    FIELD_LENGTH = 100  # Standard American football field length in yards

    def __init__(
        self,
        pos_team: Team,
        ball_position: int,
        down: Optional[int],  # None if not applicable
        distance: Optional[int],  # None if not applicable
    ) -> None:
        self._pos_team = pos_team
        self._ball_position = ball_position
        self._down = down
        self._distance = distance

    # ===============================
    # Setters
    # ===============================
    def set_pos_team(self, team: Team) -> None:
        self._pos_team = team

    def set_ball_position(self, ball_position: int) -> None:
        self._ball_position = ball_position

    def set_down(self, down: int) -> None:
        self._down = down

    def set_distance(self, distance: int) -> None:
        self._distance = distance

    # ===============================
    # Getters
    # ===============================
    @property
    def pos_team(self) -> Team:
        return self._pos_team

    @property
    def ball_position(self) -> int:
        return self._ball_position

    @property
    def down(self) -> Optional[int]:
        return self._down

    @property
    def distance(self) -> Optional[int]:
        return self._distance

    # ===============================
    # Mutators
    # ==============================
    def advance_ball(self, yards: int) -> None:
        assert self._distance is not None
        self._ball_position += yards
        self._distance -= yards
        logger.debug(
            f"Ball position updated to {self._ball_position} after gaining {yards} yards."
        )

    def reset_down_and_distance(self) -> None:
        self._down = 1
        self._distance = 10
        logger.debug("Down and distance reset to 1st and 10.")

    def flip_field(self) -> None:
        self._ball_position = PossessionState.FIELD_LENGTH - self._ball_position
        logger.debug(f"Field flipped. New ball position: {self._ball_position}.")

    # ===============================
    # Validators
    # ===============================
    def assert_down_and_distance_set(self) -> None:
        if self._down is not None and self._distance is not None:
            return
        msg = "Down and distance must be set for the current possession."
        logger.error(msg)
        raise ValueError(msg)
