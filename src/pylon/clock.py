from simpy import Environment


class GameClock:
    """Football game clock wrapper for SimPy simulations.

    Tracks quarters, time remaining, overtime, and two-minute warnings.
    All state is derived from the `env.now`; the clock itself does not
    advance or keep time.
    """

    def __init__(
        self,
        env: Environment,
        minutes_per_quarter: int = 15,
        num_reg_quarters: int = 4,
    ) -> None:
        self.env = env
        self.min_per_qtr = minutes_per_quarter
        self.num_reg_qtrs = num_reg_quarters
        self.total_game_sec = self.min_per_qtr * self.num_reg_qtrs * 60
        self.clock_is_running: bool = False

    def is_overtime(self) -> bool:
        return self.current_quarter > self.num_reg_qtrs

    @property
    def current_quarter(self) -> int:
        return int(self.env.now // (self.min_per_qtr * 60)) + 1

    @property
    def time_remaining(self) -> int:
        return max(self.total_game_sec - int(self.env.now), 0)

    def __int__(self) -> int:
        """Convert the simpy.Environment.now to an integer number of seconds.

        This is how much time has elapsed since the start of the game.
        """
        return int(self.env.now)
