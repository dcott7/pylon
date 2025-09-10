import logging 


logger = logging.getLogger(__name__)


class Clock:
    def __init__(self, total_minutes: int) -> None:
        self.total_time_sec = total_minutes * 60
        self.current_time_sec = self.total_time_sec
        self.is_running = False
        logger.debug(f"Clock initialized with {total_minutes} minutes "
                     f"({self.total_time_sec} seconds)")

    def advance(self, seconds: int, is_running: bool = True) -> None:
        """Advance the clock by `seconds`. 
        If is_running=True, clock continues running after the advance.
        If is_running=False, clock stops after the advance.
        """
        old_time = self.current_time_sec
        self.current_time_sec = max(0, self.current_time_sec - seconds)
        self.is_running = is_running

        logger.info(
            f"Clock advanced by {seconds} seconds "
            f"({old_time} -> {self.current_time_sec}), "
            f"{'running' if self.is_running else 'stopped'}"
        )

        if self.current_time_sec == 0:
            logger.warning("Clock has expired (0:00)")

    def reset(self) -> None:
        """Reset the clock to full time."""
        self.current_time_sec = self.total_time_sec
        self.is_running = False
        logger.info("Clock reset to full time")

    def time_remaining(self) -> int:
        return self.current_time_sec

    def minutes(self) -> int:
        return self.current_time_sec // 60

    def seconds(self) -> int:
        return self.current_time_sec % 60

    def __str__(self) -> str:
        return f"Clock({self.minutes()}:{self.seconds():02})"

    def __repr__(self) -> str:
        return self.__str__()


class GameClock(Clock):
    def __init__(self, minutes_per_quarter: int = 15, num_reg_quarters: int = 4) -> None:
        super().__init__(minutes_per_quarter * num_reg_quarters)
        self.minutes_per_quarter = minutes_per_quarter
        self.num_reg_quarters = num_reg_quarters
        self.quarter = 1
        logger.debug(f"GameClock initialized: {self.num_reg_quarters} quarters of "
                     f"{minutes_per_quarter} minutes each")

    def advance(self, seconds: int, is_running: bool = True) -> None:
        old_quarter = self.quarter
        super().advance(seconds, is_running)

        elapsed = self.total_time_sec - self.current_time_sec
        quarter_length = self.minutes_per_quarter * 60
        self.quarter = elapsed // quarter_length + 1

        if self.quarter != old_quarter:
            logger.info(f"Quarter advanced from {old_quarter} to {self.quarter}")

    def reset(self) -> None:
        """Reset the clock and set back to first quarter."""
        super().reset()
        self.quarter = 1
        logger.info("GameClock reset to Quarter 1")

    def __str__(self) -> str:
        return f"GameClock(Quarter {self.quarter}, {self.minutes()}:{self.seconds():02})"

    def __repr__(self) -> str:
        return self.__str__()
