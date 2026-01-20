from enum import auto, Enum
import logging
import os
import requests
import sqlite3
import argparse
from typing import Any, Dict
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "football.db")
ESPN_API_BASE = "https://sports.core.api.espn.com"
API_VERSION = "v2"
LEAGUE_PATHS = {
    "NFL": "/sports/football/leagues/nfl",
    "CFB:": "/sports/football/college-football",
    "NBA": "/sports/basketball/leagues/nba",
}


class DatabaseMode(Enum):
    LOAD = auto()
    UPDATE = auto()


def build_url(league: str, endpoint: str = "") -> str:
    """Build a full ESPN API URL for a given league and endpoint."""
    base_path = LEAGUE_PATHS.get(league.upper())
    if not base_path:
        raise ValueError(f"League {league} not supported.")
    return f"{ESPN_API_BASE}/{API_VERSION}{base_path}{endpoint}"


def extract_espn_id(url: str) -> int:
    """
    Extract ESPN ID from a team/athlete URL.
    Example: https://.../teams/1?lang=en&region=us -> 1
    """
    parsed = urlparse(url)
    return int(parsed.path.rstrip("/").split("/")[-1])


def init_db():
    logger.info("Initializing database at %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Teams table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            espn_id INTEGER PRIMARY KEY,
            location TEXT,
            name TEXT,
            abbreviation TEXT
        )
    """
    )

    # Athletes table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS athletes (
            espn_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            weight INTEGER,
            height INTEGER,
            date_of_birth TEXT,
            debut_year INTEGER,
            position TEXT
        )
    """
    )

    # Rosters table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rosters (
            team_espn_id INTEGER,       -- FK to teams.espn_id
            athlete_espn_id INTEGER,    -- FK to athletes.espn_id
            season INTEGER,
            UNIQUE(team_espn_id, athlete_espn_id, season),
            FOREIGN KEY(team_espn_id) REFERENCES teams(espn_id),
            FOREIGN KEY(athlete_espn_id) REFERENCES athletes(espn_id)
        )
    """
    )

    conn.commit()
    return conn


def record_exists(cur: sqlite3.Cursor, table: str, espn_id: int) -> bool:
    cur.execute(f"SELECT 1 FROM {table} WHERE espn_id = ?", (espn_id,))
    return cur.fetchone() is not None


def iter_page(url: str, limit: int = 50):
    page = 1
    while True:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query.update({"page": [str(page)], "limit": [str(limit)], "active": ["true"]})
        new_query = urlencode(query, doseq=True)
        paged_url = urlunparse(parsed._replace(query=new_query))

        logger.debug("Fetching page %s from %s", page, paged_url)
        res = requests.get(paged_url)
        res.raise_for_status()
        data = res.json()

        for item in data.get("items", []):
            yield item.get("$ref")

        page_count = data.get("pageCount", 1)
        if page >= page_count:
            break
        page += 1


def fetch_nfl_teams(conn: sqlite3.Connection, mode: DatabaseMode = DatabaseMode.UPDATE):
    teams_url = build_url("NFL", "/teams")
    cur = conn.cursor()

    for team_url in iter_page(teams_url):
        espn_id = extract_espn_id(team_url)

        if mode == DatabaseMode.LOAD and record_exists(cur, "teams", espn_id):
            logger.info("Skipping team %s (already loaded)", espn_id)
            continue

        res = requests.get(team_url)
        res.raise_for_status()
        team_data = res.json()
        load_team_into_db(cur, team_data)

    conn.commit()
    logger.info("Finished %s mode for NFL teams", mode)


def fetch_nfl_athletes(
    conn: sqlite3.Connection, mode: DatabaseMode = DatabaseMode.UPDATE
):
    athletes_url = build_url("NFL", "/athletes")
    cur = conn.cursor()

    for athlete_url in iter_page(athletes_url, limit=1000):
        espn_id = extract_espn_id(athlete_url)

        if mode == DatabaseMode.LOAD and record_exists(cur, "athletes", espn_id):
            logger.info("Skipping athlete %s (already loaded)", espn_id)
            continue

        res = requests.get(athlete_url)
        res.raise_for_status()
        athlete_data = res.json()
        load_athlete_into_db(cur, athlete_data)
        conn.commit()

    logger.info("Finished %s mode for NFL athletes", mode)


def fetch_nfl_team_roster(
    conn: sqlite3.Connection,
    team_espn_id: int,
    season: int,
    mode: DatabaseMode = DatabaseMode.UPDATE,
):
    roster_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{season}/teams/{team_espn_id}/athletes"
    cur = conn.cursor()

    # Get internal team_id
    cur.execute("SELECT espn_id FROM teams WHERE espn_id = ?", (team_espn_id,))
    row = cur.fetchone()
    if not row:
        logger.warning("Team %s not found in DB, skipping roster", team_espn_id)
        return

    for athlete_url in iter_page(roster_url, limit=100):
        athlete_espn_id = extract_espn_id(athlete_url)

        # Get internal athlete_id
        cur.execute(
            "SELECT espn_id FROM athletes WHERE espn_id = ?", (athlete_espn_id,)
        )
        athlete_row = cur.fetchone()
        if not athlete_row:
            if mode == DatabaseMode.LOAD:
                logger.info("Skipping athlete %s (not yet loaded)", athlete_espn_id)
                continue
            # In update mode, fetch athlete details and insert
            res = requests.get(athlete_url)
            res.raise_for_status()
            athlete_data = res.json()
            load_athlete_into_db(cur, athlete_data)
            cur.execute(
                "SELECT espn_id FROM athletes WHERE espn_id = ?", (athlete_espn_id,)
            )
            athlete_row = cur.fetchone()

        data = {
            "team_espn_id": team_espn_id,
            "athlete_espn_id": athlete_espn_id,
            "season": season,
        }

        load_roster_into_db(cur, data)
        logger.info(
            "Added athlete %s to team %s roster for season %s",
            athlete_espn_id,
            team_espn_id,
            season,
        )

    conn.commit()


def load_team_into_db(cur: sqlite3.Cursor, team_data: Dict[str, Any]):
    espn_id = team_data.get("id")
    location = team_data.get("location")
    name = team_data.get("name")
    abbreviation = team_data.get("abbreviation")

    cur.execute(
        """
        INSERT OR REPLACE INTO teams (espn_id, location, name, abbreviation)
        VALUES (?, ?, ?, ?)
    """,
        (espn_id, location, name, abbreviation),
    )
    logger.info("Inserted/Updated team: %s %s (%s)", location, name, abbreviation)


def load_athlete_into_db(cur: sqlite3.Cursor, athlete_data: Dict[str, Any]):
    espn_id = athlete_data.get("id")
    first_name = athlete_data.get("firstName")
    last_name = athlete_data.get("lastName")
    weight = athlete_data.get("weight")
    height = athlete_data.get("height")
    date_of_birth = athlete_data.get("dateOfBirth")
    debut_year = athlete_data.get("debutYear")
    position = athlete_data.get("position", {}).get("abbreviation", None)

    cur.execute(
        """
        INSERT OR REPLACE INTO athletes (
            espn_id, first_name, last_name, weight, height, date_of_birth, debut_year, position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            espn_id,
            first_name,
            last_name,
            weight,
            height,
            date_of_birth,
            debut_year,
            position,
        ),
    )
    logger.info(
        "Inserted/Updated athlete: %s %s (ID %s)", first_name, last_name, espn_id
    )


def load_roster_into_db(cur: sqlite3.Cursor, roster_data: Dict[str, Any]):
    team_id = roster_data.get("team_espn_id")
    athlete_id = roster_data.get("athlete_espn_id")
    season = roster_data.get("season")

    cur.execute(
        """
        INSERT OR REPLACE INTO rosters (team_espn_id, athlete_espn_id, season)
        VALUES (?, ?, ?)
        """,
        (team_id, athlete_id, season),
    )
    logger.info(
        "Inserted/Updated roster entry: Team %s Athlete %s Season %s",
        team_id,
        athlete_id,
        season,
    )


def fetch_all_rosters(
    conn: sqlite3.Connection, season: int, mode: DatabaseMode = DatabaseMode.UPDATE
):
    cur = conn.cursor()
    cur.execute("SELECT espn_id FROM teams")
    teams = [row[0] for row in cur.fetchall()]

    for team_espn_id in teams:
        logger.info("Fetching roster for team %s (season %s)", team_espn_id, season)
        fetch_nfl_team_roster(conn, team_espn_id, season, mode=mode)
    logger.info("Finished %s mode for all rosters (season %s)", mode, season)


def main():
    parser = argparse.ArgumentParser(
        description="Pull NFL teams, athletes, and rosters into SQLite DB"
    )
    parser.add_argument(
        "--mode",
        choices=["load", "update"],
        default=DatabaseMode.UPDATE,
        help="Mode: 'load' skips already existing records, 'update' refreshes all",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2025,
        help="Season year to fetch rosters for (default: 2025)",
    )
    args = parser.parse_args()

    logger.info("Starting NFL data pull in %s mode", args.mode)
    conn = init_db()
    # mode = DatabaseMode.LOAD if args.mode.lower() == "load" else DatabaseMode.UPDATE
    fetch_nfl_teams(conn, mode=args.mode)
    fetch_nfl_athletes(conn, mode=args.mode)
    fetch_all_rosters(conn, season=args.season, mode=args.mode)
    conn.close()
    logger.info("Data pull complete")


if __name__ == "__main__":
    main()
