import logging
import sqlite3
import simpy
from pathlib import Path
from typing import Dict

from pylon.domain.team import Team
from pylon.engine.game_engine import GameEngine

from .teams import load_team


TEAM_NAMES = ["Bears", "49ers"]


def load_teams(conn: sqlite3.Connection) -> Dict[str, Team]:
    teams: Dict[str, Team] = {}
    for team_name in TEAM_NAMES:
        team = load_team(conn, team_name)

        if team is None:
            msg = f"Failed to load team: {team_name}"
            logging.error(msg)
            raise ValueError(msg)

        teams[team.name] = team
    return teams


def main():
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    DB_PATH = DATA_DIR / "football.db"
    conn = sqlite3.connect(DB_PATH)

    # logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.DEBUG, filename="pylon.log", filemode="w")

    teams = load_teams(conn)

    home = teams["Bears"]
    away = teams["49ers"]

    ge = GameEngine(simpy.Environment(), home_team=home, away_team=away)
    ge.run()


if __name__ == "__main__":
    main()
