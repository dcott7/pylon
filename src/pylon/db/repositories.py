"""
Data access layer (repositories) for Pylon database.

Repositories handle conversion between domain objects (from pylon.domain)
and ORM objects (from schema), and provide persistence operations.
"""

import logging
from typing import List

from ..domain.athlete import Athlete as DomainAthlete
from ..domain.team import Team as DomainTeam
from .database import DatabaseManager
from .schema import Athlete as OrmAthlete
from .schema import Team as OrmTeam

logger = logging.getLogger(__name__)


class TeamRepository:
    """
    Repository for Team dimension data.

    Converts domain Team objects to ORM Team objects and handles persistence.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the TeamRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(self, domain_team: DomainTeam) -> OrmTeam:
        """
        Convert a domain Team to an ORM Team.

        Args:
            domain_team: Domain Team object.

        Returns:
            ORM Team object (not yet persisted).
        """
        orm_team = OrmTeam(
            id=domain_team.uid,
            name=domain_team.name,
            abbreviation=None,  # Domain team doesn't have abbreviation yet
        )
        return orm_team

    def save(self, domain_team: DomainTeam) -> OrmTeam:
        """
        Convert and persist a domain Team.

        Args:
            domain_team: Domain Team object.

        Returns:
            Persisted ORM Team object.
        """
        orm_team = self.to_orm(domain_team)
        self.db.insert_dimension_data(orm_team)
        logger.info(f"Persisted team: {orm_team.name} (id={orm_team.id})")
        return orm_team

    def save_batch(self, domain_teams: List[DomainTeam]) -> List[OrmTeam]:
        """
        Convert and persist multiple domain Teams.

        Args:
            domain_teams: List of domain Team objects.

        Returns:
            List of persisted ORM Team objects.
        """
        orm_teams = [self.to_orm(team) for team in domain_teams]
        self.db.insert_dimension_data(*orm_teams)
        logger.info(f"Persisted {len(orm_teams)} team(s).")
        return orm_teams


class AthleteRepository:
    """
    Repository for Athlete dimension data.

    Converts domain Athlete objects to ORM Athlete objects and handles persistence.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the AthleteRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(self, domain_athlete: DomainAthlete) -> OrmAthlete:
        """
        Convert a domain Athlete to an ORM Athlete.

        Args:
            domain_athlete: Domain Athlete object.

        Returns:
            ORM Athlete object (not yet persisted).
        """
        orm_athlete = OrmAthlete(
            id=domain_athlete.uid,
            first_name=domain_athlete.first_name,
            last_name=domain_athlete.last_name,
            position=domain_athlete.position,
        )
        return orm_athlete

    def save(self, domain_athlete: DomainAthlete) -> OrmAthlete:
        """
        Convert and persist a domain Athlete.

        Args:
            domain_athlete: Domain Athlete object.

        Returns:
            Persisted ORM Athlete object.
        """
        orm_athlete = self.to_orm(domain_athlete)
        self.db.insert_dimension_data(orm_athlete)
        logger.info(
            f"Persisted athlete: {orm_athlete.first_name} {orm_athlete.last_name} (id={orm_athlete.id})"
        )
        return orm_athlete

    def save_batch(self, domain_athletes: List[DomainAthlete]) -> List[OrmAthlete]:
        """
        Convert and persist multiple domain Athletes.

        Args:
            domain_athletes: List of domain Athlete objects.

        Returns:
            List of persisted ORM Athlete objects.
        """
        orm_athletes = [self.to_orm(athlete) for athlete in domain_athletes]
        self.db.insert_dimension_data(*orm_athletes)
        logger.info(f"Persisted {len(orm_athletes)} athlete(s).")
        return orm_athletes


class DimensionRepository:
    """
    Facade for all dimension repositories.

    Provides a unified interface for persisting dimension data.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize DimensionRepository with all sub-repositories.

        Args:
            db_manager: DatabaseManager instance.
        """
        self.teams = TeamRepository(db_manager)
        self.athletes = AthleteRepository(db_manager)

    def persist_game_dimensions(
        self,
        home_team: DomainTeam,
        away_team: DomainTeam,
    ) -> None:
        """
        Persist all dimension data for a game (teams and their rosters).

        Args:
            home_team: Home team domain object.
            away_team: Away team domain object.
        """
        logger.info("Persisting game dimension data...")

        # Persist teams
        self.teams.save_batch([home_team, away_team])

        # Persist all athletes from both rosters
        all_athletes = home_team.roster + away_team.roster
        if all_athletes:
            self.athletes.save_batch(all_athletes)

        logger.info("Game dimension data persisted successfully.")
