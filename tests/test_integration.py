"""Integration tests for full game simulation workflow."""

import json
import pytest
from typing import Generator
from pathlib import Path
from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team
from pylon.domain.playbook import (
    PlayCall,
    PlayTypeEnum,
    PlaySideEnum,
    Formation,
    PersonnelPackage,
)
from pylon.domain.rules.nfl import NFLRules
from pylon.simulation_runner import PylonSimulationRunner
from pylon.db.database import DatabaseManager
from pylon.db.schema import Game as OrmGame, Drive as OrmDrive, Play as OrmPlay
from pylon.output import OutputMode, SimulationOutputPayload


def create_test_team(uid: str, name: str) -> Team:
    """Create a test team with full roster and playbook."""
    team = Team(uid=uid, name=name)

    # Offense
    positions: list[tuple[AthletePositionEnum, int]] = [
        (AthletePositionEnum.QB, 2),
        (AthletePositionEnum.RB, 3),
        (AthletePositionEnum.WR, 5),
        (AthletePositionEnum.TE, 2),
        (AthletePositionEnum.LT, 2),
        (AthletePositionEnum.LG, 2),
        (AthletePositionEnum.C, 2),
        (AthletePositionEnum.RG, 2),
        (AthletePositionEnum.RT, 2),
        # Defense
        (AthletePositionEnum.EDGE, 3),
        (AthletePositionEnum.DT, 3),
        (AthletePositionEnum.LB, 4),
        (AthletePositionEnum.CB, 4),
        (AthletePositionEnum.FS, 2),
        (AthletePositionEnum.SS, 2),
        # Special teams
        (AthletePositionEnum.K, 1),
        (AthletePositionEnum.P, 1),
    ]

    athlete_count = 0
    for position, count in positions:
        for i in range(count):
            athlete = Athlete(
                uid=f"{uid}-{position.value}-{i}",
                first_name=f"{position.value}{i}",
                last_name="Player",
                position=position,
            )
            team.add_athlete(athlete)
            athlete_count += 1

    # Add basic plays
    offensive_plays: list[tuple[str, PlayTypeEnum]] = [
        ("Inside Zone", PlayTypeEnum.RUN),
        ("Outside Zone", PlayTypeEnum.RUN),
        ("Power", PlayTypeEnum.RUN),
        ("Slant", PlayTypeEnum.PASS),
        ("Curl", PlayTypeEnum.PASS),
        ("Go Route", PlayTypeEnum.PASS),
        ("Screen", PlayTypeEnum.PASS),
    ]

    formation = Formation(
        name="Base",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 2,
            AthletePositionEnum.TE: 1,
            AthletePositionEnum.LT: 1,
            AthletePositionEnum.LG: 1,
            AthletePositionEnum.C: 1,
            AthletePositionEnum.RG: 1,
            AthletePositionEnum.RT: 1,
        },
    )

    subformation = Formation(
        name="Base Tight",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 3,
            AthletePositionEnum.TE: 1,
            AthletePositionEnum.LT: 1,
            AthletePositionEnum.LG: 1,
            AthletePositionEnum.C: 1,
            AthletePositionEnum.RG: 1,
            AthletePositionEnum.RT: 1,
        },
        parent=formation,
    )

    personnel = PersonnelPackage(
        name="11 Personnel",
        counts={
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 3,
            AthletePositionEnum.TE: 1,
        },
    )

    def_parent_formation = Formation(
        name="Nickel",
        position_counts={
            AthletePositionEnum.EDGE: 1,
            AthletePositionEnum.DT: 1,
            AthletePositionEnum.LB: 2,
            AthletePositionEnum.CB: 2,
        },
    )
    def_subformation = Formation(
        name="Nickel 4-2-5",
        position_counts={
            AthletePositionEnum.EDGE: 2,
            AthletePositionEnum.DT: 2,
            AthletePositionEnum.LB: 3,
            AthletePositionEnum.CB: 2,
            AthletePositionEnum.FS: 1,
            AthletePositionEnum.SS: 1,
        },
        parent=def_parent_formation,
    )
    def_personnel = PersonnelPackage(
        name="Nickel",
        counts={
            AthletePositionEnum.EDGE: 2,
            AthletePositionEnum.DT: 2,
            AthletePositionEnum.LB: 3,
            AthletePositionEnum.CB: 2,
            AthletePositionEnum.FS: 1,
            AthletePositionEnum.SS: 1,
        },
    )

    for play_name, play_type in offensive_plays:
        play = PlayCall(
            name=play_name,
            play_type=play_type,
            formation=subformation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            uid=f"{uid}-{play_name.replace(' ', '-').lower()}",
        )
        team.add_play_template(play)

    def_play = PlayCall(
        name="Base Defense",
        play_type=PlayTypeEnum.DEFENSIVE_PLAY,
        formation=def_subformation,
        personnel_package=def_personnel,
        side=PlaySideEnum.DEFENSE,
        uid=f"{uid}-def-1",
    )
    kickoff_play = PlayCall(
        name="Basic Kickoff",
        play_type=PlayTypeEnum.KICKOFF,
        formation=subformation,
        personnel_package=personnel,
        side=PlaySideEnum.OFFENSE,
        uid=f"{uid}-kickoff-1",
    )
    kickoff_return_play = PlayCall(
        name="Basic Kickoff Return",
        play_type=PlayTypeEnum.KICKOFF_RETURN,
        formation=def_subformation,
        personnel_package=def_personnel,
        side=PlaySideEnum.DEFENSE,
        uid=f"{uid}-kickoff-return-1",
    )
    team.add_play_template(def_play)
    team.add_play_template(kickoff_play)
    team.add_play_template(kickoff_return_play)

    return team


@pytest.fixture
def test_db(tmp_path: Path) -> Generator[DatabaseManager]:
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_game.db"
    db = DatabaseManager(f"sqlite:///{db_path}")
    db.init_db()
    yield db
    db.close()


class TestPylonSimulationRunner:
    """Tests for PylonSimulationRunner."""

    def test_run_single_game_no_db(self, tmp_path: Path) -> None:
        """Test running a single game without database."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")
        output_path = tmp_path / "single_game_results.json"

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=1,
            base_seed=42,
            rules=NFLRules(),
            max_drives=3,  # Short game for testing
            db_manager=None,
            output_mode=OutputMode.JSON,
            json_output_path=output_path,
        )

        results = runner.run()

        assert results["experiment"]["num_reps"] == 1
        assert len(results["results"]["games"]) == 1
        assert results["results"]["games"][0]["home_score"] >= 0
        assert results["results"]["games"][0]["away_score"] >= 0
        assert "experiment" in results
        assert "teams" in results
        assert "results" in results
        assert len(results["teams"]["home"]["athletes"]) > 0
        assert "offense" in results["teams"]["home"]["playbooks"]
        assert "defense" in results["teams"]["home"]["playbooks"]
        assert len(results["results"]["game_details"]) == 1
        assert output_path.exists()

    def test_run_multiple_games_no_db(self, tmp_path: Path) -> None:
        """Test running multiple games without database."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")
        output_path = tmp_path / "multi_game_results.json"

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=3,
            base_seed=42,
            rules=NFLRules(),
            max_drives=2,
            db_manager=None,
            output_mode=OutputMode.JSON,
            json_output_path=output_path,
        )

        results = runner.run()

        assert results["experiment"]["num_reps"] == 3
        assert len(results["results"]["games"]) == 3
        # Each game should have different seed
        seeds = [game["seed"] for game in results["results"]["games"]]
        assert len(set(seeds)) == 3  # All unique
        assert output_path.exists()

    def test_run_game_with_database(self, test_db: DatabaseManager) -> None:
        """Test running a game with database persistence."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=1,
            base_seed=42,
            rules=NFLRules(),
            max_drives=3,
            db_manager=test_db,
            output_mode=OutputMode.DB,
            experiment_name="Test Experiment",
        )

        results: SimulationOutputPayload = runner.run()
        assert isinstance(results, dict)

        # Verify game was persisted
        session = test_db.get_session()
        games = session.query(OrmGame).all()
        session.close()

        assert len(games) == 1
        assert games[0].id == "1"
        assert games[0].seed == 43  # base_seed + rep_number (42 + 1)

    def test_multiple_games_sequential_ids(self, test_db: DatabaseManager) -> None:
        """Test that multiple games get sequential IDs."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=3,
            base_seed=42,
            rules=NFLRules(),
            max_drives=2,
            db_manager=test_db,
            output_mode=OutputMode.DB,
        )

        results: SimulationOutputPayload = runner.run()
        assert isinstance(results, dict)

        # Verify sequential game IDs
        session = test_db.get_session()
        games = session.query(OrmGame).order_by(OrmGame.id).all()
        session.close()

        assert len(games) == 3
        assert games[0].id == "1"
        assert games[1].id == "2"
        assert games[2].id == "3"

    def test_game_with_drives_and_plays(self, test_db: DatabaseManager) -> None:
        """Test that drives and plays are persisted."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=1,
            base_seed=42,
            rules=NFLRules(),
            max_drives=3,
            db_manager=test_db,
            output_mode=OutputMode.DB,
        )

        results: SimulationOutputPayload = runner.run()
        assert isinstance(results, dict)

        # Verify drives were persisted
        session = test_db.get_session()
        games = session.query(OrmGame).all()
        drives = session.query(OrmDrive).all()
        plays = session.query(OrmPlay).all()
        session.close()

        assert len(games) == 1
        assert len(drives) > 0
        assert len(plays) > 0

        # Verify drives reference the game
        for drive in drives:
            assert drive.game_id == "1"

        # Verify plays reference drives
        for play in plays:
            assert play.drive_id is not None

    def test_aggregate_stats_calculation(self, tmp_path: Path) -> None:
        """Test that aggregate statistics are calculated correctly."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=5,
            base_seed=42,
            rules=NFLRules(),
            max_drives=None,
            db_manager=None,
            output_mode=OutputMode.JSON,
            json_output_path=tmp_path / "aggregate_results.json",
        )

        results = runner.run()

        aggregate = results["results"]["aggregate"]
        assert "home_wins" in aggregate
        assert "away_wins" in aggregate
        assert "ties" in aggregate
        assert "avg_home_score" in aggregate
        assert "avg_away_score" in aggregate

        # Wins + ties should equal total games
        total_results = (
            aggregate["home_wins"] + aggregate["away_wins"] + aggregate["ties"]
        )
        assert total_results == 5

    def test_db_mode_requires_db_manager(self) -> None:
        """Test db mode rejects missing database manager."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=1,
            base_seed=42,
            rules=NFLRules(),
            db_manager=None,
            output_mode=OutputMode.DB,
        )

        with pytest.raises(ValueError, match="db_manager is required"):
            runner.run()

    def test_both_mode_writes_json_and_database(
        self, test_db: DatabaseManager, tmp_path: Path
    ) -> None:
        """Test both mode writes JSON and database outputs."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")
        output_path = tmp_path / "both_mode_results.json"

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=1,
            base_seed=42,
            rules=NFLRules(),
            db_manager=test_db,
            output_mode=OutputMode.BOTH,
            json_output_path=output_path,
        )

        results = runner.run()
        assert results["experiment"]["num_reps"] == 1
        assert output_path.exists()

        with output_path.open("r", encoding="utf-8") as file_handle:
            saved = json.load(file_handle)
        assert saved["experiment"]["num_reps"] == 1
        assert "experiment" in saved
        assert "teams" in saved
        assert "results" in saved

        session = test_db.get_session()
        games = session.query(OrmGame).all()
        session.close()
        assert len(games) == 1


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    def test_full_simulation_workflow(
        self, test_db: DatabaseManager, tmp_path: Path
    ) -> None:
        """Test complete simulation workflow with all features."""
        home = create_test_team("chiefs", "Kansas City Chiefs")
        away = create_test_team("49ers", "San Francisco 49ers")

        runner = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=2,
            base_seed=42,
            rules=NFLRules(),
            max_drives=3,
            db_manager=test_db,
            output_mode=OutputMode.BOTH,
            json_output_path=tmp_path / "full_workflow_results.json",
            experiment_name="Chiefs vs 49ers Test",
            experiment_description="Integration test of full workflow",
            log_dir=tmp_path / "logs",
        )

        results = runner.run()

        # Verify results structure
        assert "experiment" in results
        assert results["experiment"]["name"] == "Chiefs vs 49ers Test"
        assert results["experiment"]["num_reps"] == 2
        assert len(results["results"]["games"]) == 2
        assert len(results["results"]["game_details"]) == 2

        # Verify database state
        session = test_db.get_session()
        games = session.query(OrmGame).all()
        drives = session.query(OrmDrive).all()
        plays = session.query(OrmPlay).all()
        session.close()

        assert len(games) == 2
        assert len(drives) > 0
        assert len(plays) > 0

        # Verify log files were created
        log_dir = tmp_path / "logs"
        assert log_dir.exists()
        log_files = list(log_dir.glob("pylon.*.log"))
        assert len(log_files) == 2  # One per rep
        assert (tmp_path / "full_workflow_results.json").exists()

    def test_deterministic_replay(self, tmp_path: Path) -> None:
        """Test that same seed produces same results."""
        home = create_test_team("home", "Home Team")
        away = create_test_team("away", "Away Team")

        # Run first simulation
        runner1 = PylonSimulationRunner(
            home_team=home,
            away_team=away,
            num_reps=1,
            base_seed=12345,
            rules=NFLRules(),
            max_drives=3,
            db_manager=None,
            output_mode=OutputMode.JSON,
            json_output_path=tmp_path / "deterministic_1.json",
        )
        results1 = runner1.run()

        # Run second simulation with same seed
        home2 = create_test_team("home", "Home Team")
        away2 = create_test_team("away", "Away Team")

        runner2 = PylonSimulationRunner(
            home_team=home2,
            away_team=away2,
            num_reps=1,
            base_seed=12345,
            rules=NFLRules(),
            max_drives=3,
            db_manager=None,
            output_mode=OutputMode.JSON,
            json_output_path=tmp_path / "deterministic_2.json",
        )
        results2 = runner2.run()

        # Results should be identical
        game1 = results1["results"]["games"][0]
        game2 = results2["results"]["games"][0]

        assert game1["seed"] == game2["seed"]
        assert game1["home_score"] == game2["home_score"]
        assert game1["away_score"] == game2["away_score"]
        assert game1["total_plays"] == game2["total_plays"]
        assert game1["total_drives"] == game2["total_drives"]
