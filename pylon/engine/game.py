from enum import auto, Enum
import logging


logger = logging.getLogger(__name__)


class SimulationStatus(Enum):
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    FINISHED = auto()

