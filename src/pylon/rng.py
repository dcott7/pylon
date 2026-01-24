from typing import Optional, Sequence, TypeVar
import random
import logging
import time


logger = logging.getLogger(__name__)


T = TypeVar("T")


class RNG:
    """
    Random Number Generator wrapper class. Uses Python's built-in random module
    to generate random numbers with an optional seed for reproducibility.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is None:
            seed = int(time.time_ns() & 0xFFFFFFFF)
            logger.debug(f"RNG initialized with generated seed={seed}")

        self._seed = seed
        self._rng = random.Random(seed)

    # ===============================
    # Getters
    # ===============================
    @property
    def seed(self) -> int:
        return self._seed

    # ===============================
    # Random Methods
    # ===============================
    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        return self._rng.choice(seq)
