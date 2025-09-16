import heapq
import random
from time import perf_counter
from typing import List, Optional


from .event import SimulationEvent
from .exceptions import SimulationError


class Simulation:
    def __init__(self, seed: Optional[int]) -> None:
        self._seed = seed if seed is not None else random.randrange(1 << 30)
        random.seed(self._seed)
        self._queue: List[SimulationEvent] = []
        self._simtime = 0
        self._is_running: bool = False
        self._sim_start_time: Optional[float] = None
        self._total_run_time: Optional[float] = None

    def queue(self) -> List[SimulationEvent]:
        return self._queue
    
    def simtime(self) -> int:
        return self._simtime
    
    def sim_start_time(self) -> float:
        return self._sim_start_time
    
    def current_runtime(self) -> float:
        return perf_counter() - self.sim_start_time()
    
    def is_running(self) -> bool:
        return self._is_running
    
    def schedule_event(self, event: SimulationEvent, scheduled_time: int) -> None:
        if scheduled_time < self.simtime():
            raise SimulationError(f"Attempted to schedule event in the past {scheduled_time}<{self.simtime()}")
        event.schedule(scheduled_time)
        heapq.heappush(self._queue, event)

    def execute(self) -> None:
        if self._is_running:
            raise SimulationError("Simulation already running")
        
        self._sim_start_time = perf_counter()
        self._is_running = True

        while self._is_running and self._queue:
            event = heapq.heappop(self._queue)
            self._simtime = event.when_scheduled()
            event.execute()

        self._is_running = False
        self._total_run_time = self.current_runtime()

    def total_run_time(self) -> float:
        return self._total_run_time
    
    def stop(self):
        self._is_running = False