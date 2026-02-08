"""Tests for domain layer: Team, Athlete, and Playbook classes."""

from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team
from pylon.domain.playbook import (
    Formation,
    PersonnelPackage,
    PlayCall,
    PlayTypeEnum,
    PlaySideEnum,
)


def create_offense_subformation() -> Formation:
    parent = Formation(
        name="Singleback",
        position_counts={
            AthletePositionEnum.QB: 1,
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 2,
            AthletePositionEnum.TE: 1,
        },
        uid="form-parent-off",
    )
    return Formation(
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
        parent=parent,
        uid="form-sub-off",
    )


def create_defense_subformation() -> Formation:
    parent = Formation(
        name="Nickel",
        position_counts={
            AthletePositionEnum.EDGE: 1,
            AthletePositionEnum.DT: 1,
            AthletePositionEnum.LB: 2,
            AthletePositionEnum.CB: 2,
        },
        uid="form-parent-def",
    )
    return Formation(
        name="Nickel 4-2-5",
        position_counts={
            AthletePositionEnum.EDGE: 2,
            AthletePositionEnum.DT: 2,
            AthletePositionEnum.LB: 3,
            AthletePositionEnum.CB: 2,
            AthletePositionEnum.FS: 1,
            AthletePositionEnum.SS: 1,
        },
        parent=parent,
        uid="form-sub-def",
    )


def create_offense_personnel() -> PersonnelPackage:
    return PersonnelPackage(
        name="11 Personnel",
        counts={
            AthletePositionEnum.RB: 1,
            AthletePositionEnum.WR: 3,
            AthletePositionEnum.TE: 1,
        },
        uid="pers-11",
    )


def create_defense_personnel() -> PersonnelPackage:
    return PersonnelPackage(
        name="Nickel",
        counts={
            AthletePositionEnum.EDGE: 2,
            AthletePositionEnum.DT: 2,
            AthletePositionEnum.LB: 3,
            AthletePositionEnum.CB: 2,
            AthletePositionEnum.FS: 1,
            AthletePositionEnum.SS: 1,
        },
        uid="pers-nickel",
    )


class TestAthlete:
    """Tests for Athlete class."""

    def test_create_athlete(self) -> None:
        """Test basic athlete creation."""
        athlete = Athlete(
            uid="player-1",
            first_name="Patrick",
            last_name="Mahomes",
            position=AthletePositionEnum.QB,
        )
        assert athlete.uid == "player-1"
        assert athlete.first_name == "Patrick"
        assert athlete.last_name == "Mahomes"
        assert athlete.position == AthletePositionEnum.QB

    def test_athlete_full_name(self) -> None:
        """Test athlete full name property."""
        athlete = Athlete(
            uid="player-1",
            first_name="Travis",
            last_name="Kelce",
            position=AthletePositionEnum.TE,
        )
        assert athlete.full_name == "Travis Kelce"


class TestTeam:
    """Tests for Team class."""

    def test_create_team(self) -> None:
        """Test basic team creation."""
        team = Team(uid="team-1", name="Kansas City Chiefs")
        assert team.uid == "team-1"
        assert team.name == "Kansas City Chiefs"
        assert len(team.roster) == 0

    def test_add_athlete_to_roster(self) -> None:
        """Test adding athletes to team roster."""
        team = Team(uid="team-1", name="Chiefs")
        qb = Athlete(
            uid="qb-1",
            first_name="Patrick",
            last_name="Mahomes",
            position=AthletePositionEnum.QB,
        )
        rb = Athlete(
            uid="rb-1",
            first_name="Isiah",
            last_name="Pacheco",
            position=AthletePositionEnum.RB,
        )

        team.add_athlete(qb)
        team.add_athlete(rb)

        assert len(team.roster) == 2
        assert qb in team.roster
        assert rb in team.roster

    def test_get_athletes_by_position(self) -> None:
        """Test filtering athletes by position."""
        team = Team(uid="team-1", name="Chiefs")
        qb1 = Athlete(
            uid="qb-1",
            first_name="Patrick",
            last_name="Mahomes",
            position=AthletePositionEnum.QB,
        )
        qb2 = Athlete(
            uid="qb-2",
            first_name="Blaine",
            last_name="Gabbert",
            position=AthletePositionEnum.QB,
        )
        wr = Athlete(
            uid="wr-1",
            first_name="Travis",
            last_name="Kelce",
            position=AthletePositionEnum.TE,
        )

        team.add_athlete(qb1)
        team.add_athlete(qb2)
        team.add_athlete(wr)

        qbs = team.get_athletes_by_position(AthletePositionEnum.QB)
        assert len(qbs) == 2
        assert qb1 in qbs
        assert qb2 in qbs
        assert wr not in qbs


class TestFormation:
    """Tests for Formation class."""

    def test_create_formation(self) -> None:
        """Test basic formation creation."""
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
        assert formation.uid == "form-1"
        assert formation.name == "Singleback"


class TestPersonnelPackage:
    """Tests for PersonnelPackage class."""

    def test_create_personnel_package(self) -> None:
        """Test basic personnel package creation."""
        personnel = PersonnelPackage(
            uid="pers-1",
            name="11 Personnel",
            counts={
                AthletePositionEnum.RB: 1,
                AthletePositionEnum.WR: 3,
                AthletePositionEnum.TE: 1,
            },
        )
        assert personnel.uid == "pers-1"
        assert personnel.name == "11 Personnel"


class TestPlayCall:
    """Tests for PlayCall class."""

    def test_create_offensive_play(self) -> None:
        """Test creating an offensive play call."""
        formation = create_offense_subformation()
        personnel = create_offense_personnel()
        play = PlayCall(
            name="PA Shot Seam",
            play_type=PlayTypeEnum.PASS,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
            uid="play-1",
            description="Play action deep seam route",
        )
        assert play.uid == "play-1"
        assert play.name == "PA Shot Seam"
        assert play.play_type == PlayTypeEnum.PASS
        assert play.side == PlaySideEnum.OFFENSE
        assert play.description == "Play action deep seam route"

    def test_create_defensive_play(self):
        """Test creating a defensive play call."""
        formation = create_defense_subformation()
        personnel = create_defense_personnel()
        play = PlayCall(
            uid="play-2",
            name="Cover 2",
            play_type=PlayTypeEnum.DEFENSIVE_PLAY,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.DEFENSE,
            description="Two deep safeties zone coverage",
        )
        assert play.uid == "play-2"
        assert play.name == "Cover 2"
        assert play.play_type == PlayTypeEnum.DEFENSIVE_PLAY
        assert play.side == PlaySideEnum.DEFENSE

    def test_create_run_play(self):
        """Test creating a run play."""
        formation = create_offense_subformation()
        personnel = create_offense_personnel()
        play = PlayCall(
            uid="play-3",
            name="Inside Zone",
            play_type=PlayTypeEnum.RUN,
            formation=formation,
            personnel_package=personnel,
            side=PlaySideEnum.OFFENSE,
        )
        assert play.play_type == PlayTypeEnum.RUN
        assert play.side == PlaySideEnum.OFFENSE
