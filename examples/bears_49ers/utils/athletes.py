import sqlite3
import logging
from typing import List, Optional, Dict, Any

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


def get_madden_rating(
    conn: sqlite3.Connection, espn_id: int, iteration_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch Madden rating for an athlete by ESPN ID.

    Args:
        conn: SQLite connection to football.db
        espn_id: ESPN athlete ID
        iteration_id: Madden game version (e.g., "2-week-1"). If None, gets latest.

    Returns:
        Dict with madden_id, overall_rating, position_id, iteration_id, or None if not found.
    """
    if iteration_id:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT mr.madden_id, mr.overall_rating, mr.position_id, mr.iteration_id
            FROM madden_ratings mr
            JOIN madden_players mp ON mr.madden_id = mp.madden_id
            WHERE mp.espn_id = ? AND mr.iteration_id = ?
            """,
            (espn_id, iteration_id),
        )
    else:
        # Get most recent iteration for this athlete
        cur = conn.cursor()
        cur.execute(
            """
            SELECT mr.madden_id, mr.overall_rating, mr.position_id, mr.iteration_id
            FROM madden_ratings mr
            JOIN madden_players mp ON mr.madden_id = mp.madden_id
            WHERE mp.espn_id = ?
            ORDER BY mr.iteration_id DESC
            LIMIT 1
            """,
            (espn_id,),
        )

    row = cur.fetchone()
    if row:
        return {
            "madden_id": row[0],
            "overall_rating": row[1],
            "position_id": row[2],
            "iteration_id": row[3],
        }
    return None


def get_team_madden_ratings(
    conn: sqlite3.Connection, team_id: int, iteration_id: Optional[str] = None
) -> Dict[int, Dict[str, Any]]:
    """
    Fetch Madden ratings for all athletes on a team.

    Args:
        conn: SQLite connection to football.db
        team_id: NFL team ID
        iteration_id: Madden game version. If None, gets latest per athlete.

    Returns:
        Dict mapping ESPN ID to Madden rating data.
    """
    ratings: Dict[int, Dict[str, Any]] = {}
    cur = conn.cursor()

    if iteration_id:
        cur.execute(
            """
            SELECT mp.espn_id, mr.madden_id, mr.overall_rating, mr.position_id, mr.iteration_id
            FROM madden_ratings mr
            JOIN madden_players mp ON mr.madden_id = mp.madden_id
            JOIN rosters r ON mp.espn_id = r.athlete_espn_id
            WHERE r.team_espn_id = ? AND mr.iteration_id = ?
            """,
            (team_id, iteration_id),
        )
    else:
        # Get latest iteration per athlete
        cur.execute(
            """
            SELECT mp.espn_id, mr.madden_id, mr.overall_rating, mr.position_id, mr.iteration_id
            FROM madden_ratings mr
            JOIN madden_players mp ON mr.madden_id = mp.madden_id
            JOIN rosters r ON mp.espn_id = r.athlete_espn_id
            WHERE r.team_espn_id = ? AND (mp.espn_id, mr.iteration_id) IN (
                SELECT mp2.espn_id, mr2.iteration_id
                FROM madden_ratings mr2
                JOIN madden_players mp2 ON mr2.madden_id = mp2.madden_id
                WHERE mp2.espn_id IN (
                    SELECT athlete_espn_id FROM rosters WHERE team_espn_id = ?
                )
                ORDER BY mr2.iteration_id DESC
            )
            """,
            (team_id, team_id),
        )

    for row in cur.fetchall():
        espn_id = row[0]
        ratings[espn_id] = {
            "madden_id": row[1],
            "overall_rating": row[2],
            "position_id": row[3],
            "iteration_id": row[4],
        }

    return ratings


def load_team_athletes_with_madden(
    conn: sqlite3.Connection,
    team_id: int,
    season: int = 2025,
    iteration_id: Optional[str] = None,
) -> List[Athlete]:
    """
    Load team athletes and enrich with Madden ratings.

    Args:
        conn: SQLite connection to football.db
        team_id: Team ID
        season: Season (for rosters table)
        iteration_id: Madden game version. If None, uses latest per athlete.

    Returns:
        List of Athlete objects with madden_rating metadata if available.
    """
    athlete_ids = get_roster_athlete_ids(conn, team_id, season)
    athlete_data = get_athletes(conn, athlete_ids)
    madden_ratings = get_team_madden_ratings(conn, team_id, iteration_id)

    roster: List[Athlete] = []
    for espn_id, first_name, last_name, position in athlete_data:
        pos = cast_pos(position)
        if pos is None:
            logger.warning(
                f"Skipping athlete with unknown position: {first_name} {last_name} ({espn_id})"
            )
            continue

        athlete = Athlete(first_name, last_name, pos, uid=str(espn_id))

        # Attach Madden rating if available
        if espn_id in madden_ratings:
            rating = madden_ratings[espn_id]
            athlete.madden_rating = rating  # type: ignore
            logger.info(
                f"Loaded athlete: {first_name} {last_name} ({espn_id}) - "
                f"Madden OVR: {rating['overall_rating']}"
            )
        else:
            logger.info(
                f"Loaded athlete: {first_name} {last_name} ({espn_id}) - No Madden rating"
            )

        roster.append(athlete)

    return roster
