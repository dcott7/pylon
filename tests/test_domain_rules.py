"""Tests for domain rules: NFL rule validation and constraints."""

from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team
from pylon.domain.playbook import (
    Formation,
    PersonnelPackage,
    PlayCall,
    PlayTypeEnum,
    PlaySideEnum,
)
from pylon.domain.rules.nfl import NFLRules
from pylon.state.play_record import ScoringTypeEnum


class TestFormationValidation:
    """Tests for formation rules and constraints."""

    def test_formation_position_counts_valid(self):
        """Test formation with valid position counts."""
        formation = Formation(
            name="Singleback",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
                AthletePositionEnum.OLINE: 5,
            },
            uid="form-1",
        )
        assert formation.name == "Singleback"
        assert len(formation.position_counts) == 5

    def test_formation_with_parent(self):
        """Test formation with parent formation."""
        parent = Formation(
            name="Parent",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
            uid="parent-1",
        )

        child = Formation(
            name="Child",
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
            parent=parent,
            uid="child-1",
        )

        assert child.parent == parent
        assert child.name == "Child"

    def test_formation_offensive_positions(self):
        """Test formation with offensive positions."""
        formation = Formation(
            name="I-Form",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 2,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
                AthletePositionEnum.OLINE: 5,
            },
            uid="form-2",
        )

        offensive_positions = {
            AthletePositionEnum.QB,
            AthletePositionEnum.RB,
            AthletePositionEnum.WR,
            AthletePositionEnum.TE,
            AthletePositionEnum.OLINE,
        }

        for pos in formation.position_counts.keys():
            assert pos in offensive_positions

    def test_formation_defensive_positions(self):
        """Test formation with defensive positions."""
        formation = Formation(
            name="Nickel",
            position_counts={
                AthletePositionEnum.EDGE: 2,
                AthletePositionEnum.DT: 2,
                AthletePositionEnum.LB: 3,
                AthletePositionEnum.CB: 2,
                AthletePositionEnum.FS: 1,
                AthletePositionEnum.SS: 1,
            },
            uid="form-3",
        )

        defensive_positions = {
            AthletePositionEnum.EDGE,
            AthletePositionEnum.DT,
            AthletePositionEnum.LB,
            AthletePositionEnum.CB,
            AthletePositionEnum.FS,
            AthletePositionEnum.SS,
        }

        for pos in formation.position_counts.keys():
            assert pos in defensive_positions

    def test_formation_11_personnel_offensive(self):
        """Test that offensive formations total 11 players."""
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
            uid="form-4",
        )

        total = sum(formation.position_counts.values())
        assert total == 11

    def test_formation_11_personnel_defensive(self):
        """Test that defensive formations total 11 players."""
        formation = Formation(
            name="Nickel",
            position_counts={
                AthletePositionEnum.EDGE: 2,
                AthletePositionEnum.DT: 2,
                AthletePositionEnum.LB: 3,
                AthletePositionEnum.CB: 2,
                AthletePositionEnum.FS: 1,
                AthletePositionEnum.SS: 1,
            },
            uid="form-5",
        )

        total = sum(formation.position_counts.values())
        assert total == 11


class TestPersonnelPackageValidation:
    """Tests for personnel package constraints."""

    def test_personnel_package_offensive(self):
        """Test offensive personnel package."""
        personnel = PersonnelPackage(
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers-1",
        )

        assert personnel.name == "11 Personnel"
        assert sum(personnel.counts.values()) == 5

    def test_personnel_package_defensive(self):
        """Test defensive personnel package."""
        personnel = PersonnelPackage(
            name="Nickel",
            counts={
                AthletePositionEnum.EDGE: 2,
                AthletePositionEnum.DT: 2,
                AthletePositionEnum.LB: 3,
                AthletePositionEnum.CB: 2,
                AthletePositionEnum.FS: 1,
                AthletePositionEnum.SS: 1,
            },
            uid="pers-2",
        )

        assert personnel.name == "Nickel"
        total = sum(personnel.counts.values())
        assert total == 11

    def test_personnel_package_multiple_types(self):
        """Test personnel package with multiple player types."""
        personnel = PersonnelPackage(
            name="21 Personnel",
            counts={
                AthletePositionEnum.RB: 2,
                AthletePositionEnum.WR: 1,
                AthletePositionEnum.TE: 1,
            },
            uid="pers-3",
        )

        assert len(personnel.counts) == 3
        assert personnel.counts[AthletePositionEnum.RB] == 2


class TestPlayCallValidation:
    """Tests for play call rules and validation."""

    def test_play_call_offensive_with_subformation(self):
        """Test offensive play call with proper formation hierarchy."""
        parent = Formation(
            name="SB-Parent",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
            uid="form-parent",
        )

        formation = Formation(
            name="SB-Tight",
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
            parent=parent,
            uid="form-sub",
        )

        personnel = PersonnelPackage(
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers",
        )

        play = PlayCall(
            uid="play",
            name="Power Run",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )

        assert play.side == PlaySideEnum.OFFENSE
        assert play.play_type == PlayTypeEnum.RUN

    def test_play_call_pass(self):
        """Test pass play."""
        parent = Formation(
            name="Shotgun-P",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
            uid="form-shotgun-p",
        )

        formation = Formation(
            name="Shotgun-Sub",
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
            parent=parent,
            uid="form-shotgun",
        )

        personnel = PersonnelPackage(
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers-pass",
        )

        play = PlayCall(
            uid="play-pass",
            name="Slant",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )

        assert play.play_type == PlayTypeEnum.PASS
        assert play.side == PlaySideEnum.OFFENSE

    def test_play_call_with_description(self):
        """Test play call with description."""
        parent = Formation(
            name="IForm-P",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 1,
                AthletePositionEnum.TE: 1,
            },
            uid="form-iform-p",
        )

        formation = Formation(
            name="IForm-Sub",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 2,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
                AthletePositionEnum.LT: 1,
                AthletePositionEnum.LG: 1,
                AthletePositionEnum.C: 1,
                AthletePositionEnum.RG: 1,
                AthletePositionEnum.RT: 1,
            },
            parent=parent,
            uid="form-iform",
        )

        personnel = PersonnelPackage(
            name="21 Personnel",
            counts={
                AthletePositionEnum.RB: 2,
                AthletePositionEnum.WR: 1,
                AthletePositionEnum.TE: 1,
            },
            uid="pers-21",
        )

        play = PlayCall(
            uid="play-counter",
            name="Counter",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            description="Inside zone counter to backside",
        )

        assert play.description == "Inside zone counter to backside"


class TestNFLRulesValidation:
    """Tests for NFL-specific rule validation."""

    def test_nfl_first_down_rule(self):
        """Test NFL first down requires 10 yards."""
        rules = NFLRules()
        assert rules.FIRST_DOWN_YARDS == 10

    def test_nfl_field_dimensions(self):
        """Test NFL field dimensions."""
        rules = NFLRules()
        assert rules.FIELD_LENGTH == 100

    def test_nfl_game_time_structure(self):
        """Test NFL game time structure."""
        rules = NFLRules()
        assert rules.MINUTES_PER_QUARTER == 15
        assert rules.QUARTERS_PER_HALF == 2
        assert rules.TIMEOUTS_PER_HALF == 3

    def test_nfl_extra_point_spot(self):
        """Test NFL extra point spot."""
        rules = NFLRules()
        assert rules.EXTRA_POINT_SPOT == 15

    def test_nfl_touchback_spot(self):
        """Test NFL touchback spot."""
        rules = NFLRules()
        assert rules.DEFAULT_TOUCHBACK_SPOT == 20

    def test_nfl_scoring_values(self):
        """Test NFL scoring point values."""
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.TOUCHDOWN] == 6
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.FIELD_GOAL] == 3
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.SAFETY] == 2
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.EXTRA_POINT_KICK] == 1
        assert NFLRules.SCORING_VALUES[ScoringTypeEnum.EXTRA_POINT_TWO_POINT] == 2


class TestTeamRosterValidation:
    """Tests for team roster and position constraints."""

    def test_team_roster_positions(self):
        """Test team can have athletes in all positions."""
        team = Team(uid="team-1", name="Test Team")

        # Add one athlete of each position
        all_positions = [
            AthletePositionEnum.QB,
            AthletePositionEnum.RB,
            AthletePositionEnum.WR,
            AthletePositionEnum.TE,
            AthletePositionEnum.OLINE,
            AthletePositionEnum.EDGE,
            AthletePositionEnum.DT,
            AthletePositionEnum.LB,
            AthletePositionEnum.CB,
            AthletePositionEnum.FS,
            AthletePositionEnum.SS,
        ]

        for i, pos in enumerate(all_positions):
            athlete = Athlete(
                uid=f"player-{i}",
                first_name=f"Player{i}",
                last_name="Test",
                position=pos,
            )
            team.add_athlete(athlete)

        assert len(team.roster) == len(all_positions)

    def test_team_get_athletes_by_position(self):
        """Test filtering team athletes by position."""
        team = Team(uid="team-1", name="Test Team")

        # Add QBs
        for i in range(2):
            team.add_athlete(
                Athlete(
                    uid=f"qb-{i}",
                    first_name=f"QB{i}",
                    last_name="Test",
                    position=AthletePositionEnum.QB,
                )
            )

        # Add WRs
        for i in range(3):
            team.add_athlete(
                Athlete(
                    uid=f"wr-{i}",
                    first_name=f"WR{i}",
                    last_name="Test",
                    position=AthletePositionEnum.WR,
                )
            )

        qbs = team.get_athletes_by_position(AthletePositionEnum.QB)
        wrs = team.get_athletes_by_position(AthletePositionEnum.WR)

        assert len(qbs) == 2
        assert len(wrs) == 3

    def test_team_roster_with_duplicates(self):
        """Test team roster can have multiple athletes in same position."""
        team = Team(uid="team-1", name="Test Team")

        for i in range(5):
            team.add_athlete(
                Athlete(
                    uid=f"wr-{i}",
                    first_name=f"WR{i}",
                    last_name="Test",
                    position=AthletePositionEnum.WR,
                )
            )

        wrs = team.get_athletes_by_position(AthletePositionEnum.WR)
        assert len(wrs) == 5


class TestRuleConstraints:
    """Tests for rule constraints and enforcement."""

    def test_formation_has_required_structure(self):
        """Test formation requires name and position counts."""
        formation = Formation(
            name="Base",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
            uid="form-1",
        )

        assert formation.name is not None
        assert formation.position_counts is not None
        assert len(formation.position_counts) > 0

    def test_play_call_has_required_fields(self):
        """Test play call requires formation and personnel."""
        parent = Formation(
            name="Base-P",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 1,
            },
            uid="form-base-p",
        )

        formation = Formation(
            name="Base-Sub",
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
            parent=parent,
            uid="form-base",
        )

        personnel = PersonnelPackage(
            name="Pass",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers-pass",
        )

        play = PlayCall(
            uid="play-1",
            name="Test Play",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )

        assert play.formation is not None
        assert play.personnel_package is not None
        assert play.play_type is not None
        assert play.side is not None
