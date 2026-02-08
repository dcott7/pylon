"""Tests for state layer: GameState, DriveRecord, PlayRecord, etc."""

from pylon.domain.team import Team
from pylon.state.game_state import GameState, GameStatus
from pylon.state.game_clock import GameClock
from pylon.state.scoreboard_state import Scoreboard
from pylon.state.possession_state import PossessionState


class TestGameClock:
    """Tests for GameClock class."""

    def test_create_game_clock(self) -> None:
        """Test basic game clock creation."""
        elapsed = 0
        clock = GameClock(lambda: elapsed, minutes_per_quarter=15, num_reg_quarters=4)
        assert clock.current_quarter == 1
        assert clock.time_remaining == 3600  # 60 minutes total (4 quarters × 15 min)
        assert clock.min_per_qtr == 15

    def test_clock_quarter_progression(self) -> None:
        """Test clock advancing through quarters."""
        elapsed = 0

        def get_elapsed():
            return elapsed

        clock = GameClock(get_elapsed, minutes_per_quarter=15, num_reg_quarters=4)
        assert clock.current_quarter == 1

        # Advance to Q2
        elapsed = 901
        assert clock.current_quarter == 2

        # Advance to Q3
        elapsed = 1801
        assert clock.current_quarter == 3

        # Advance to Q4
        elapsed = 2701
        assert clock.current_quarter == 4

    def test_seconds_left_in_quarter(self) -> None:
        """Test calculating seconds left in game."""
        elapsed = 0

        def get_elapsed():
            return elapsed

        clock = GameClock(get_elapsed, minutes_per_quarter=15, num_reg_quarters=4)

        # Start of Q1: 3600 seconds left in game
        assert clock.time_remaining == 3600

        # 5 minutes elapsed: 3300 seconds left in game
        elapsed = 300
        assert clock.time_remaining == 3300
        # 1 second left in Q1: 2701 seconds left in game
        elapsed = 899
        assert clock.time_remaining == 2701

        # Start of Q2: 2700 seconds left in game (3 quarters remaining)
        elapsed = 900
        assert clock.time_remaining == 2700


class TestScoreboard:
    """Tests for Scoreboard class."""

    def test_create_scoreboard(self) -> None:
        """Test basic scoreboard creation."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        scoreboard = Scoreboard(home, away)

        assert scoreboard.current_score(home) == 0
        assert scoreboard.current_score(away) == 0

    def test_score_touchdown(self) -> None:
        """Test scoring a touchdown."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        scoreboard = Scoreboard(home, away)

        scoreboard.add_points(home, 6)
        assert scoreboard.current_score(home) == 6
        assert scoreboard.current_score(away) == 0

    def test_score_field_goal(self) -> None:
        """Test scoring a field goal."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        scoreboard = Scoreboard(home, away)

        scoreboard.add_points(away, 3)
        assert scoreboard.current_score(home) == 0
        assert scoreboard.current_score(away) == 3

    def test_score_extra_point(self) -> None:
        """Test scoring an extra point."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        scoreboard = Scoreboard(home, away)

        scoreboard.add_points(home, 6)
        scoreboard.add_points(home, 1)
        assert scoreboard.current_score(home) == 7

    def test_score_two_point_conversion(self) -> None:
        """Test scoring a two-point conversion."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        scoreboard = Scoreboard(home, away)

        scoreboard.add_points(home, 6)
        scoreboard.add_points(home, 2)
        assert scoreboard.current_score(home) == 8

    def test_score_safety(self) -> None:
        """Test scoring a safety."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")
        scoreboard = Scoreboard(home, away)

        scoreboard.add_points(away, 2)
        assert scoreboard.current_score(home) == 0
        assert scoreboard.current_score(away) == 2


class TestPossessionState:
    """Tests for PossessionState class."""

    def test_create_possession_state(self) -> None:
        """Test basic possession state creation."""
        team = Team(uid="team-1", name="Team 1")
        possession = PossessionState(
            pos_team=team, ball_position=25, down=1, distance=10
        )

        assert possession.pos_team == team
        assert possession.ball_position == 25
        assert possession.down == 1
        assert possession.distance == 10

    def test_advance_down(self) -> None:
        """Test advancing down."""
        team = Team(uid="team-1", name="Team 1")
        possession = PossessionState(
            pos_team=team, ball_position=25, down=1, distance=10
        )

        possession.advance_down()
        assert possession.down == 2

        possession.advance_down()
        assert possession.down == 3

        possession.advance_down()
        assert possession.down == 4

    def test_reset_down_and_distance(self) -> None:
        """Test resetting downs after first down."""
        team = Team(uid="team-1", name="Team 1")
        possession = PossessionState(
            pos_team=team, ball_position=25, down=3, distance=2
        )

        possession.reset_down_and_distance()
        assert possession.down == 1
        assert possession.distance == 10


class TestGameState:
    """Tests for GameState class."""

    def test_create_game_state(self):
        """Test basic game state creation."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")

        game_state = GameState(
            home_team=home,
            away_team=away,
            minutes_per_quarter=15,
            quarters_per_half=2,
            max_timeouts=3,
            game_id="1",
        )

        assert game_state.home_team == home
        assert game_state.away_team == away
        assert game_state.game_data.game_id == "1"
        assert game_state.game_data.status == GameStatus.NOT_STARTED

    def test_game_state_opponent(self):
        """Test getting opponent team."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")

        game_state = GameState(
            home_team=home,
            away_team=away,
            minutes_per_quarter=15,
            quarters_per_half=2,
            max_timeouts=3,
            game_id="1",
        )

        assert game_state.opponent(home) == away
        assert game_state.opponent(away) == home

    def test_game_state_start_end(self):
        """Test starting and ending game."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")

        game_state = GameState(
            home_team=home,
            away_team=away,
            minutes_per_quarter=15,
            quarters_per_half=2,
            max_timeouts=3,
            game_id="1",
        )

        assert game_state.game_data.status == GameStatus.NOT_STARTED

        game_state.game_data.start_game()
        assert game_state.game_data.status == GameStatus.IN_PROGRESS

        game_state.game_data.end_game()
        assert game_state.game_data.status == GameStatus.COMPLETE

    def test_game_state_total_drives_plays(self):
        """Test counting total drives and plays."""
        home = Team(uid="home", name="Home Team")
        away = Team(uid="away", name="Away Team")

        game_state = GameState(
            home_team=home,
            away_team=away,
            minutes_per_quarter=15,
            quarters_per_half=2,
            max_timeouts=3,
            game_id="1",
        )

        assert game_state.total_drives() == 0
        assert game_state.total_plays() == 0
