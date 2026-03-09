import logging
import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List

from pylon.domain.team import Team
from pylon.domain.rules.nfl import NFLRules
from pylon.engine import SimulationRunner
from pylon.db import DatabaseManager

from .utils.teams import load_team


TEAM_NAMES = ["Bears", "49ers"]

# setup paths
NUM_REPS = 50
LOG_LEVEL = logging.DEBUG
EXAMPLE_DIR = Path(__file__).parent
ROOT_DIR = EXAMPLE_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DB_PATH = DATA_DIR / "football.db"
PYLON_DB_PATH = EXAMPLE_DIR / "pylon_sim.db"


def load_teams(conn: sqlite3.Connection) -> Dict[str, Team]:
    """Load Bear and 49ers teams from the example database."""
    teams: Dict[str, Team] = {}
    for team_name in TEAM_NAMES:
        team = load_team(conn, team_name)

        if team is None:
            msg = f"Failed to load team: {team_name}"
            logging.error(msg)
            raise ValueError(msg)

        teams[team.name] = team
    return teams


def main() -> None:
    # Clean up old database to avoid constraint violations on re-runs
    if Path(PYLON_DB_PATH).exists():
        Path(PYLON_DB_PATH).unlink()

    # Setup logging
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(EXAMPLE_DIR / "pylon.log"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)

    # Load teams from example database
    example_conn = sqlite3.connect(INPUT_DB_PATH)
    teams = load_teams(example_conn)
    example_conn.close()

    home = teams["Bears"]
    away = teams["49ers"]

    logger.info(f"Home: {home.name}")
    logger.info(f"Away: {away.name}")

    # Initialize Pylon database for persistence
    db_manager = DatabaseManager(f"sqlite:///{PYLON_DB_PATH}")
    db_manager.init_db()

    # Run multi-rep simulation with per-rep logs under ./log
    logger.info(f"\n--- Running multi-rep simulation ({NUM_REPS} reps) ---")
    runner = SimulationRunner(
        home_team=home,
        away_team=away,
        num_reps=NUM_REPS,
        base_seed=42,
        rules=NFLRules(),
        db_manager=db_manager,
        experiment_name=f"{away.name} at {home.name} - {NUM_REPS} Rep Test",
        experiment_description="Test run of multi-rep simulation with database persistence",
        log_dir=EXAMPLE_DIR / "log",
        log_level=LOG_LEVEL,
        # max_drives=100,  # Uncomment to limit drives per game for debugging infinate loops
    )
    results = runner.run()

    # Log aggregate results
    logger.info("\n" + "=" * 80)
    logger.info("Simulation Results")
    logger.info("=" * 80)
    logger.info(f"Experiment ID: {results['experiment_id']}")
    logger.info(f"Total Reps: {results['num_reps']}")
    logger.info(f"Total Time: {results['elapsed_time']:.2f}s")

    agg = results["aggregate"]
    if "failed_reps" in agg and agg["failed_reps"] > 0:
        logger.warning(f"Failed Reps: {agg['failed_reps']}")

    if "home_wins" in agg:
        logger.info(
            f"{home.name} Record: {agg['home_wins']}-{agg['away_wins']}-{agg['ties']} "
            f"({agg['home_win_pct']:.1%})"
        )
        logger.info(f"{home.name} Avg Score: {agg['avg_home_score']:.1f}")
        logger.info(f"{away.name} Avg Score: {agg['avg_away_score']:.1f}")
        logger.info(f"Avg Game Duration: {agg['avg_duration_seconds']:.2f}s")

    # Save results to JSON
    results_file = EXAMPLE_DIR / "simulation_results.json"
    with open(results_file, "w") as f:
        # Include aggregate and per-rep details for easier analysis.
        rep_results: List[Dict[str, Any]] = [
            {
                "rep_number": game["rep_number"],
                "seed": game["seed"],
                "status": game["status"],
                "score": {
                    home.name: game["home_score"],
                    away.name: game["away_score"],
                },
                "winner_id": game["winner_id"],
                "final_quarter": game["final_quarter"],
                "duration_seconds": game["duration_seconds"],
                "total_plays": game["total_plays"],
                "total_drives": game["total_drives"],
            }
            for game in results["games"]
        ]

        output: Dict[str, Any] = {
            "experiment": {
                "id": results["experiment_id"],
                "name": results["experiment_name"],
                "num_reps": results["num_reps"],
                "base_seed": results["base_seed"],
                "elapsed_time": results["elapsed_time"],
            },
            "aggregate": results["aggregate"],
            "reps": rep_results,
        }
        json.dump(output, f, indent=2)
    logger.info(f"\nResults saved to: {results_file}")

    logger.info(f"Database persisted to: {PYLON_DB_PATH}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
