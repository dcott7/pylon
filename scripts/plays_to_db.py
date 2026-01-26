import json
import sqlite3
from typing import Dict, Set, Tuple

# ---------------------------------------------------------
# Load JSON
# ---------------------------------------------------------

with open("./data/plays.json", "r") as f:
    plays_data = json.load(f)

def_formations_seen: Set[Tuple[str, str]] = set()
off_formations_seen: Set[Tuple[str, str]] = set()
team_plays: Dict[str, Set[str]] = {}

# ---------------------------------------------------------
# Personnel mapping
# ---------------------------------------------------------


def cast_off_to_personnel(required_pos: Dict[str, int]) -> str:
    personnel_map = {
        frozenset({("RB", 2), ("TE", 3)}): "twenty_three_personnel",
        frozenset({("RB", 2), ("TE", 2)}): "twenty_two_personnel",
        frozenset({("RB", 2), ("TE", 1)}): "twenty_one_personnel",
        frozenset({("RB", 2), ("TE", 0)}): "twenty_personnel",
        frozenset({("RB", 1), ("TE", 3)}): "thirteen_personnel",
        frozenset({("RB", 1), ("TE", 2)}): "twelve_personnel",
        frozenset({("RB", 1), ("TE", 1)}): "eleven_personnel",
        frozenset({("RB", 1), ("TE", 0)}): "ten_personnel",
        frozenset({("RB", 0), ("TE", 2)}): "two_personnel",
        frozenset({("RB", 0), ("TE", 1)}): "one_personnel",
        frozenset({("RB", 0), ("TE", 0)}): "zero_personnel",
    }
    key = frozenset(required_pos.items())
    p = personnel_map.get(key, None)
    if p is None:
        raise ValueError(f"Unknown Personnel for required positions: {required_pos}")
    return p


def cast_def_to_personnel(required_pos: Dict[str, int]) -> str:
    DL = required_pos.get("DT", 0) + required_pos.get("DE", 0)
    LB = required_pos.get("MLB", 0) + required_pos.get("OLB", 0)
    key = (DL, LB)
    personnel_map = {
        (2, 4): "two_four_personnel",
        (3, 1): "quarter_personnel",
        (3, 2): "dime_personnel",
        (3, 3): "three_three_personnel",
        (3, 4): "three_four_personnel",
        (4, 2): "nickel_personnel",
        (4, 3): "four_three_personnel",
        (5, 2): "five_two_personnel",
        (5, 3): "five_three_personnel",
        (6, 2): "six_two_personnel",
    }
    p = personnel_map.get(key, None)
    if p is None:
        raise ValueError(f"Unknown Personnel for required positions: {required_pos}")
    return p


def lookup_team_id(cur: sqlite3.Cursor, raw_name: str) -> int:
    if not raw_name[0].isdigit():
        raw_name = raw_name.title()
    cur.execute("SELECT espn_id FROM teams WHERE name = ?", (raw_name,))
    row = cur.fetchone()
    if row:
        return row[0]

    raise ValueError(f"Team '{raw_name}' not found in teams table")


# ---------------------------------------------------------
# Database setup
# ---------------------------------------------------------

conn = sqlite3.connect("data/football.db")
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS def_formations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    dl INTEGER,
    lb INTEGER,
    db INTEGER,
    FOREIGN KEY(parent_id) REFERENCES def_formations(id),
    UNIQUE(parent_id, name)
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS def_personnel_packages (
    name TEXT PRIMARY KEY,
    dl INTEGER,
    lb INTEGER
)
"""
)


cur.execute(
    """
CREATE TABLE IF NOT EXISTS def_plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    play_type TEXT,
    formation_id INTEGER,
    personnel_name TEXT,
    side TEXT,
    team_id INTEGER,
    FOREIGN KEY(formation_id) REFERENCES def_formations(id),
    FOREIGN KEY(team_id) REFERENCES teams(espn_id)
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS def_play_tags (
    play_id INTEGER,
    tag TEXT,
    FOREIGN KEY(play_id) REFERENCES def_plays(id),
    UNIQUE(play_id, tag)
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS off_formations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    qb INTEGER,
    rb INTEGER,
    te INTEGER,
    wr INTEGER,
    t INTEGER,
    g INTEGER,
    c INTEGER,
    FOREIGN KEY(parent_id) REFERENCES off_formations(id),
    UNIQUE(parent_id, name)
)
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS off_personnel_packages (
    name TEXT PRIMARY KEY,
    rb INTEGER,
    te INTEGER,
    wr INTEGER
)
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS off_plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    play_type TEXT,
    formation_id INTEGER,
    personnel_name TEXT,
    side TEXT,
    team_id INTEGER,
    FOREIGN KEY(formation_id) REFERENCES off_formations(id),
    FOREIGN KEY(personnel_name) REFERENCES off_personnel_packages(name),
    FOREIGN KEY(team_id) REFERENCES teams(espn_id)
)
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS off_play_tags (
    play_id INTEGER,
    tag TEXT,
    FOREIGN KEY(play_id) REFERENCES off_plays(id),
    UNIQUE(play_id, tag)
)
"""
)

conn.commit()

# ---------------------------------------------------------
# Insert personnel packages (static)
# ---------------------------------------------------------

DEF_PERSONNEL_PACKAGES = [
    # name, dl, lb
    ("two_four_personnel", 2, 4),
    ("quarter_personnel", 3, 1),
    ("dime_personnel", 3, 2),
    ("three_three_personnel", 3, 3),
    ("three_four_personnel", 3, 4),
    ("nickel_personnel", 4, 2),
    ("four_three_personnel", 4, 3),
    ("five_two_personnel", 5, 2),
    ("five_three_personnel", 5, 3),
    ("six_two_personnel", 6, 2),
]

for name, dl, lb in DEF_PERSONNEL_PACKAGES:
    cur.execute(
        """
        INSERT OR IGNORE INTO def_personnel_packages (name, dl, lb)
        VALUES (?, ?, ?)
    """,
        (name, dl, lb),
    )

OFF_PERSONNEL_PACKAGES = [
    # name, rb, te, wr
    ("twenty_three_personnel", 2, 3, 0),
    ("twenty_two_personnel", 2, 2, 1),
    ("twenty_one_personnel", 2, 1, 2),
    ("twenty_personnel", 2, 0, 3),
    ("thirteen_personnel", 1, 3, 1),
    ("twelve_personnel", 1, 2, 2),
    ("eleven_personnel", 1, 1, 3),
    ("ten_personnel", 1, 0, 4),
    ("two_personnel", 0, 2, 3),
    ("one_personnel", 0, 1, 4),
    ("zero_personnel", 0, 0, 5),
]

for name, rb, te, wr in OFF_PERSONNEL_PACKAGES:
    cur.execute(
        """
        INSERT OR IGNORE INTO off_personnel_packages (name, rb, te, wr)
        VALUES (?, ?, ?, ?)
    """,
        (name, rb, te, wr),
    )

conn.commit()

# ---------------------------------------------------------
# Phase 1: Insert all formations (parent_id NULL)
# ---------------------------------------------------------

def_formation_ids: Dict[Tuple[str, str], int] = {}

for team_data in plays_data:
    if team_data["side"] != "defense":
        continue

    parent = team_data["formation"].replace("-", "_").lower()
    sub = team_data["subformation"].replace("-", "_").lower()

    if (parent, sub) in def_formations_seen:
        continue

    def_formations_seen.add((parent, sub))

    required = team_data["required_pos"]
    DL = required.get("DT", 0) + required.get("DE", 0)
    LB = required.get("MLB", 0) + required.get("OLB", 0)
    DB = required.get("CB", 0) + required.get("FS", 0) + required.get("SS", 0)

    cur.execute(
        """
        INSERT OR IGNORE INTO def_formations
        (name, parent_id, dl, lb, db)
        VALUES (?, NULL, NULL, NULL, NULL)
    """,
        (parent,),
    )

    cur.execute(
        """
        INSERT INTO def_formations
        (name, parent_id, dl, lb, db)
        VALUES (?, NULL, ?, ?, ?)
    """,
        (sub, DL, LB, DB),
    )

    assert cur.lastrowid is not None
    def_formation_ids[(parent, sub)] = cur.lastrowid


off_formation_ids: Dict[Tuple[str, str], int] = {}

for team_data in plays_data:
    if team_data["side"] != "offense":
        continue

    parent = team_data["formation"].replace("-", "_").lower()
    sub = team_data["subformation"].replace("-", "_").lower()

    if (parent, sub) in off_formations_seen:
        continue

    off_formations_seen.add((parent, sub))

    required = team_data["required_pos"]
    rb = required.get("RB", 0)
    te = required.get("TE", 0)
    wr = 5 - (rb + te)

    # Insert parent formation (if not already)
    cur.execute(
        """
        INSERT OR IGNORE INTO off_formations
        (name, parent_id, qb, rb, te, wr, t, g, c)
        VALUES (?, NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL)
    """,
        (parent,),
    )

    # Insert subformation
    cur.execute(
        """
        INSERT INTO off_formations
        (name, parent_id, qb, rb, te, wr, t, g, c)
        VALUES (?, NULL, 1, ?, ?, ?, 2, 2, 1)
    """,
        (sub, rb, te, wr),
    )

    assert cur.lastrowid is not None
    off_formation_ids[(parent, sub)] = cur.lastrowid

conn.commit()

# ---------------------------------------------------------
# Phase 2: Update parent_id for subformations
# ---------------------------------------------------------

for (parent, sub), sub_id in def_formation_ids.items():
    cur.execute("SELECT id FROM def_formations WHERE name = ?", (parent,))
    parent_id = cur.fetchone()[0]

    cur.execute(
        """
        UPDATE def_formations
        SET parent_id = ?
        WHERE id = ?
    """,
        (parent_id, sub_id),
    )

conn.commit()

for (parent, sub), sub_id in off_formation_ids.items():
    cur.execute("SELECT id FROM off_formations WHERE name = ?", (parent,))
    parent_id = cur.fetchone()[0]

    cur.execute(
        """
        UPDATE off_formations
        SET parent_id = ?
        WHERE id = ?
    """,
        (parent_id, sub_id),
    )

conn.commit()

# ---------------------------------------------------------
# Insert plays + tags
# ---------------------------------------------------------

for team_data in plays_data:
    if team_data["side"] != "defense":
        continue

    team_id = lookup_team_id(cur, team_data["team"])

    parent = team_data["formation"].replace("-", "_").lower()
    sub = team_data["subformation"].replace("-", "_").lower()
    formation_id = def_formation_ids[(parent, sub)]

    for play in team_data["plays"]:
        play_name = play["name"].replace("-", "_").replace(" ", "_").lower()
        personnel = cast_def_to_personnel(team_data["required_pos"])

        cur.execute(
            """
            INSERT INTO def_plays
            (name, play_type, formation_id, personnel_name, side, team_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                play_name,
                "DEFENSIVE_PLAY",
                formation_id,
                personnel,
                "DEFENSE",
                team_id,
            ),
        )

        play_id = cur.lastrowid

        for part in play_name.split("_"):
            cur.execute("SELECT DISTINCT tag FROM def_play_tags WHERE tag = ?", (part,))
            if cur.fetchone():
                continue

            cur.execute(
                """
                INSERT INTO def_play_tags (play_id, tag)
                VALUES (?, ?)
            """,
                (play_id, part),
            )


for team_data in plays_data:
    if team_data["side"] != "offense":
        continue

    raw_team_name = team_data["team"]
    team_id = lookup_team_id(cur, raw_team_name)

    parent = team_data["formation"].replace("-", "_").lower()
    sub = team_data["subformation"].replace("-", "_").lower()
    formation_id = off_formation_ids[(parent, sub)]

    for play in team_data["plays"]:
        play_name = play["name"].replace("-", "_").replace(" ", "_").lower()
        personnel = cast_off_to_personnel(team_data["required_pos"])
        side = team_data["side"].upper()
        play_type = play["type"].upper()

        cur.execute(
            """
            INSERT INTO off_plays
            (name, play_type, formation_id, personnel_name, side, team_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (play_name, play_type, formation_id, personnel, side, team_id),
        )

        play_id = cur.lastrowid

        for part in play_name.split("_"):
            cur.execute("SELECT DISTINCT tag FROM off_play_tags WHERE tag = ?", (part,))
            if cur.fetchone():
                continue

            cur.execute(
                """
                INSERT INTO off_play_tags (play_id, tag)
                VALUES (?, ?)
                """,
                (play_id, part),
            )


conn.commit()
conn.close()
