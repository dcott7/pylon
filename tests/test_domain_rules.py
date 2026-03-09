"""Tests for domain rules: NFL rule validation and constraints."""

import pytest

from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team
from pylon.domain.playbook import (
    Formation,
    PersonnelPackage,
    PlayCall,
    Playbook,
    PlayTypeEnum,
    PlaySideEnum,
)
from pylon.domain.rules.nfl import NFLRules
from pylon.state.play_record import ScoringTypeEnum


@pytest.fixture
def parent_formation() -> Formation:
    """Fixture for a parent formation (abstract template)."""
    return Formation(
        name="Parent",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 2,
            AthletePositionEnum.TE: 1,
        },
        uid="parent-fixture",
    )


@pytest.fixture
def basic_offensive_formation(parent_formation: Formation) -> Formation:
    """Fixture for a basic offensive formation with parent used in multiple tests."""
    return Formation(
        name="Singleback",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 3,
            AthletePositionEnum.TE: 1,
            AthletePositionEnum.OLINE: 5,
        },
        parent=parent_formation,
        uid="basic-off-form",
    )


class TestFormationValidation:
    """Tests for formation rules and constraints."""

    def test_formation_position_counts_valid(
        self, basic_offensive_formation: Formation
    ) -> None:
        """Test formation with valid position counts."""
        formation = basic_offensive_formation
        assert formation.name == "Singleback"
        assert formation.positions == list(formation.position_counts.keys())
        assert len(formation.position_counts) == 5

    def test_formation_position_count_method(
        self, basic_offensive_formation: Formation
    ) -> None:
        """Test the position_count method returns correct counts."""
        formation = basic_offensive_formation
        # Test position_count for positions in the formation
        assert formation.position_count(AthletePositionEnum.QB) == 1
        assert formation.position_count(AthletePositionEnum.RB) == 1
        assert formation.position_count(AthletePositionEnum.WR) == 3
        assert formation.position_count(AthletePositionEnum.TE) == 1
        assert formation.position_count(AthletePositionEnum.OLINE) == 5

        # Test position_count for positions NOT in the formation
        assert formation.position_count(AthletePositionEnum.CB) == 0
        assert formation.position_count(AthletePositionEnum.DT) == 0

    def test_formation_has_position_method(
        self, basic_offensive_formation: Formation
    ) -> None:
        """Test the has_position method checks position presence."""
        formation = basic_offensive_formation
        # Test has_position for positions in the formation
        assert formation.has_position(AthletePositionEnum.QB) is True
        assert formation.has_position(AthletePositionEnum.WR) is True
        assert formation.has_position(AthletePositionEnum.TE) is True

        # Test has_position for positions NOT in the formation
        assert formation.has_position(AthletePositionEnum.CB) is False

    def test_formation_has_tag_and_add_tag(self) -> None:
        """Test the has_tag method and add_tag functionality."""
        formation = Formation(
            name="Spread",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.WR: 4,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.OLINE: 5,
            },
            tags=["passing", "spread"],
            uid="form-with-tags",
        )
        # Test has_tag for existing tags
        assert formation.has_tag("passing") is True
        assert formation.has_tag("spread") is True

        # Test has_tag for non-existing tags
        assert formation.has_tag("running") is False

        # Test add_tag functionality
        formation.add_tag("no-huddle")
        assert formation.has_tag("no-huddle") is True

        # Test adding duplicate tag doesn't create duplicates
        formation.add_tag("passing")
        assert formation.tags.count("passing") == 1

    def test_formation_is_subformation_of(self) -> None:
        """Test the is_subformation_of method for hierarchy checking."""
        grandparent = Formation(
            name="Base",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
            },
            uid="gp",
        )

        parent = Formation(
            name="Singleback",
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
            parent=grandparent,
            uid="p",
        )

        child = Formation(
            name="Singleback Tight",
            position_counts={
                AthletePositionEnum.QB: 1,
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 2,
                AthletePositionEnum.TE: 2,
                AthletePositionEnum.LT: 1,
                AthletePositionEnum.LG: 1,
                AthletePositionEnum.C: 1,
                AthletePositionEnum.RG: 1,
                AthletePositionEnum.RT: 1,
            },
            parent=parent,
            uid="c",
        )

        # Test direct parent relationship
        assert child.is_subformation_of(parent) is True

        # Test grandparent relationship
        assert child.is_subformation_of(grandparent) is True

        # Test non-parent relationship
        unrelated = Formation(
            name="Unrelated",
            position_counts={AthletePositionEnum.QB: 1},
            uid="unrel",
        )
        assert child.is_subformation_of(unrelated) is False

        # Test self is not subformation of self
        assert parent.is_subformation_of(parent) is False

    def test_formation_with_parent(
        self, parent_formation: Formation, basic_offensive_formation: Formation
    ) -> None:
        """Test formation with parent formation."""
        parent = parent_formation
        child = basic_offensive_formation

        assert child.parent == parent
        assert child.name == "Singleback"

    def test_formation_offensive_positions(
        self, basic_offensive_formation: Formation
    ) -> None:
        """Test formation with offensive positions."""
        formation = basic_offensive_formation

        offensive_positions = {
            AthletePositionEnum.QB,
            AthletePositionEnum.RB,
            AthletePositionEnum.WR,
            AthletePositionEnum.TE,
            AthletePositionEnum.OLINE,
        }

        for pos in formation.position_counts.keys():
            assert pos in offensive_positions

    def test_formation_defensive_positions(self) -> None:
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

    def test_formation_11_personnel_offensive(
        self, basic_offensive_formation: Formation
    ) -> None:
        """Test that offensive formations total 11 players."""
        formation = basic_offensive_formation

        total = sum(formation.position_counts.values())
        assert total == 11

    def test_formation_11_personnel_defensive(self) -> None:
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

    def test_personnel_package_offensive(self) -> None:
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

    def test_personnel_package_defensive(self) -> None:
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

    def test_personnel_package_multiple_types(self) -> None:
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

    def test_play_call_offensive_with_subformation(self) -> None:
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

    def test_play_call_pass(self) -> None:
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

    def test_play_call_with_description(self) -> None:
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

    def test_nfl_first_down_rule(self) -> None:
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

    def test_team_get_athlete_by_uid(self):
        """Test getting athletes by UID."""
        team = Team(uid="team-2", name="Test Team")

        qb = Athlete(
            uid="qb-001",
            first_name="Tom",
            last_name="Brady",
            position=AthletePositionEnum.QB,
        )
        wr = Athlete(
            uid="wr-001",
            first_name="Jerry",
            last_name="Rice",
            position=AthletePositionEnum.WR,
        )

        team.add_athlete(qb)
        team.add_athlete(wr)

        # Test finding existing athletes
        found_qb = team.get_athlete_by_uid("qb-001")
        assert found_qb is not None
        assert found_qb.uid == "qb-001"
        assert found_qb.first_name == "Tom"

        found_wr = team.get_athlete_by_uid("wr-001")
        assert found_wr is not None
        assert found_wr.position == AthletePositionEnum.WR

        # Test non-existing athlete
        not_found = team.get_athlete_by_uid("rb-999")
        assert not_found is None

    def test_team_add_play_template(self):
        """Test adding play templates to the correct playbook."""
        team = Team(uid="team-3", name="Test Team")

        # Create offensive play
        off_parent = Formation(
            name="Off-P",
            position_counts={AthletePositionEnum.QB: 1, AthletePositionEnum.RB: 1},
            uid="off-p",
        )
        off_formation = Formation(
            name="Off-Sub",
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
            parent=off_parent,
            uid="off-sub",
        )
        off_personnel = PersonnelPackage(
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="off-pers",
        )
        off_play = PlayCall(
            uid="off-play",
            name="Power Run",
            play_type=PlayTypeEnum.RUN,
            formation=off_formation,
            personnel_package=off_personnel,
            side=PlaySideEnum.OFFENSE,
        )

        # Create defensive play
        def_parent = Formation(
            name="Def-P",
            position_counts={AthletePositionEnum.CB: 2},
            uid="def-p",
        )
        def_formation = Formation(
            name="Def-Sub",
            position_counts={
                AthletePositionEnum.EDGE: 2,
                AthletePositionEnum.DT: 2,
                AthletePositionEnum.LB: 3,
                AthletePositionEnum.CB: 2,
                AthletePositionEnum.FS: 1,
                AthletePositionEnum.SS: 1,
            },
            parent=def_parent,
            uid="def-sub",
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
            uid="def-pers",
        )
        def_play = PlayCall(
            uid="def-play",
            name="Cover 2",
            play_type=PlayTypeEnum.DEFENSIVE_PLAY,
            formation=def_formation,
            personnel_package=def_personnel,
            side=PlaySideEnum.DEFENSE,
        )

        # Add plays to team
        team.add_play_template(off_play)
        team.add_play_template(def_play)

        # Verify plays were added to correct playbooks
        assert len(team.off_playbook) == 1
        assert len(team.def_playbook) == 1
        assert team.off_playbook.get_by_uid("off-play") is not None
        assert team.def_playbook.get_by_uid("def-play") is not None

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

    def test_playbook_get_by_name(self):
        """Test retrieving plays by name."""
        playbook = Playbook(uid="pb-1")

        # Create multiple plays with same and different names
        parent = Formation(
            name="P",
            position_counts={AthletePositionEnum.QB: 1},
            uid="p1",
        )
        formation = Formation(
            name="Sub",
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
            uid="s1",
        )
        personnel = PersonnelPackage(
            name="11",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers1",
        )

        play1 = PlayCall(
            uid="p1",
            name="Power",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )
        play2 = PlayCall(
            uid="p2",
            name="Power",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )
        play3 = PlayCall(
            uid="p3",
            name="Slant",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )

        playbook.add_play(play1)
        playbook.add_play(play2)
        playbook.add_play(play3)

        # Test getting by name
        power_plays = playbook.get_by_name("Power")
        assert len(power_plays) == 2

        slant_plays = playbook.get_by_name("Slant")
        assert len(slant_plays) == 1

        nonexistent = playbook.get_by_name("Nonexistent")
        assert len(nonexistent) == 0

    def test_playbook_get_by_uid(self):
        """Test retrieving plays by UID."""
        playbook = Playbook(uid="pb-2")

        parent = Formation(
            name="P2",
            position_counts={AthletePositionEnum.QB: 1},
            uid="p2",
        )
        formation = Formation(
            name="Sub2",
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
            uid="s2",
        )
        personnel = PersonnelPackage(
            name="11",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers2",
        )

        play = PlayCall(
            uid="unique-play-123",
            name="Counter",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )

        playbook.add_play(play)

        # Test getting by UID
        found = playbook.get_by_uid("unique-play-123")
        assert found is not None
        assert found.uid == "unique-play-123"
        assert found.name == "Counter"

        # Test non-existing UID
        not_found = playbook.get_by_uid("nonexistent-uid")
        assert not_found is None

    def test_playbook_get_by_tag(self):
        """Test retrieving plays by tag."""
        playbook = Playbook(uid="pb-3")

        parent = Formation(
            name="P3",
            position_counts={AthletePositionEnum.QB: 1},
            uid="p3",
        )
        formation = Formation(
            name="Sub3",
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
            uid="s3",
        )
        personnel = PersonnelPackage(
            name="11",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers3",
        )

        play1 = PlayCall(
            uid="p1-tag",
            name="Quick Slant",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            tags=["quick", "passing"],
        )
        play2 = PlayCall(
            uid="p2-tag",
            name="Deep Post",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            tags=["deep", "passing"],
        )
        play3 = PlayCall(
            uid="p3-tag",
            name="Inside Zone",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            tags=["zone", "running"],
        )

        playbook.add_play(play1)
        playbook.add_play(play2)
        playbook.add_play(play3)

        # Test getting by tag
        passing_plays = playbook.get_by_tag("passing")
        assert len(passing_plays) == 2

        running_plays = playbook.get_by_tag("running")
        assert len(running_plays) == 1

        quick_plays = playbook.get_by_tag("quick")
        assert len(quick_plays) == 1

    def test_playbook_get_by_type(self):
        """Test retrieving plays by play type."""
        playbook = Playbook(uid="pb-4")

        parent = Formation(
            name="P4",
            position_counts={AthletePositionEnum.QB: 1},
            uid="p4",
        )
        formation = Formation(
            name="Sub4",
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
            uid="s4",
        )
        personnel = PersonnelPackage(
            name="11",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers4",
        )

        run1 = PlayCall(
            uid="run1",
            name="Power",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )
        run2 = PlayCall(
            uid="run2",
            name="Counter",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )
        pass_play = PlayCall(
            uid="pass1",
            name="Verticals",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )

        playbook.add_play(run1)
        playbook.add_play(run2)
        playbook.add_play(pass_play)

        # Test getting by type
        run_plays = playbook.get_by_type(PlayTypeEnum.RUN)
        assert len(run_plays) == 2

        pass_plays = playbook.get_by_type(PlayTypeEnum.PASS)
        assert len(pass_plays) == 1

    def test_playbook_len(self):
        """Test playbook length."""
        playbook = Playbook(uid="pb-5")

        assert len(playbook) == 0

        parent = Formation(
            name="P5",
            position_counts={AthletePositionEnum.QB: 1},
            uid="p5",
        )
        formation = Formation(
            name="Sub5",
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
            uid="s5",
        )
        personnel = PersonnelPackage(
            name="11",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers5",
        )

        for i in range(5):
            play = PlayCall(
                uid=f"play-{i}",
                name=f"Play {i}",
                play_type=PlayTypeEnum.RUN,
                formation=formation,
                personnel_package=personnel,
                side=PlaySideEnum.OFFENSE,
            )
            playbook.add_play(play)

        assert len(playbook) == 5

    def test_play_call_add_tag(self):
        """Test adding tags to a play call."""
        parent = Formation(
            name="P6",
            position_counts={AthletePositionEnum.QB: 1},
            uid="p6",
        )
        formation = Formation(
            name="Sub6",
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
            uid="s6",
        )
        personnel = PersonnelPackage(
            name="11",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
            uid="pers6",
        )

        play = PlayCall(
            uid="play-tag-test",
            name="Test Play",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            tags=["initial-tag"],
        )

        # Test initial tags
        assert "initial-tag" in play.tags
        assert len(play.tags) == 1

        # Test adding new tag
        play.add_tag("quick")
        assert "quick" in play.tags
        assert len(play.tags) == 2

        # Test adding duplicate tag (should not add again)
        play.add_tag("quick")
        assert play.tags.count("quick") == 1
        assert len(play.tags) == 2

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
