from typing import Optional
import logging
import sqlite3

from pylon.domain.team import Team
from pylon.domain.athlete import Athlete
from pylon.domain.playbook import Playbook, PlayCall, PlaySideEnum

from .athletes import load_team_athletes
from .plays import load_team_plays


logger = logging.getLogger(__name__)


def load_team(conn: sqlite3.Connection, team_name: str) -> Optional[Team]:
    """
    Load a full Team domain object from the database, including:
    - roster (Athlete objects)
    - offensive and defensive playbooks (PlayCall objects)
    """

    cur = conn.cursor()

    team_name = team_name.strip()
    team_name = team_name.title() if not team_name[0].isdigit() else team_name
    cur.execute(
        "SELECT espn_id, name FROM teams WHERE name = ?",
        (team_name,),
    )
    row = cur.fetchone()

    if row is None:
        logger.error(f"Team with name '{team_name}' not found in database.")
        return None

    team_id: int = row[0]
    name: str = row[1]

    roster: list[Athlete] = load_team_athletes(conn, team_id)
    plays: list[PlayCall] = load_team_plays(conn, team_id)

    off_pb = Playbook()
    def_pb = Playbook()

    for play in plays:
        if play.side == PlaySideEnum.OFFENSE:
            off_pb.add_play(play)
        else:
            # since there are no defensive plays in the DB, this block won't run
            # we will manually add defensive play(s) later
            def_pb.add_play(play)

    team = Team(
        name=name,
        off_playbook=off_pb,
        def_playbook=def_pb,
        roster=roster,
        uid=str(team_id),  # stable identifier
    )
    logger.info(f"Loaded team: {team.name} ({team_id})")

    return team
