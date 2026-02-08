"""Tests for engine layer: GameEngine, DriveEngine, and specialized engines."""

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
from pylon.engine.game_engine import GameEngine
from pylon.rng import RNG
from pylon.state.game_state import GameStatus


def create_minimal_team(uid: str, name: str) -> Team:
    """Helper to create a minimal team with basic roster."""
    team = Team(uid=uid, name=name)

    # Add minimal roster
    qb = Athlete(
        uid=f"{uid}-qb",
        first_name="Test",
        last_name="QB",
        position=AthletePositionEnum.QB,
    )
    rb = Athlete(
        uid=f"{uid}-rb",
        first_name="Test",
        last_name="RB",
        position=AthletePositionEnum.RB,
    )
    wr1 = Athlete(
        uid=f"{uid}-wr1",
        first_name="Test",
        last_name="WR1",
        position=AthletePositionEnum.WR,
    )
    wr2 = Athlete(
        uid=f"{uid}-wr2",
        first_name="Test",
        last_name="WR2",
        position=AthletePositionEnum.WR,
    )
    te = Athlete(
        uid=f"{uid}-te",
        first_name="Test",
        last_name="TE",
        position=AthletePositionEnum.TE,
    )
    lt = Athlete(
        uid=f"{uid}-lt",
        first_name="Test",
        last_name="LT",
        position=AthletePositionEnum.LT,
    )
    lg = Athlete(
        uid=f"{uid}-lg",
        first_name="Test",
        last_name="LG",
        position=AthletePositionEnum.LG,
    )
    c = Athlete(
        uid=f"{uid}-c", first_name="Test", last_name="C", position=AthletePositionEnum.C
    )
    rg = Athlete(
        uid=f"{uid}-rg",
        first_name="Test",
        last_name="RG",
        position=AthletePositionEnum.RG,
    )
    rt = Athlete(
        uid=f"{uid}-rt",
        first_name="Test",
        last_name="RT",
        position=AthletePositionEnum.RT,
    )

    # Defense
    de1 = Athlete(
        uid=f"{uid}-de1",
        first_name="Test",
        last_name="DE1",
        position=AthletePositionEnum.EDGE,
    )
    de2 = Athlete(
        uid=f"{uid}-de2",
        first_name="Test",
        last_name="DE2",
        position=AthletePositionEnum.EDGE,
    )
    dt1 = Athlete(
        uid=f"{uid}-dt1",
        first_name="Test",
        last_name="DT1",
        position=AthletePositionEnum.DT,
    )
    dt2 = Athlete(
        uid=f"{uid}-dt2",
        first_name="Test",
        last_name="DT2",
        position=AthletePositionEnum.DT,
    )
    lb1 = Athlete(
        uid=f"{uid}-lb1",
        first_name="Test",
        last_name="LB1",
        position=AthletePositionEnum.LB,
    )
    lb2 = Athlete(
        uid=f"{uid}-lb2",
        first_name="Test",
        last_name="LB2",
        position=AthletePositionEnum.LB,
    )
    lb3 = Athlete(
        uid=f"{uid}-lb3",
        first_name="Test",
        last_name="LB3",
        position=AthletePositionEnum.LB,
    )
    cb1 = Athlete(
        uid=f"{uid}-cb1",
        first_name="Test",
        last_name="CB1",
        position=AthletePositionEnum.CB,
    )
    cb2 = Athlete(
        uid=f"{uid}-cb2",
        first_name="Test",
        last_name="CB2",
        position=AthletePositionEnum.CB,
    )
    s1 = Athlete(
        uid=f"{uid}-s1",
        first_name="Test",
        last_name="S1",
        position=AthletePositionEnum.FS,
    )
    s2 = Athlete(
        uid=f"{uid}-s2",
        first_name="Test",
        last_name="S2",
        position=AthletePositionEnum.SS,
    )

    # Special teams
    k = Athlete(
        uid=f"{uid}-k", first_name="Test", last_name="K", position=AthletePositionEnum.K
    )
    p = Athlete(
        uid=f"{uid}-p", first_name="Test", last_name="P", position=AthletePositionEnum.P
    )

    for athlete in [
        qb,
        rb,
        wr1,
        wr2,
        te,
        lt,
        lg,
        c,
        rg,
        rt,
        de1,
        de2,
        dt1,
        dt2,
        lb1,
        lb2,
        lb3,
        cb1,
        cb2,
        s1,
        s2,
        k,
        p,
    ]:
        team.add_athlete(athlete)

    # Add basic playbook
    parent_formation = Formation(
        name="Singleback",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 2,
            AthletePositionEnum.TE: 1,
        },
    )
    subformation = Formation(
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
    pass_play = PlayCall(
        uid=f"{uid}-pass-1",
        name="Basic Pass",
        play_type=PlayTypeEnum.PASS,
        formation=subformation,
        personnel_package=personnel,
        side=PlaySideEnum.OFFENSE,
    )
    run_play = PlayCall(
        uid=f"{uid}-run-1",
        name="Basic Run",
        play_type=PlayTypeEnum.RUN,
        formation=subformation,
        personnel_package=personnel,
        side=PlaySideEnum.OFFENSE,
    )
    def_play = PlayCall(
        uid=f"{uid}-def-1",
        name="Base Defense",
        play_type=PlayTypeEnum.DEFENSIVE_PLAY,
        formation=def_subformation,
        personnel_package=def_personnel,
        side=PlaySideEnum.DEFENSE,
    )
    team.add_play_template(pass_play)
    team.add_play_template(run_play)
    team.add_play_template(def_play)

    return team


class TestGameEngine:
    """Tests for GameEngine class."""

    def test_create_game_engine(self):
        """Test basic game engine creation."""
        home = create_minimal_team("home", "Home Team")
        away = create_minimal_team("away", "Away Team")

        engine = GameEngine(
            home_team=home,
            away_team=away,
            game_id="1",
            rng=RNG(seed=42),
            rules=NFLRules(),
        )

        assert engine.game_state.home_team == home
        assert engine.game_state.away_team == away
        assert engine.game_state.game_data.game_id == "1"
        assert engine.game_state.game_data.status == GameStatus.NOT_STARTED

    def test_game_engine_with_max_drives(self):
        """Test game engine with max drives limit."""
        home = create_minimal_team("home", "Home Team")
        away = create_minimal_team("away", "Away Team")

        engine = GameEngine(
            home_team=home,
            away_team=away,
            game_id="1",
            rng=RNG(seed=42),
            rules=NFLRules(),
            max_drives=5,
        )

        assert engine.max_drives == 5
        assert engine.max_drives_reached is False

    def test_game_engine_run_short_game(self):
        """Test running a short game with max drives."""
        home = create_minimal_team("home", "Home Team")
        away = create_minimal_team("away", "Away Team")

        engine = GameEngine(
            home_team=home,
            away_team=away,
            game_id="1",
            rng=RNG(seed=42),
            rules=NFLRules(),
            max_drives=3,  # Very short game for testing
        )

        engine.run()

        # Game should have completed or hit max drives
        assert (
            engine.game_state.game_data.status == GameStatus.COMPLETE
            or engine.max_drives_reached
        )
        assert len(engine.game_state.drives) <= 3


class TestRNG:
    """Tests for RNG class."""

    def test_rng_deterministic(self):
        """Test that RNG with same seed produces same results."""
        rng1 = RNG(seed=42)
        rng2 = RNG(seed=42)

        results1 = [rng1.random() for _ in range(10)]
        results2 = [rng2.random() for _ in range(10)]

        assert results1 == results2

    def test_rng_different_seeds(self):
        """Test that different seeds produce different results."""
        rng1 = RNG(seed=42)
        rng2 = RNG(seed=43)

        results1 = [rng1.random() for _ in range(10)]
        results2 = [rng2.random() for _ in range(10)]

        assert results1 != results2

    def test_rng_choice(self):
        """Test RNG choice method."""
        rng = RNG(seed=42)
        options = ["A", "B", "C", "D"]

        choices = [rng.choice(options) for _ in range(20)]

        # Should have picked from options
        assert all(choice in options for choice in choices)
        # With 20 picks, should have some variety (not all same)
        assert len(set(choices)) > 1

    def test_rng_randint(self):
        """Test RNG randint method."""
        rng = RNG(seed=42)

        results = [rng.randint(1, 10) for _ in range(20)]

        # All results should be in range
        assert all(1 <= r <= 10 for r in results)
        # Should have some variety
        assert len(set(results)) > 1


class TestNFLRules:
    """Tests for NFL rules implementation."""

    def test_nfl_rules_constants(self):
        """Test NFL rules constants."""
        rules = NFLRules()

        assert rules.MINUTES_PER_QUARTER == 15
        assert rules.QUARTERS_PER_HALF == 2
        assert rules.TIMEOUTS_PER_HALF == 3

    def test_nfl_rules_field_dimensions(self):
        """Test NFL field dimensions."""
        rules = NFLRules()

        assert rules.FIELD_LENGTH == 100
        # Check kickoff and other field position rules exist
        assert hasattr(rules, "KICKOFF_SPOT")
