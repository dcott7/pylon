import csv
from typing import Dict, List
from pathlib import Path

from pylon.entities.team import Team
from pylon.entities.athlete import Athlete, AthletePositionEnum


TEAM_FILE = Path("./data/teams.csv")
ROSTER_FILE = Path("./data/roster.csv")
ATHLETE_POS_FILE = Path("./data/athlete_pos.csv")


def espn_pos_cast(espn_pos_abbrev: str):
    mapping = {
        "LB": "MLB",
        "OG": "G",
        "DL": "DT",
        "OL": "T",
        "DB": "CB",
        "PK": "K",
        "NT": "DT",
        "S": "SS",
        "FB": "RB",
        "ATH": "WR",
        "OT": "T"
    }
    return mapping.get(espn_pos_abbrev, espn_pos_abbrev or None)


def load_positions() -> Dict[str, AthletePositionEnum]:
    """
    Load athlete_id -> AthletePositionEnum from athlete_pos.csv
    """
    athlete_positions: Dict[str, AthletePositionEnum] = {}
    with open(ATHLETE_POS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pos_abbr = row["pos_type_abbreviation"].strip()
            athlete_id = row["athlete_id"].strip()
            
            if pos_abbr in ["-"]:
                continue

            pos_abbr = espn_pos_cast(pos_abbr)

            try:
                athlete_positions[athlete_id] = AthletePositionEnum[pos_abbr]
            except KeyError:
                continue

    return athlete_positions


def load_teams() -> List[Team]:
    """
    Load teams and rosters from CSV files.
    Returns a list of Team objects with populated Athlete rosters.
    """
    teams: Dict[str, Team] = {}
    athlete_positions = load_positions()

    with open(TEAM_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team_id = row["id"].strip()
            name = f"{row['location']} {row['name']}"
            teams[team_id] = Team(uid=team_id, name=name)

    with open(ROSTER_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            athlete_id = row["athlete_id"].strip()
            pos = athlete_positions.get(athlete_id, None)

            athlete = Athlete(
                uid=athlete_id,
                first_name=row["athlete_first_name"].strip(),
                last_name=row["athlete_last_name"].strip(),
                position=pos,
            )

            team_id = row["team_id"].strip()
            if team_id in teams:
                    teams[team_id].add_player(athlete)

    return list(teams.values())


def main():
    teams = load_teams()
    for t in teams:
        print(t)


if __name__ == "__main__":
    main()