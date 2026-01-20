from typing import Counter, Dict, List, Optional, Tuple
import logging
import sqlite3

from pylon.domain.playbook import (
    PlayCall,
    PlayTypeEnum,
    PlaySideEnum,
    Formation,
    PersonnelPackage,
)
from pylon.domain.athlete import AthletePositionEnum, PositionTree, POSITION_TREE


logger = logging.getLogger(__name__)


def expand_group(tree: PositionTree, count: Optional[int]) -> List[AthletePositionEnum]:
    leaves = tree.all_positions()
    result: List[AthletePositionEnum] = []

    if count is None:
        return result

    i = 0
    while len(result) < count:
        result.append(leaves[i % len(leaves)])
        i += 1
    return result


def load_formations(
    conn: sqlite3.Connection,
) -> Tuple[Dict[int, Formation], Dict[int, Formation]]:
    cur = conn.cursor()

    # -------------------------
    # OFFENSE
    # -------------------------
    cur.execute("""
        SELECT id, name, parent_id, qb, rb, te, wr, t, g, c
        FROM off_formations
    """)
    off_rows = cur.fetchall()

    off_formations: Dict[int, Formation] = {}
    def_formations: Dict[int, Formation] = {}

    # Build offensive formations
    for row in off_rows:
        fid, name, parent_id, qb, rb, te, wr, t, g, c = row

        off_counts: Dict[AthletePositionEnum, int] = {}
        if qb is not None:
            off_counts[AthletePositionEnum.QB] = qb
        if rb is not None:
            off_counts[AthletePositionEnum.RB] = rb
        if te is not None:
            off_counts[AthletePositionEnum.TE] = te
        if wr is not None:
            off_counts[AthletePositionEnum.WR] = wr
        if t is not None:
            off_counts[AthletePositionEnum.T] = t
        if g is not None:
            off_counts[AthletePositionEnum.G] = g
        if c is not None:
            off_counts[AthletePositionEnum.C] = c

        off_formations[fid] = Formation(
            name=name,
            position_counts=off_counts,
            tags=[],
            parent=None,
            uid=str(fid),
        )

    # Assign offensive parents
    for fid, name, parent_id, *_ in off_rows:
        if parent_id is not None:
            off_formations[fid].parent = off_formations[parent_id]
            off_formations[parent_id].subformations.add(off_formations[fid])

    # -------------------------
    # DEFENSE
    # -------------------------
    cur.execute("""
        SELECT id, name, parent_id, dl, lb, db
        FROM def_formations
    """)
    def_rows = cur.fetchall()

    for row in def_rows:
        fid, name, parent_id, dl, lb, db = row

        dline_positions = expand_group(
            POSITION_TREE.children[AthletePositionEnum.DEFENSE].children[
                AthletePositionEnum.DLINE
            ],
            dl,
        )

        lb_positions = expand_group(
            POSITION_TREE.children[AthletePositionEnum.DEFENSE].children[
                AthletePositionEnum.LB
            ],
            lb,
        )

        db_positions = expand_group(
            POSITION_TREE.children[AthletePositionEnum.DEFENSE].children[
                AthletePositionEnum.DB
            ],
            db,
        )

        all_positions = dline_positions + lb_positions + db_positions
        def_counts = Counter(all_positions)

        def_formations[fid] = Formation(
            name=name,
            position_counts=def_counts,
            tags=[],
            parent=None,
            uid=str(fid),
        )

    # Assign defensive parents
    for fid, name, parent_id, *_ in def_rows:
        if parent_id is not None:
            def_formations[fid].parent = def_formations[parent_id]
            def_formations[parent_id].subformations.add(def_formations[fid])

    return off_formations, def_formations


def load_personnel_packages(conn: sqlite3.Connection) -> Dict[str, PersonnelPackage]:
    cur = conn.cursor()
    packages: Dict[str, PersonnelPackage] = {}

    # -------------------------
    # OFFENSE
    # -------------------------
    cur.execute("SELECT name, rb, te, wr FROM off_personnel_packages")
    for name, rb, te, wr in cur.fetchall():
        packages[name] = PersonnelPackage(
            name=name,
            counts={
                AthletePositionEnum.RB: rb,
                AthletePositionEnum.TE: te,
                AthletePositionEnum.WR: wr,
            },
            uid=name,
        )

    # -------------------------
    # DEFENSE
    # -------------------------
    cur.execute("SELECT name, dl, lb FROM def_personnel_packages")
    for name, dl, lb in cur.fetchall():
        # Compute DB count automatically
        db = 11 - (dl + lb)

        # Expand DL/LB/DB using the PositionTree
        dline_positions = expand_group(
            POSITION_TREE.children[AthletePositionEnum.DEFENSE].children[
                AthletePositionEnum.DLINE
            ],
            dl,
        )

        lb_positions = expand_group(
            POSITION_TREE.children[AthletePositionEnum.DEFENSE].children[
                AthletePositionEnum.LB
            ],
            lb,
        )

        db_positions = expand_group(
            POSITION_TREE.children[AthletePositionEnum.DEFENSE].children[
                AthletePositionEnum.DB
            ],
            db,
        )

        # Build final counts
        all_positions = dline_positions + lb_positions + db_positions
        counts = Counter(all_positions)

        packages[name] = PersonnelPackage(
            name=name,
            counts=counts,
            uid=name,
        )

    return packages


def load_plays_for_team(
    conn: sqlite3.Connection,
    team_espn_id: int,
    off_formations: Dict[int, Formation],
    def_formations: Dict[int, Formation],
    personnel: Dict[str, PersonnelPackage],
) -> List[PlayCall]:
    cur = conn.cursor()
    plays: List[PlayCall] = []

    # --- OFFENSE ---
    cur.execute(
        """
        SELECT id, name, play_type, formation_id, personnel_name, side
        FROM off_plays
        WHERE team_id = ?
    """,
        (team_espn_id,),
    )

    for pid, name, play_type, formation_id, personnel_name, side in cur.fetchall():
        cur.execute("SELECT tag FROM off_play_tags WHERE play_id = ?", (pid,))
        tags = [row[0] for row in cur.fetchall()]

        plays.append(
            PlayCall(
                name=name,
                play_type=PlayTypeEnum[play_type],
                formation=off_formations[formation_id],
                personnel_package=personnel[personnel_name],
                side=PlaySideEnum[side],
                tags=tags,
                uid=str(pid),
            )
        )

    # --- DEFENSE ---
    cur.execute(
        """
        SELECT id, name, play_type, formation_id, personnel_name, side
        FROM def_plays
        WHERE team_id = ?
    """,
        (team_espn_id,),
    )

    for pid, name, play_type, formation_id, personnel_name, side in cur.fetchall():
        cur.execute("SELECT tag FROM def_play_tags WHERE play_id = ?", (pid,))
        tags = [row[0] for row in cur.fetchall()]

        plays.append(
            PlayCall(
                name=name,
                play_type=PlayTypeEnum.DEFENSIVE_PLAY,
                formation=def_formations[formation_id],
                personnel_package=personnel[personnel_name],
                side=PlaySideEnum.DEFENSE,
                tags=tags,
                uid=str(pid),
            )
        )

    return plays


def load_team_plays(conn: sqlite3.Connection, team_espn_id: int) -> List[PlayCall]:
    off_formations, def_formations = load_formations(conn)
    personnel = load_personnel_packages(conn)
    return load_plays_for_team(
        conn, team_espn_id, off_formations, def_formations, personnel
    )
