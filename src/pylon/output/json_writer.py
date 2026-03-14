"""JSON output writer for simulation results."""

import json
from pathlib import Path

from .types import SimulationOutputPayload


class JsonOutputWriter:
    """Writes simulation results to JSON file output."""

    def __init__(self, output_path: Path | str) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write_results(self, results: SimulationOutputPayload) -> Path:
        """Write simulation results to JSON and return the resolved output path."""
        with open(self.output_path, "w", encoding="utf-8") as file_handle:
            json.dump(results, file_handle, indent=2)
        return self.output_path
