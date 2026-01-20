import sqlite3
import logging
from typing import List, Optional

from pylon.domain.athlete import Athlete, AthletePositionEnum


logger = logging.getLogger(__name__)


def get_roster_athlete_ids(conn: sqlite3.Connection, team_id: int, season: int):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT athlete_espn_id FROM rosters
        WHERE team_espn_id = ? AND season = ?
    """,
        (team_id, season),
    )
    return [row[0] for row in cur.fetchall()]


def get_athletes(conn: sqlite3.Connection, athlete_ids: list[int]):
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT espn_id, first_name, last_name, position FROM athletes
        WHERE espn_id IN ({",".join(["?"] * len(athlete_ids))})
    """,
        athlete_ids,
    )
    return cur.fetchall()


def cast_pos(pos_abbv: str) -> Optional[AthletePositionEnum]:
    mapping = {
        "QB": AthletePositionEnum.QB,
        "RB": AthletePositionEnum.RB,
        "FB": AthletePositionEnum.RB,
        "WR": AthletePositionEnum.WR,
        "TE": AthletePositionEnum.TE,
        "C": AthletePositionEnum.C,
        "G": AthletePositionEnum.G,
        "OL": AthletePositionEnum.G,
        "OT": AthletePositionEnum.T,
        "DT": AthletePositionEnum.DT,
        "NT": AthletePositionEnum.DT,
        "DL": AthletePositionEnum.DT,
        "DE": AthletePositionEnum.EDGE,
        "LB": AthletePositionEnum.MLB,
        "S": AthletePositionEnum.SS,
        "CB": AthletePositionEnum.CB,
        "DB": AthletePositionEnum.CB,
        "LS": AthletePositionEnum.LS,
        "K": AthletePositionEnum.K,
        "P": AthletePositionEnum.P,
        "PK": AthletePositionEnum.K,
        # Add other position mappings as needed
    }
    if pos_abbv == "-":
        return None
    pos = mapping.get(pos_abbv, None)
    if pos is None:
        msg = f"Unknown position abbreviation: {pos_abbv}"
        logger.error(msg)
        raise ValueError(msg)

    return pos


def load_team_athletes(
    conn: sqlite3.Connection, team_id: int, season: int = 2025
) -> List[Athlete]:
    athlete_ids = get_roster_athlete_ids(conn, team_id, season)
    athlete_data = get_athletes(conn, athlete_ids)

    roster: List[Athlete] = []
    for espn_id, first_name, last_name, position in athlete_data:
        pos = cast_pos(position)
        if pos is None:
            logger.warning(
                f"Skipping athlete with unknown position: {first_name} {last_name} ({espn_id})"
            )
            continue

        athlete = Athlete(first_name, last_name, pos, uid=str(espn_id))
        roster.append(athlete)
        logger.info(f"Loaded athlete: {first_name} {last_name} ({espn_id})")

    return roster
