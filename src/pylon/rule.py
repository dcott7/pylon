from .state import GameState


class GameRules:
    def __init__(self) -> None:
        pass

    def is_game_over(self, state: GameState) -> bool:
        # regulation-only placeholder
        if state.clock.time_remaining > 0:
            return False

        return not state.scoreboard.is_tied()


class NFLRegularSeasonGameRules(GameRules):
    """
    NFL Regular Season Game Rules
    """

    MAX_OT_SECONDS = 10 * 60  # 10-minute overtime

    def is_game_over(self, state: GameState) -> bool:

        if state.clock.time_remaining > 0:
            return False

        if not state.scoreboard.is_tied():
            return True

        if not state.clock.is_overtime():
            return False

        if self._defense_scored_on_first_possession(state):
            return True

        # 5. Both teams have possessed at least once
        if self._both_teams_possessed(state):
            if not state.scoreboard.is_tied():
                return True

        # 6. Overtime time expired → tie
        if state.overtime_elapsed >= self.MAX_OT_SECONDS:
            return True

        return False
