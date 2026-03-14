"""Unit tests for deterministic RNG behavior."""

from sim.rng import RNG


class TestRNG:
    """Tests for RNG class."""

    def test_rng_deterministic(self) -> None:
        """Test that RNG with the same seed produces the same sequence."""
        rng1 = RNG(seed=42)
        rng2 = RNG(seed=42)

        results1 = [rng1.random() for _ in range(10)]
        results2 = [rng2.random() for _ in range(10)]

        assert results1 == results2

    def test_rng_different_seeds(self) -> None:
        """Test that different seeds produce different sequences."""
        rng1 = RNG(seed=42)
        rng2 = RNG(seed=43)

        results1 = [rng1.random() for _ in range(10)]
        results2 = [rng2.random() for _ in range(10)]

        assert results1 != results2

    def test_rng_choice(self) -> None:
        """Test RNG choice returns values from the provided options."""
        rng = RNG(seed=42)
        options = ["A", "B", "C", "D"]

        choices = [rng.choice(options) for _ in range(20)]

        assert all(choice in options for choice in choices)
        assert len(set(choices)) > 1

    def test_rng_randint(self) -> None:
        """Test RNG randint returns values within the specified range."""
        rng = RNG(seed=42)

        results = [rng.randint(1, 10) for _ in range(20)]

        assert all(1 <= value <= 10 for value in results)
        assert len(set(results)) > 1
