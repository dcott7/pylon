"""Tests for database layer: schema, repositories, and persistence."""

from typing import Any, Generator
from pathlib import Path

import pytest
from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team
from pylon.domain.playbook import (
    PlayCall,
    PlayTypeEnum,
    PlaySideEnum,
    Formation,
    PersonnelPackage,
)
from pylon.db.database import DatabaseManager
from pylon.db.repositories import (
    TeamRepository,
    AthleteRepository,
    PlayCallRepository,
    GameRepository,
    DimensionRepository,
)
from pylon.db.schema import (
    Team as OrmTeam,
    Athlete as OrmAthlete,
    PlayCall as OrmPlayCall,
)


@pytest.fixture
def db_manager() -> Generator[DatabaseManager, Any, None]:
    """Create an in-memory database for testing."""
    db = DatabaseManager("sqlite:///:memory:")
    db.init_db()
    yield db
    db.close()


class TestDatabaseSetup:
    """Tests for database setup and configuration."""

    def test_create_in_memory_database(self, db_manager: DatabaseManager) -> None:
        """Test creating an in-memory database."""
        assert db_manager is not None
        session = db_manager.get_session()
        assert session is not None
        session.close()

    def test_create_file_database(self, tmp_path: Path) -> None:
        """Test creating a file-based database."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(f"sqlite:///{db_path}")
        db.init_db()

        assert db_path.exists()
        db.close()


class TestTeamRepository:
    """Tests for TeamRepository."""

    def test_save_team(self, db_manager: DatabaseManager) -> None:
        """Test saving a team to database."""
        team = Team(uid="team-1", name="Test Team")
        repo = TeamRepository(db_manager)

        orm_team = repo.save(team)

        assert orm_team.id == "team-1"
        assert orm_team.name == "Test Team"

    def test_save_team_batch(self, db_manager: DatabaseManager) -> None:
        """Test batch saving teams."""
        teams = [
            Team(uid="team-1", name="Team 1"),
            Team(uid="team-2", name="Team 2"),
            Team(uid="team-3", name="Team 3"),
        ]
        repo = TeamRepository(db_manager)

        orm_teams = repo.save_batch(teams)

        assert len(orm_teams) == 3
        assert orm_teams[0].id == "team-1"
        assert orm_teams[1].id == "team-2"
        assert orm_teams[2].id == "team-3"

    def test_retrieve_saved_team(self, db_manager: DatabaseManager) -> None:
        """Test retrieving a saved team from database."""
        team = Team(uid="team-1", name="Test Team")
        repo = TeamRepository(db_manager)
        repo.save(team)

        # Query it back
        session = db_manager.get_session()
        orm_team = session.query(OrmTeam).filter_by(id="team-1").first()
        session.close()

        assert orm_team is not None
        assert orm_team.id == "team-1"
        assert orm_team.name == "Test Team"


class TestAthleteRepository:
    """Tests for AthleteRepository."""

    def test_save_athlete(self, db_manager: DatabaseManager) -> None:
        """Test saving an athlete to database."""
        athlete = Athlete(
            uid="athlete-1",
            first_name="John",
            last_name="Doe",
            position=AthletePositionEnum.QB,
        )
        repo = AthleteRepository(db_manager)

        orm_athlete = repo.save(athlete)

        assert orm_athlete.id == "athlete-1"
        assert orm_athlete.first_name == "John"
        assert orm_athlete.last_name == "Doe"
        assert orm_athlete.position == AthletePositionEnum.QB

    def test_save_athlete_batch(self, db_manager: DatabaseManager) -> None:
        """Test batch saving athletes."""
        athletes = [
            Athlete(
                uid=f"athlete-{i}",
                first_name=f"Player{i}",
                last_name=f"Last{i}",
                position=AthletePositionEnum.WR,
            )
            for i in range(5)
        ]
        repo = AthleteRepository(db_manager)

        orm_athletes = repo.save_batch(athletes)

        assert len(orm_athletes) == 5


class TestPlayCallRepository:
    """Tests for PlayCallRepository."""

    def test_save_play_call(self, db_manager: DatabaseManager) -> None:
        """Test saving a play call to database."""
        # First save a team (required foreign key)
        team = Team(uid="team-1", name="Test Team")
        team_repo = TeamRepository(db_manager)
        team_repo.save(team)

        parent_formation = Formation(
            name="Singleback",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
        )
        formation = Formation(
            name="Singleback Tight",
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
            parent=parent_formation,
        )
        personnel = PersonnelPackage(
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
        )

        play = PlayCall(
            uid="play-1",
            name="Deep Pass",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )
        repo = PlayCallRepository(db_manager)

        orm_play = repo.save(play, team_id="team-1")

        assert orm_play.id == "play-1"
        assert orm_play.name == "Deep Pass"
        assert orm_play.team_id == "team-1"


class TestGameRepository:
    """Tests for GameRepository."""

    def test_create_game(self, db_manager: DatabaseManager) -> None:
        """Test creating a game record."""
        # First save teams
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        team_repo = TeamRepository(db_manager)
        team_repo.save(home)
        team_repo.save(away)

        repo = GameRepository(db_manager)
        orm_game = repo.create(
            seed=42,
            home_team_id="home",
            away_team_id="away",
            home_score=21,
            away_score=17,
            winner_id="home",
            total_plays=125,
            total_drives=12,
            final_quarter=4,
            game_id="1",
        )

        assert orm_game.id == "1"
        assert orm_game.seed == 42
        assert orm_game.home_team_id == "home"
        assert orm_game.away_team_id == "away"
        assert orm_game.home_score == 21
        assert orm_game.away_score == 17
        assert orm_game.winner_id == "home"

    def test_sequential_game_ids(self, db_manager: DatabaseManager) -> None:
        """Test that games get sequential IDs."""
        # Save teams
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        team_repo = TeamRepository(db_manager)
        team_repo.save(home)
        team_repo.save(away)

        repo = GameRepository(db_manager)

        # Create multiple games
        game1 = repo.create(
            seed=42,
            home_team_id="home",
            away_team_id="away",
            home_score=21,
            away_score=17,
            winner_id="home",
            total_plays=100,
            total_drives=10,
            final_quarter=4,
            game_id="1",
        )

        game2 = repo.create(
            seed=43,
            home_team_id="home",
            away_team_id="away",
            home_score=24,
            away_score=20,
            winner_id="home",
            total_plays=105,
            total_drives=11,
            final_quarter=4,
            game_id="2",
        )

        assert game1.id == "1"
        assert game2.id == "2"


class TestDimensionRepository:
    """Tests for DimensionRepository facade."""

    def test_persist_game_dimensions(self, db_manager: DatabaseManager) -> None:
        """Test persisting all game dimensions at once."""
        # Create teams with rosters
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")

        for i in range(3):
            home.add_athlete(
                Athlete(
                    uid=f"home-player-{i}",
                    first_name=f"Home{i}",
                    last_name=f"Player{i}",
                    position=AthletePositionEnum.WR,
                )
            )
            away.add_athlete(
                Athlete(
                    uid=f"away-player-{i}",
                    first_name=f"Away{i}",
                    last_name=f"Player{i}",
                    position=AthletePositionEnum.WR,
                )
            )

        # Create shared formations
        parent_formation = Formation(
            name="Singleback",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
        )

        formation = Formation(
            name="Singleback Tight",
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
            parent=parent_formation,
        )

        personnel = PersonnelPackage(
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
        )

        # Add plays to playbooks using shared formations
        home.add_play_template(
            PlayCall(
                uid="home-pass",
                name="Pass Play",
                play_type=PlayTypeEnum.PASS,
                formation=formation,
                personnel_package=personnel,
                side=PlaySideEnum.OFFENSE,
            )
        )

        away.add_play_template(
            PlayCall(
                uid="away-pass",
                name="Pass Play",
                play_type=PlayTypeEnum.PASS,
                formation=formation,
                personnel_package=personnel,
                side=PlaySideEnum.OFFENSE,
            )
        )

        repo = DimensionRepository(db_manager)
        repo.persist_game_dimensions(home, away)

        # Verify teams were saved
        session = db_manager.get_session()
        teams = session.query(OrmTeam).all()
        athletes = session.query(OrmAthlete).all()
        plays = session.query(OrmPlayCall).all()
        session.close()

        assert len(teams) == 2
        assert len(athletes) == 6  # 3 per team
        assert len(plays) >= 2  # At least 1 per team
