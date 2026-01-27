"""
Data access layer (repositories) for Pylon database.

Repositories handle conversion between domain objects (from pylon.domain)
and ORM objects (from schema), and provide persistence operations.
"""

import logging
from typing import Dict, List

from ..domain.athlete import Athlete as DomainAthlete
from ..domain.team import Team as DomainTeam
from ..domain.playbook import Formation as DomainFormation
from ..domain.playbook import PersonnelPackage as DomainPersonnel
from ..domain.playbook import PlayCall as DomainPlayCall
from .database import DatabaseManager
from .schema import Athlete as OrmAthlete
from .schema import Team as OrmTeam
from .schema import Formation as OrmFormation
from .schema import Personnel as OrmPersonnel
from .schema import Play as OrmPlay

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


class FormationRepository:
    """
    Repository for Formation dimension data.

    Converts domain Formation objects to ORM Formation objects and handles persistence.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the FormationRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(
        self, domain_formation: DomainFormation, parent_id: str | None = None
    ) -> OrmFormation:
        """
        Convert a domain Formation to an ORM Formation.

        Args:
            domain_formation: Domain Formation object.
            parent_id: Optional parent formation ID for sub-formations.

        Returns:
            ORM Formation object (not yet persisted).
        """
        orm_formation = OrmFormation(
            id=domain_formation.uid,
            name=domain_formation.name,
            parent_formation_id=parent_id,
        )
        return orm_formation

    def save(
        self, domain_formation: DomainFormation, parent_id: str | None = None
    ) -> OrmFormation:
        """
        Convert and persist a domain Formation.

        Args:
            domain_formation: Domain Formation object.
            parent_id: Optional parent formation ID.

        Returns:
            Persisted ORM Formation object.
        """
        orm_formation = self.to_orm(domain_formation, parent_id)
        self.db.insert_dimension_data(orm_formation)
        logger.info(
            f"Persisted formation: {orm_formation.name} (id={orm_formation.id})"
        )
        return orm_formation

    def save_batch(
        self, domain_formations: List[DomainFormation]
    ) -> List[OrmFormation]:
        """
        Convert and persist multiple domain Formations.

        Args:
            domain_formations: List of domain Formation objects.

        Returns:
            List of persisted ORM Formation objects.
        """
        orm_formations = [self.to_orm(formation) for formation in domain_formations]
        self.db.insert_dimension_data(*orm_formations)
        logger.info(f"Persisted {len(orm_formations)} formation(s).")
        return orm_formations


class PersonnelRepository:
    """
    Repository for Personnel dimension data.

    Converts domain Personnel objects to ORM Personnel objects and handles persistence.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the PersonnelRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(self, domain_personnel: DomainPersonnel) -> OrmPersonnel:
        """
        Convert a domain Personnel to an ORM Personnel.

        Args:
            domain_personnel: Domain Personnel object.

        Returns:
            ORM Personnel object (not yet persisted).
        """
        orm_personnel = OrmPersonnel(
            id=domain_personnel.uid, name=domain_personnel.name
        )
        return orm_personnel

    def save(self, domain_personnel: DomainPersonnel) -> OrmPersonnel:
        """
        Convert and persist a domain Personnel.

        Args:
            domain_personnel: Domain Personnel object.

        Returns:
            Persisted ORM Personnel object.
        """
        orm_personnel = self.to_orm(domain_personnel)
        self.db.insert_dimension_data(orm_personnel)
        logger.info(
            f"Persisted personnel: {orm_personnel.name} (id={orm_personnel.id})"
        )
        return orm_personnel

    def save_batch(
        self, domain_personnels: List[DomainPersonnel]
    ) -> List[OrmPersonnel]:
        """
        Convert and persist multiple domain Personnel.

        Args:
            domain_personnels: List of domain Personnel objects.

        Returns:
            List of persisted ORM Personnel objects.
        """
        orm_personnels = [self.to_orm(personnel) for personnel in domain_personnels]
        self.db.insert_dimension_data(*orm_personnels)
        logger.info(f"Persisted {len(orm_personnels)} personnel(s).")
        return orm_personnels


class PlayRepository:
    """
    Repository for Play dimension data.

    Converts domain Play/PlayCall objects to ORM Play objects and handles persistence.
    Plays are linked to their owning team and reference formations/personnel.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the PlayRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(
        self,
        domain_play: DomainPlayCall,
        team_id: str,
        formation_id: str | None = None,
        personnel_id: str | None = None,
    ) -> OrmPlay:
        """
        Convert a domain PlayCall to an ORM Play.

        Args:
            domain_play: Domain PlayCall object.
            team_id: Team UID that owns this play.
            formation_id: Optional Formation ID reference.
            personnel_id: Optional Personnel ID reference.

        Returns:
            ORM Play object (not yet persisted).
        """
        orm_play = OrmPlay(
            id=domain_play.uid,
            name=domain_play.name,
            play_type=domain_play.play_type,
            side=domain_play.side,
            team_id=team_id,
            formation_id=formation_id,
            personnel_id=personnel_id,
            description=domain_play.description,
        )
        return orm_play

    def save(
        self,
        domain_play: DomainPlayCall,
        team_id: str,
        formation_id: str | None = None,
        personnel_id: str | None = None,
    ) -> OrmPlay:
        """
        Convert and persist a domain PlayCall.

        Args:
            domain_play: Domain PlayCall object.
            team_id: Team UID that owns this play.
            formation_id: Optional Formation ID reference.
            personnel_id: Optional Personnel ID reference.

        Returns:
            Persisted ORM Play object.
        """
        orm_play = self.to_orm(domain_play, team_id, formation_id, personnel_id)
        self.db.insert_dimension_data(orm_play)
        logger.info(f"Persisted play: {orm_play.name} (id={orm_play.id})")
        return orm_play

    def save_batch(
        self,
        domain_plays: List[DomainPlayCall],
        team_id: str,
        formation_ids: dict[str, str] | None = None,
        personnel_ids: dict[str, str] | None = None,
    ) -> List[OrmPlay]:
        """
        Convert and persist multiple domain PlayCalls.

        Args:
            domain_plays: List of domain PlayCall objects.
            team_id: Team UID that owns these plays.
            formation_ids: Optional mapping of play UID -> formation ID.
            personnel_ids: Optional mapping of play UID -> personnel ID.

        Returns:
            List of persisted ORM Play objects.
        """
        formation_ids = formation_ids or {}
        personnel_ids = personnel_ids or {}

        orm_plays = [
            self.to_orm(
                play,
                team_id,
                formation_ids.get(play.uid),
                personnel_ids.get(play.uid),
            )
            for play in domain_plays
        ]
        self.db.insert_dimension_data(*orm_plays)
        logger.info(f"Persisted {len(orm_plays)} play(s).")
        return orm_plays


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
        self.db = db_manager
        self.teams = TeamRepository(db_manager)
        self.athletes = AthleteRepository(db_manager)
        self.formations = FormationRepository(db_manager)
        self.personnel = PersonnelRepository(db_manager)
        self.plays = PlayRepository(db_manager)

    def persist_game_dimensions(
        self,
        home_team: DomainTeam,
        away_team: DomainTeam,
    ) -> None:
        """
        Persist all dimension data for a game.

        This includes:
        - Teams (home and away)
        - Athletes (all players from both rosters)
        - Formations (unique formations from all plays)
        - Personnel (unique personnel from all plays)
        - Plays (all play templates from both teams' playbooks)

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

        # Extract and persist formations, personnel, and plays from playbooks
        for team in [home_team, away_team]:
            # Collect plays from both offensive and defensive playbooks
            off_plays = team.off_playbook.plays if team.off_playbook else []
            def_plays = team.def_playbook.plays if team.def_playbook else []
            all_plays = off_plays + def_plays

            if not all_plays:
                continue

            # Extract unique formations from plays (if they have formations)
            formations: List[DomainFormation] = []
            formation_map: Dict[str, str] = {}  # play_uid -> formation_uid
            for play in all_plays:
                if hasattr(play, "formation") and play.formation:
                    formations.append(play.formation)
                    formation_map[play.uid] = play.formation.uid

            if formations:
                # Deduplicate formations by UID
                unique_formations = {f.uid: f for f in formations}.values()
                self.formations.save_batch(list(unique_formations))

            # Extract unique personnel from plays (if they have personnel)
            personnels: List[DomainPersonnel] = []
            personnel_map: Dict[str, str] = {}  # play_uid -> personnel_uid
            for play in all_plays:
                if hasattr(play, "personnel") and play.personnel_package:
                    personnels.append(play.personnel_package)
                    personnel_map[play.uid] = play.personnel_package.uid

            if personnels:
                # Deduplicate personnel by UID
                unique_personnels = {p.uid: p for p in personnels}.values()
                self.personnel.save_batch(list(unique_personnels))

            # Persist plays (with references to formations and personnel)
            self.plays.save_batch(all_plays, team.uid, formation_map, personnel_map)

        logger.info("Game dimension data persisted successfully.")
