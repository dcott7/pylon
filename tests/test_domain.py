"""Tests for domain layer: Athlete and Team classes.

Domain rules tests (Formation, PersonnelPackage, PlayCall validation) are in test_domain_rules.py.
"""

from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.domain.team import Team


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
