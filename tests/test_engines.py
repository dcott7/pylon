"""Tests for specialized engine classes: Drive, Play, and core engine interactions."""

import pytest
from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team
from pylon.domain.playbook import (
    Formation,
    PersonnelPackage,
    PlayCall,
    PlayTypeEnum,
    PlaySideEnum,
)
from pylon.state.drive_record import DriveRecord, DriveEndResult
from pylon.state.play_record import ScoringTypeEnum
from pylon.engine.drive_engine import DriveEngine
from pylon.engine.play_engine import PlayEngine
from pylon.engine.game_engine import GameEngine
from pylon.models.registry import ModelRegistry
from pylon.domain.rules.nfl import NFLRules
from pylon.rng import RNG


def create_test_team(uid: str, name: str) -> Team:
    """Helper to create a team with valid roster and plays."""
    team = Team(uid=uid, name=name)

    # Add minimal roster
    positions = [
        AthletePositionEnum.QB,
        AthletePositionEnum.RB,
        AthletePositionEnum.WR,
        AthletePositionEnum.TE,
        AthletePositionEnum.LT,
        AthletePositionEnum.LG,
        AthletePositionEnum.C,
        AthletePositionEnum.RG,
        AthletePositionEnum.RT,
        AthletePositionEnum.EDGE,
        AthletePositionEnum.EDGE,
    ]

    for i, pos in enumerate(positions):
        team.add_athlete(
            Athlete(
                uid=f"{uid}-player-{i}",
                first_name=f"Player{i}",
                last_name="Test",
                position=pos,
            )
        )

    # Add valid plays with proper formation hierarchy
    parent_formation = Formation(
        name=f"{uid}-Parent",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 2,
            AthletePositionEnum.TE: 1,
        },
        uid=f"{uid}-parent-form",
    )

    formation = Formation(
        name=f"{uid}-Sub",
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
        uid=f"{uid}-form",
    )

    personnel = PersonnelPackage(
        name="11 Personnel",
        counts={
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 3,
            AthletePositionEnum.TE: 1,
        },
        uid=f"{uid}-pers",
    )

    play = PlayCall(
        uid=f"{uid}-play",
        name="Test Play",
        play_type=PlayTypeEnum.PASS,
        formation=formation,
        personnel_package=personnel,
        side=PlaySideEnum.OFFENSE,
    )

    team.add_play_template(play)
    return team


@pytest.fixture
def game_engine():
    """Fixture providing a game engine with valid setup."""
    home = create_test_team("home", "Home")
    away = create_test_team("away", "Away")

    engine = GameEngine(
        home_team=home,
        away_team=away,
        game_id="test-game-1",
        rng=RNG(seed=42),
        rules=NFLRules(),
    )
    return engine


class TestDriveRecord:
    """Tests for DriveRecord state capture."""

    def test_create_drive_record(self, game_engine: GameEngine) -> None:
        """Test creating a drive record."""
        drive = DriveRecord(game_engine.game_state)
        assert len(drive.plays) == 0
        assert drive is not None

    def test_drive_end_result_enum(self):
        """Test drive end result enum values."""
        assert DriveEndResult.SCORE.value == "score"
        assert DriveEndResult.TURNOVER.value == "turnover"
        assert DriveEndResult.PUNT.value == "punt"
        assert DriveEndResult.FIELD_GOAL_ATTEMPT.value == "field_goal_attempt"
        assert DriveEndResult.END_OF_HALF.value == "end_of_half"
        assert DriveEndResult.END_OF_GAME.value == "end_of_game"


class TestPlayRecord:
    """Tests for PlayRecord state capture."""

    def test_play_record_scoring_type(self):
        """Test play record scoring type enum."""
        assert ScoringTypeEnum.TOUCHDOWN.value == "touchdown"
        assert ScoringTypeEnum.FIELD_GOAL.value == "field_goal"
        assert ScoringTypeEnum.SAFETY.value == "safety"
        assert ScoringTypeEnum.EXTRA_POINT_KICK.value == "extra_point_kick"
        assert ScoringTypeEnum.EXTRA_POINT_TWO_POINT.value == "extra_point_two_point"


class TestDriveEngine:
    """Tests for drive-level simulation engine."""

    def test_create_drive_engine(self, game_engine: GameEngine) -> None:
        """Test creating a drive engine."""
        models = ModelRegistry()
        rng = RNG(seed=42)
        rules = NFLRules()

        engine = DriveEngine(game_engine.game_state, models, rng, rules)
        assert engine.game_state == game_engine.game_state
        assert engine.drive_record is not None
        assert isinstance(engine.drive_record, DriveRecord)

    def test_drive_engine_has_play_engine(self, game_engine: GameEngine) -> None:
        """Test that drive engine has a play engine."""
        models = ModelRegistry()
        rng = RNG(seed=42)
        rules = NFLRules()

        engine = DriveEngine(game_engine.game_state, models, rng, rules)
        assert engine.play_engine is not None
        assert isinstance(engine.play_engine, PlayEngine)


class TestPlayEngine:
    """Tests for play-level simulation engine."""

    def test_create_play_engine(self, game_engine: GameEngine) -> None:
        """Test creating a play engine."""
        models = ModelRegistry()
        rng = RNG(seed=42)
        rules = NFLRules()

        engine = PlayEngine(game_engine.game_state, models, rng, rules)
        assert engine.game_state == game_engine.game_state
        assert engine.models == models
        assert engine.rng == rng
        assert engine.rules == rules

    def test_play_engine_with_rng(self, game_engine: GameEngine) -> None:
        """Test play engine uses RNG for randomness."""
        models = ModelRegistry()
        rng = RNG(seed=42)
        rules = NFLRules()

        engine = PlayEngine(game_engine.game_state, models, rng, rules)

        # RNG should be available for play execution
        random_value = engine.rng.randint(1, 100)
        assert 1 <= random_value <= 100


class TestNFLRulesConstants:
    """Tests for NFL rule constants."""

    def test_nfl_game_structure(self):
        """Test NFL game structure constants."""
        assert NFLRules.MINUTES_PER_QUARTER == 15
        assert NFLRules.QUARTERS_PER_HALF == 2
        assert NFLRules.TIMEOUTS_PER_HALF == 3

    def test_nfl_field_positions(self):
        """Test NFL field position constants."""
        assert NFLRules.KICKOFF_SPOT == 35
        assert NFLRules.EXTRA_POINT_SPOT == 15
        assert NFLRules.DEFAULT_TOUCHBACK_SPOT == 20
        assert NFLRules.FIELD_LENGTH == 100

    def test_nfl_scoring_values(self):
        """Test NFL scoring constants."""
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.TOUCHDOWN] == 6
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.FIELD_GOAL] == 3
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.SAFETY] == 2
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.EXTRA_POINT_KICK] == 1
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.EXTRA_POINT_TWO_POINT] == 2

    def test_nfl_play_rules(self):
        """Test NFL play rule constants."""
        assert NFLRules.FIRST_DOWN_YARDS == 10
        assert NFLRules.MAX_DOWNS == 4

    def test_nfl_first_down_rule_object(self):
        """Test NFL first down rule object."""
        assert NFLRules.first_down_rule is not None
        assert NFLRules.first_down_rule.first_down_yards == 10
        assert NFLRules.first_down_rule.max_downs == 4

    def test_nfl_create_instance(self):
        """Test creating NFL rules instance."""
        rules = NFLRules()
        assert rules.MINUTES_PER_QUARTER == 15
        assert rules.KICKOFF_SPOT == 35
        assert rules.FIRST_DOWN_YARDS == 10
        assert rules.MAX_DOWNS == 4


class TestGameEngine:
    """Tests for GameEngine."""

    def test_game_engine_creation(self, game_engine: GameEngine) -> None:
        """Test GameEngine creates valid game state."""
        assert game_engine.game_state is not None
        assert game_engine.game_state.home_team is not None
        assert game_engine.game_state.away_team is not None

    def test_game_engine_rng_seeding(self) -> None:
        """Test GameEngine respects RNG seeding."""
        home = create_test_team("home", "Home")
        away = create_test_team("away", "Away")

        # Two engines with same seed should be created consistently
        engine1 = GameEngine(
            home_team=home,
            away_team=away,
            game_id="game1",
            rng=RNG(seed=42),
            rules=NFLRules(),
        )

        engine2 = GameEngine(
            home_team=create_test_team("home2", "Home2"),
            away_team=create_test_team("away2", "Away2"),
            game_id="game2",
            rng=RNG(seed=42),
            rules=NFLRules(),
        )

        # Both should be playable
        assert engine1.game_state is not None
        assert engine2.game_state is not None

    def test_game_engine_initial_possession(self, game_engine: GameEngine) -> None:
        """Test game engine initializes possession."""
        assert game_engine.game_state.pos_team is not None
        assert game_engine.game_state.def_team is not None

    def test_game_engine_clock(self, game_engine: GameEngine) -> None:
        """Test game engine clock is initialized."""
        assert game_engine.game_state.clock is not None
        assert game_engine.game_state.clock.current_quarter == 1
        assert game_engine.game_state.clock.time_remaining == 3600  # 60 minutes


class TestEngineIntegration:
    """Integration tests for engines working together."""

    def test_game_state_time_management(self, game_engine: GameEngine) -> None:
        """Test game state manages time correctly."""
        initial_time = game_engine.game_state.clock.seconds_elapsed
        assert initial_time == 0

        # Total time should be 3600 seconds (60 minutes)
        assert game_engine.game_state.clock.time_remaining == 3600

    def test_game_state_team_rosters(self, game_engine: GameEngine) -> None:
        """Test teams have rosters loaded."""
        assert len(game_engine.game_state.home_team.roster) > 0
        assert len(game_engine.game_state.away_team.roster) > 0

    def test_game_state_scoreboard(self, game_engine: GameEngine) -> None:
        """Test scoreboard is initialized."""
        assert game_engine.game_state.scoreboard is not None
        assert (
            game_engine.game_state.scoreboard.current_score(
                game_engine.game_state.home_team
            )
            == 0
        )
        assert (
            game_engine.game_state.scoreboard.current_score(
                game_engine.game_state.away_team
            )
            == 0
        )
