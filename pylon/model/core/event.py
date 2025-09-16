from abc import ABC, abstractmethod


class SimulationEvent(ABC):
    """
    SimulationEvent should be inherited by ALL
    simulation events. All of these events should 
    define an execute method that processes the event
    and possibly schedules other follow-on events.
    """
    def __init__(self, name: str, priority: int) -> None:
        self._name = name
        self._priority: int = priority
        self._scheduled_time: int = None

    def schedule(self, schedule_time: int) -> None:
        self._scheduled_time = schedule_time

    @abstractmethod
    def execute(self, simulation: "Simulation") -> None:
        raise NotImplementedError()
    
    def priority(self):
        return self._priority

    def is_scheduled(self):
        return self._scheduled_time is not None
    
    def when_scheduled(self) -> int:
        return self._scheduled_time
    
    def __lt__(self, event: "SimulationEvent") -> bool:
        """
        Comparison operation to determine the order in 
        processing of events for the heap queue in 
        Simulation.
        """
        return (self.when_scheduled(), self.priority()) < (event.when_scheduled(), event.priority())