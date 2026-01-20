import logging

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
        self, pos_team: Team, ball_position: int, down: int, distance: int
    ) -> None:
        self._pos_team = pos_team
        self._ball_position = ball_position
        self._down = down
        self._distance = distance

    def advance_ball(self, yards: int) -> None:
        self._ball_position += yards
        self._distance -= yards
        logger.debug(
            f"Ball position updated to {self._ball_position} after gaining {yards} yards."
        )

    def set_state(
        self, pos_team: Team, ball_position: int, down: int, distance: int
    ) -> None:
        self._pos_team = pos_team
        self._ball_position = ball_position
        self._down = down
        self._distance = distance
        logger.debug(
            f"Possession state set to ball position: {ball_position}, down: {down}, distance: {distance}."
        )

    def reset_down_and_distance(self) -> None:
        self._down = 1
        self._distance = 10
        logger.debug("Down and distance reset to 1st and 10.")

    def update_down(self, down: int) -> None:
        self._down = down
        logger.debug(f"Down updated to {self._down}.")

    def update_distance(self, distance: int) -> None:
        self._distance = distance
        logger.debug(f"Distance to first down updated to {self._distance} yards.")

    def update_ball_position(self, ball_position: int) -> None:
        self._ball_position = ball_position
        logger.debug(f"Ball position updated to {self._ball_position}.")

    def update_possession(self, team: Team) -> None:
        self._pos_team = team
        logger.debug(f"Possession updated to team: {team.name}.")

    def set_possession(self, team: Team) -> None:
        self._pos_team = team
        logger.debug(f"Possession changed to team: {team.name}.")

    def flip_field(self) -> None:
        self._ball_position = PossessionState.FIELD_LENGTH - self._ball_position
        logger.debug(f"Field flipped. New ball position: {self._ball_position}.")

    @property
    def pos_team(self) -> Team:
        return self._pos_team

    @property
    def ball_position(self) -> int:
        return self._ball_position

    @property
    def down(self) -> int:
        return self._down

    @property
    def distance(self) -> int:
        return self._distance
