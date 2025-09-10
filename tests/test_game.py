import csv
from typing import List

from pylon.engine.team import Team


TEAM_FILE = "./data/teams.csv"


def load_teams(team_path: str = TEAM_FILE) -> List[Team]:
    teams: List[Team] = []
    with open(team_path, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            team_id = row.get("id")
            location = row.get("location", "").strip()
            name = row.get("name", "").strip()
            
            full_name = f"{location} {name}".strip()
            team = Team(uid=team_id, name=full_name, roster=[])
            teams.append(team)
    return teams


def main():
    teams = load_teams()
    for t in teams:
        print(t)


if __name__ == "__main__":
    main()