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
        """
        NFL Regular Season Overtime Rules

        At the end of regulation, the referee will toss a coin to determine
        which team will possess the ball first in overtime. The visiting team
        captain will call the toss.

        No more than one 10-minute period will follow a three-minute
        intermission. Each team must have the opportunity to possess the ball.
        The exception: if the team kicking off to start the overtime period
        scores a safety on the receiving team’s initial possession, in which
        case the team that kicked off is the winner.

        After each team has had an opportunity to possess the ball, if one team
        has more points than its opponent, it is the winner (subject to the
        General Rules Applicable to Overtime). If the team that possesses the
        ball first does not score on its initial possession, or if the score is
        tied after each team has had its opportunity to possess the ball, the
        team that scores next, by any method, is the winner.

        Each team gets two timeouts.

        If the score is still tied at the end of the overtime period, the result
        of the game will be recorded as a tie.

        There are no instant replay coach’s challenges; all reviews will be
        initiated by the replay official.
        """

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
