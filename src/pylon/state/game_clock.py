class GameClock:
    """Football game clock wrapper for seconds elapsed.

    Tracks quarters, time remaining, overtime, and two-minute warnings.
    All state is derived from the `seconds_elapsed`; the clock itself does not
    advance or keep time.
    """

    def __init__(
        self,
        seconds_elapsed: int,
        minutes_per_quarter: int = 15,
        num_reg_quarters: int = 4,
    ) -> None:
        self.seconds_elapsed = seconds_elapsed
        self.min_per_qtr = minutes_per_quarter
        self.num_reg_qtrs = num_reg_quarters
        self.total_game_sec = self.min_per_qtr * self.num_reg_qtrs * 60
        self.clock_is_running: bool = False

    def is_overtime(self) -> bool:
        return self.current_quarter > self.num_reg_qtrs

    @property
    def current_quarter(self) -> int:
        return int(self.seconds_elapsed // (self.min_per_qtr * 60)) + 1

    @property
    def time_remaining(self) -> int:
        return max(self.total_game_sec - int(self.seconds_elapsed), 0)

    def is_expired(self) -> bool:
        return self.time_remaining <= 0

    def project(self, seconds_elapsed: int) -> tuple[int, int]:
        """
        Return (quarter, time_remaining) after advancing the clock
        by the given number of seconds, without mutating state.
        """
        projected_now = int(self.seconds_elapsed) + seconds_elapsed

        quarter = int(projected_now // (self.min_per_qtr * 60)) + 1
        time_remaining = max(self.total_game_sec - projected_now, 0)

        return quarter, time_remaining
