"""
Data access layer (repositories) for Pylon database.

Repositories handle conversion between domain objects (from pylon.domain)
and ORM objects (from schema), and provide persistence operations.
"""

import logging
from typing import TYPE_CHECKING, Dict, List
import uuid

from ..domain.athlete import Athlete as DomainAthlete
from ..domain.athlete import AthletePositionEnum
from ..state.drive_record import DriveRecord
from ..state.game_state import GameState
from ..state.play_record import PlayRecord, PlayParticipantType
from .database import DatabaseManager
from .schema import Athlete as OrmAthlete
from .schema import Team as OrmTeam
from .schema import Formation as OrmFormation
from .schema import Personnel as OrmPersonnel
from .schema import PlayCall as OrmPlayCall
from .schema import Experiment as OrmExperiment
from .schema import Game as OrmGame
from .schema import Drive as OrmDrive
from .schema import Play as OrmPlay
from .schema import PlayPersonnelAssignment as OrmPlayPersonnelAssignment
from .schema import PlayParticipant as OrmPlayParticipant
from .schema import team_roster

if TYPE_CHECKING:
    from ..output.types import (
        AthleteOutputPayload,
        FormationOutputPayload,
        PersonnelOutputPayload,
        PlayCallOutputPayload,
        TeamOutputPayload,
    )

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

    def to_orm(self, team_output: "TeamOutputPayload") -> OrmTeam:
        """
        Convert a domain Team to an ORM Team.

        Args:
            team_output: Team output payload.

        Returns:
            ORM Team object (not yet persisted).
        """
        orm_team = OrmTeam(
            id=team_output["uid"],
            name=team_output["name"],
            abbreviation=None,  # Domain team doesn't have abbreviation yet
        )
        return orm_team

    def save(self, team_output: "TeamOutputPayload") -> OrmTeam:
        """
        Convert and persist a team output payload.

        Args:
            team_output: Team output payload.

        Returns:
            Persisted ORM Team object.
        """
        orm_team = self.to_orm(team_output)
        self.db.insert_dimension_data(orm_team)
        logger.info(f"Persisted team: {orm_team.name} (id={orm_team.id})")
        return orm_team

    def save_batch(self, team_outputs: List["TeamOutputPayload"]) -> List[OrmTeam]:
        """
        Convert and persist multiple team output payloads.

        Args:
            team_outputs: List of team output payloads.

        Returns:
            List of persisted ORM Team objects.
        """
        orm_teams = [self.to_orm(team) for team in team_outputs]
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

    def to_orm(self, athlete_output: "AthleteOutputPayload") -> OrmAthlete:
        """
        Convert a domain Athlete to an ORM Athlete.

        Args:
            athlete_output: Athlete output payload.

        Returns:
            ORM Athlete object (not yet persisted).
        """
        orm_athlete = OrmAthlete(
            id=athlete_output["uid"],
            first_name=athlete_output["first_name"],
            last_name=athlete_output["last_name"],
            position=athlete_output["position"],
        )
        return orm_athlete

    def save(self, athlete_output: "AthleteOutputPayload") -> OrmAthlete:
        """
        Convert and persist an athlete output payload.

        Args:
            athlete_output: Athlete output payload.

        Returns:
            Persisted ORM Athlete object.
        """
        orm_athlete = self.to_orm(athlete_output)
        self.db.insert_dimension_data(orm_athlete)
        logger.info(
            f"Persisted athlete: {orm_athlete.first_name} {orm_athlete.last_name} (id={orm_athlete.id})"
        )
        return orm_athlete

    def save_batch(
        self, athlete_outputs: List["AthleteOutputPayload"]
    ) -> List[OrmAthlete]:
        """
        Convert and persist multiple athlete output payloads.

        Args:
            athlete_outputs: List of athlete output payloads.

        Returns:
            List of persisted ORM Athlete objects.
        """
        orm_athletes = [self.to_orm(athlete) for athlete in athlete_outputs]
        self.db.insert_dimension_data(*orm_athletes)
        logger.info(f"Persisted {len(orm_athletes)} athlete(s).")
        return orm_athletes


class TeamRosterRepository:
    """Repository for team-athlete association table persistence."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def save_batch(self, team_outputs: List["TeamOutputPayload"]) -> None:
        """Persist team-to-athlete mappings in the team_roster association table."""
        team_roster_rows: List[Dict[str, str]] = []

        for team in team_outputs:
            for athlete in team["athletes"]:
                team_roster_rows.append(
                    {"team_id": team["uid"], "athlete_id": athlete["uid"]}
                )

        if not team_roster_rows:
            return

        self.db.insert_rows(
            table=team_roster,
            rows=team_roster_rows,
            label="team_roster association",
        )


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
        self,
        formation_output: "FormationOutputPayload",
        parent_id: str | None = None,
    ) -> OrmFormation:
        """
        Convert a Formation payload to an ORM Formation.

        Args:
            formation_output: Formation output payload.
            parent_id: Optional parent formation ID for sub-formations.

        Returns:
            ORM Formation object (not yet persisted).
        """
        orm_formation = OrmFormation(
            id=formation_output["uid"],
            name=formation_output["name"],
            parent_formation_id=parent_id,
        )
        return orm_formation

    def save(
        self,
        formation_output: "FormationOutputPayload",
        parent_id: str | None = None,
    ) -> OrmFormation:
        """
        Convert and persist a Formation payload.

        Args:
            formation_output: Formation object.
            parent_id: Optional parent formation ID.

        Returns:
            Persisted ORM Formation object.
        """
        orm_formation = self.to_orm(formation_output, parent_id)
        self.db.insert_dimension_data(orm_formation)
        logger.info(
            f"Persisted formation: {orm_formation.name} (id={orm_formation.id})"
        )
        return orm_formation

    def save_batch(
        self, formation_outputs: List["FormationOutputPayload"]
    ) -> List[OrmFormation]:
        """
        Convert and persist multiple Formation payloads.

        Duplicates (by ID or name) are silently ignored.

        Args:
            formation_outputs: List of FormationOutputPayload objects.

        Returns:
            List of persisted ORM Formation objects.
        """
        orm_formations = [self.to_orm(formation) for formation in formation_outputs]
        self.db.insert_dimension_data_or_ignore(*orm_formations)
        logger.info(
            f"Persisted {len(orm_formations)} formation(s) (duplicates ignored)."
        )
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

    def to_orm(self, personnel_output: "PersonnelOutputPayload") -> OrmPersonnel:
        """
        Convert a domain Personnel to an ORM Personnel.

        Args:
            personnel_output: Personnel output payload.

        Returns:
            ORM Personnel object (not yet persisted).
        """
        orm_personnel = OrmPersonnel(
            id=personnel_output["uid"], name=personnel_output["name"]
        )
        return orm_personnel

    def save(self, personnel_output: "PersonnelOutputPayload") -> OrmPersonnel:
        """
        Convert and persist a domain Personnel.

        Args:
            personnel_output: Personnel output payload.

        Returns:
            Persisted ORM Personnel object.
        """
        orm_personnel = self.to_orm(personnel_output)
        self.db.insert_dimension_data(orm_personnel)
        logger.info(
            f"Persisted personnel: {orm_personnel.name} (id={orm_personnel.id})"
        )
        return orm_personnel

    def save_batch(
        self, personnel_output: List["PersonnelOutputPayload"]
    ) -> List[OrmPersonnel]:
        """
        Convert and persist multiple domain Personnel.

        Duplicates (by ID) are silently ignored.

        Args:
            personnel_output: List of PersonnelOutputPayload objects.

        Returns:
            List of persisted ORM Personnel objects.
        """
        orm_personnels = [self.to_orm(personnel) for personnel in personnel_output]
        self.db.insert_dimension_data_or_ignore(*orm_personnels)
        logger.info(
            f"Persisted {len(orm_personnels)} personnel(s) (duplicates ignored)."
        )
        return orm_personnels


class PlayCallRepository:
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
        play_output: "PlayCallOutputPayload",
        team_id: str,
        formation_id: str | None = None,
        personnel_id: str | None = None,
    ) -> OrmPlayCall:
        """
        Convert a domain PlayCall to an ORM PlayCall.

        Args:
            play_output: PlayCallOutputPayload object.
            team_id: Team UID that owns this play.
            formation_id: Optional Formation ID reference.
            personnel_id: Optional Personnel ID reference.

        Returns:
            ORM PlayCall object (not yet persisted).
        """
        orm_play_call = OrmPlayCall(
            id=play_output["uid"],
            name=play_output["name"],
            play_type=play_output["play_type"],
            side=play_output["side"],
            team_id=team_id,
            formation_id=formation_id,
            personnel_id=personnel_id,
            description=play_output["description"],
        )
        return orm_play_call

    def save(
        self,
        play_output: "PlayCallOutputPayload",
        team_id: str,
        formation_id: str | None = None,
        personnel_id: str | None = None,
    ) -> OrmPlayCall:
        """
        Convert and persist a PlayCall payload.

        Args:
            play_output: PlayCallOutputPayload object.
            team_id: Team UID that owns this play.
            formation_id: Optional Formation ID reference.
            personnel_id: Optional Personnel ID reference.

        Returns:
            Persisted ORM PlayCall object.
        """
        orm_play_call = self.to_orm(play_output, team_id, formation_id, personnel_id)
        self.db.insert_dimension_data(orm_play_call)
        logger.info(
            f"Persisted play call: {orm_play_call.name} (id={orm_play_call.id})"
        )
        return orm_play_call

    def save_batch(
        self,
        play_output: List["PlayCallOutputPayload"],
        team_id: str,
        formation_ids: Dict[str, str] | None = None,
        personnel_ids: Dict[str, str] | None = None,
    ) -> List[OrmPlayCall]:
        """
        Convert and persist multiple domain PlayCalls.

        Duplicates (by ID) are silently ignored.

        Args:
            play_output: List of PlayCallOutputPayload objects.
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
                formation_ids.get(play["uid"]),
                personnel_ids.get(play["uid"]),
            )
            for play in play_output
        ]
        self.db.insert_dimension_data_or_ignore(*orm_plays)
        logger.info(f"Persisted {len(orm_plays)} play(s) (duplicates ignored).")
        return orm_plays


class ExperimentRepository:
    """
    Repository for Experiment fact data.

    Handles persistence of experiment metadata—simulation runs grouped
    for statistical analysis.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the ExperimentRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def create(
        self,
        name: str,
        num_reps: int,
        base_seed: int,
        description: str | None = None,
        experiment_id: str | None = None,
    ) -> OrmExperiment:
        """
        Create and persist a new experiment.

        Args:
            name: Human-readable experiment name.
            num_reps: Number of replications planned.
            base_seed: Base random seed for deterministic rep generation.
            description: Optional detailed description.
            experiment_id: Optional explicit ID (auto-generated if None).

        Returns:
            Persisted ORM Experiment object.
        """
        orm_experiment = OrmExperiment(
            id=experiment_id or str(uuid.uuid4()),
            name=name,
            description=description,
            num_reps=num_reps,
            base_seed=base_seed,
        )
        self.db.insert_dimension_data(orm_experiment)
        logger.info(
            f"Persisted experiment: {orm_experiment.name} (id={orm_experiment.id})"
        )
        return orm_experiment


class GameRepository:
    """
    Repository for Game fact data.

    Handles persistence of individual game simulation results—one per rep.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the GameRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def create(
        self,
        seed: int,
        home_team_id: str,
        away_team_id: str,
        home_score: int,
        away_score: int,
        winner_id: str | None,
        total_plays: int,
        total_drives: int,
        final_quarter: int,
        experiment_id: str | None = None,
        rep_number: int | None = None,
        duration_seconds: float | None = None,
        game_id: str | None = None,
        status: str = "completed",
    ) -> OrmGame:
        """
        Create and persist a new game result.

        Args:
            seed: Random seed used for this game.
            home_team_id: Home team UID.
            away_team_id: Away team UID.
            home_score: Final home team score.
            away_score: Final away team score.
            winner_id: Winning team UID (None for ties).
            total_plays: Number of plays executed.
            total_drives: Number of drives executed.
            final_quarter: Final quarter when game ended.
            experiment_id: Optional parent experiment reference.
            rep_number: Optional replication number within experiment.
            duration_seconds: Optional execution time.
            game_id: Optional explicit ID (auto-generated if None).
            status: Game status - 'completed' or 'failed'. Defaults to 'completed'.

        Returns:
            Persisted ORM Game object.
        """
        orm_game = OrmGame(
            id=game_id or str(uuid.uuid4()),
            experiment_id=experiment_id,
            rep_number=rep_number,
            seed=seed,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            winner_id=winner_id,
            total_plays=total_plays,
            total_drives=total_drives,
            duration_seconds=duration_seconds,
            final_quarter=final_quarter,
            status=status,
        )
        self.db.insert_dimension_data(orm_game)
        logger.info(
            f"Persisted game: {orm_game.id} (rep={orm_game.rep_number}, score={orm_game.home_score}-{orm_game.away_score})"
        )
        return orm_game

    def save_batch(self, games: List[OrmGame]) -> None:
        """
        Batch persist multiple game results.

        Args:
            games: List of ORM Game objects to persist.
        """
        self.db.insert_dimension_data(*games)
        logger.info(f"Persisted {len(games)} game(s).")


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
        self.team_roster = TeamRosterRepository(db_manager)
        self.formations = FormationRepository(db_manager)
        self.personnel = PersonnelRepository(db_manager)
        self.play_calls = PlayCallRepository(db_manager)

    def persist_game_dimensions(
        self,
        home_team: "TeamOutputPayload",
        away_team: "TeamOutputPayload",
    ) -> None:
        """
        Persist all dimension data for a game.

        This includes:
        - Teams (home and away)
        - Athletes (all players from both rosters)
        - Formations (unique formations from all plays, deduped across both teams by UID)
        - Personnel (unique personnel from all plays, deduped across both teams by UID)
        - Plays (all play templates from both teams' playbooks)

        Args:
            home_team: Home team canonical output payload.
            away_team: Away team canonical output payload.
        """
        logger.info("Persisting game dimension data...")

        # Persist teams
        self.teams.save_batch([home_team, away_team])

        # Persist all athletes from both rosters and associate with their teams
        all_athletes = home_team["athletes"] + away_team["athletes"]
        if all_athletes:
            self.athletes.save_batch(all_athletes)
            self.team_roster.save_batch([home_team, away_team])

        # Collect all formations/personnel globally and plays per team.
        # We dedupe formations/personnel by UID before delegating to repositories.
        all_formations: Dict[str, "FormationOutputPayload"] = {}
        all_personnels: Dict[str, "PersonnelOutputPayload"] = {}
        team_plays: Dict[str, List["PlayCallOutputPayload"]] = {}

        # Process both teams to extract plays, formations, and personnel
        for team in [home_team, away_team]:
            # Collect plays from both offensive and defensive playbooks
            playbooks = team["playbooks"]
            off_plays: List["PlayCallOutputPayload"] = playbooks["offense"]["plays"]
            def_plays: List["PlayCallOutputPayload"] = playbooks["defense"]["plays"]
            all_plays = off_plays + def_plays

            if not all_plays:
                team_plays[team["uid"]] = []
                continue

            team_play_payloads: List["PlayCallOutputPayload"] = []

            # Extract formations and personnel from plays
            for play in all_plays:
                formation = play["formation"]
                personnel = play["personnel_package"]

                # Deduplicate by UID (both teams often share standard formations/personnel).
                if formation["uid"] not in all_formations:
                    all_formations[formation["uid"]] = formation
                if personnel["uid"] not in all_personnels:
                    all_personnels[personnel["uid"]] = personnel

                team_play_payloads.append(play)

            team_plays[team["uid"]] = team_play_payloads

        # Persist deduplicated formations and personnel
        if all_formations:
            self.formations.save_batch(list(all_formations.values()))
        if all_personnels:
            self.personnel.save_batch(list(all_personnels.values()))

        # Persist plays for both teams
        for team in [home_team, away_team]:
            plays = team_plays.get(team["uid"], [])
            if plays:
                formation_ids = {
                    play["uid"]: play["formation"]["uid"] for play in plays
                }
                personnel_ids = {
                    play["uid"]: play["personnel_package"]["uid"] for play in plays
                }
                self.play_calls.save_batch(
                    plays,
                    team["uid"],
                    formation_ids=formation_ids,
                    personnel_ids=personnel_ids,
                )

        logger.info("Game dimension data persisted successfully.")


class DriveRepository:
    """
    Repository for Drive fact data.

    Handles conversion between DriveRecord (execution state) and ORM Drive objects
    and manages persistence of drive execution records.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the DriveRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(self, drive_record: DriveRecord, game_id: str) -> OrmDrive:
        """
        Convert a DriveRecord to an ORM Drive.

        Args:
            drive_record: DriveRecord object from simulation.
            game_id: Parent game ID.

        Returns:
            ORM Drive object (not yet persisted).
        """
        execution_data = drive_record.execution_data
        start = drive_record.start
        end = drive_record.end

        orm_drive = OrmDrive(
            game_id=game_id,
            drive_number=int(drive_record.uid),  # Sequential drive number within game
            offense_team_id=start.pos_team.uid if start.pos_team else None,
            defense_team_id=start.def_team.uid if start.def_team else None,
            # Start snapshot
            start_quarter=start.clock_snapshot.quarter,
            start_time_remaining=start.clock_snapshot.time_remaining,
            start_down=start.possession_snapshot.down,
            start_distance=start.possession_snapshot.distance,
            start_yardline=start.possession_snapshot.yardline,
            # End snapshot
            end_quarter=end.clock_snapshot.quarter,
            end_time_remaining=end.clock_snapshot.time_remaining,
            end_down=end.possession_snapshot.down,
            end_distance=end.possession_snapshot.distance,
            end_yardline=end.possession_snapshot.yardline,
            # Aggregates
            plays_run=len(drive_record.plays),
            yards_gained=execution_data.yards_gained,
            time_elapsed=execution_data.time_elapsed,
            # Results
            result=execution_data.result.value if execution_data.result else "unknown",
            scoring_type=execution_data.scoring_type.value
            if execution_data.scoring_type
            else None,
            scoring_team_id=execution_data.scoring_team.uid
            if execution_data.scoring_team
            else None,
        )
        return orm_drive

    def save(self, drive_record: DriveRecord, game_id: str) -> OrmDrive:
        """
        Convert and persist a single DriveRecord.

        Args:
            drive_record: DriveRecord object.
            game_id: Parent game ID.

        Returns:
            Persisted ORM Drive object.
        """
        orm_drive = self.to_orm(drive_record, game_id)
        self.db.insert_fact_data(orm_drive)
        logger.info(
            f"Persisted drive: {orm_drive.id} (plays={orm_drive.plays_run}, yards={orm_drive.yards_gained})"
        )
        return orm_drive

    def save_batch(
        self, drive_records: List[DriveRecord], game_id: str
    ) -> List[OrmDrive]:
        """
        Convert and persist multiple DriveRecords.

        Args:
            drive_records: List of DriveRecord objects.
            game_id: Parent game ID.

        Returns:
            List of persisted ORM Drive objects.
        """
        orm_drives = [self.to_orm(dr, game_id) for dr in drive_records]
        self.db.insert_fact_data(*orm_drives)
        logger.info(f"Persisted {len(orm_drives)} drive(s).")
        return orm_drives


class PlayRepository:
    """
    Repository for Play fact data.

    Handles conversion between PlayRecord (execution state) and ORM Play objects
    and manages persistence of play execution records.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the PlayRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(
        self, play_record: PlayRecord, game_id: str, drive_id: int, play_number: int
    ) -> OrmPlay:
        """
        Convert a PlayRecord to an ORM Play.

        Args:
            play_record: PlayRecord object from simulation.
            game_id: Parent game ID.
            drive_id: Parent drive ID.
            play_number: 1-based play number within drive.

        Returns:
            ORM Play object (not yet persisted).
        """
        execution_data = play_record.execution_data
        start = play_record.start
        end = play_record.end

        orm_play = OrmPlay(
            game_id=game_id,
            drive_id=drive_id,
            play_number=play_number,
            # Call metadata
            play_call_id=execution_data.off_play_call.uid
            if execution_data.off_play_call
            else None,
            play_type=execution_data.play_type,
            side=execution_data.off_play_call.side
            if execution_data.off_play_call
            else None,
            formation_id=None,  # Can be enhanced if formation tracking is added
            personnel_id=None,  # Can be enhanced if personnel tracking is added
            # Teams
            offense_team_id=start.pos_team.uid if start.pos_team else None,
            defense_team_id=start.def_team.uid if start.def_team else None,
            # Start snapshot
            quarter=start.clock_snapshot.quarter,
            time_remaining=start.clock_snapshot.time_remaining,
            down=start.possession_snapshot.down,
            distance=start.possession_snapshot.distance,
            yardline_start=start.possession_snapshot.yardline,
            # Outcomes
            yardline_end=end.possession_snapshot.yardline,
            yards_gained=execution_data.yards_gained or 0,
            possession_changed=int(execution_data.is_possession_change or False),
            turnover=int(execution_data.is_turnover or False),
            scoring_type=None,  # Can be populated if scoring data is tracked
            scoring_team_id=None,  # Can be populated if scoring data is tracked
        )
        return orm_play

    def save(
        self, play_record: PlayRecord, game_id: str, drive_id: int, play_number: int
    ) -> OrmPlay:
        """
        Convert and persist a single PlayRecord.

        Args:
            play_record: PlayRecord object.
            game_id: Parent game ID.
            drive_id: Parent drive ID.
            play_number: 1-based play number within drive.

        Returns:
            Persisted ORM Play object.
        """
        orm_play = self.to_orm(play_record, game_id, drive_id, play_number)
        self.db.insert_fact_data(orm_play)
        logger.info(f"Persisted play: {orm_play.id} (yards={orm_play.yards_gained})")
        return orm_play

    def save_batch(
        self, play_records: List[PlayRecord], game_id: str, drive_id: int
    ) -> List[OrmPlay]:
        """
        Convert and persist multiple PlayRecords from a drive.

        Args:
            play_records: List of PlayRecord objects.
            game_id: Parent game ID.
            drive_id: Parent drive ID.

        Returns:
            List of persisted ORM Play objects.
        """
        orm_plays = [
            self.to_orm(pr, game_id, drive_id, i + 1)
            for i, pr in enumerate(play_records)
        ]
        self.db.insert_fact_data(*orm_plays)
        logger.info(f"Persisted {len(orm_plays)} play(s).")
        return orm_plays


class PlayPersonnelAssignmentRepository:
    """
    Repository for PlayPersonnelAssignment fact data.

    Tracks which athletes were assigned to which positions for each play.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the PlayPersonnelAssignmentRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(
        self, play_id: int, team_id: str, athlete_id: str, position: AthletePositionEnum
    ) -> OrmPlayPersonnelAssignment:
        """
        Create an ORM PlayPersonnelAssignment.

        Args:
            play_id: Play fact ID.
            team_id: Team ID.
            athlete_id: Athlete ID.
            position: AthletePositionEnum.

        Returns:
            ORM PlayPersonnelAssignment object (not yet persisted).
        """
        orm_assignment = OrmPlayPersonnelAssignment(
            id=str(uuid.uuid4()),
            play_id=play_id,
            team_id=team_id,
            athlete_id=athlete_id,
            position=position,
        )
        return orm_assignment

    def save_batch(
        self,
        play_id: int,
        assignments: Dict[AthletePositionEnum, List[DomainAthlete]],
        team_id: str,
    ) -> List[OrmPlayPersonnelAssignment]:
        """
        Persist personnel assignments for a play.

        Args:
            play_id: Play fact ID.
            assignments: Dict of position -> List[Athlete] from play execution.
            team_id: Team ID.

        Returns:
            List of persisted ORM PlayPersonnelAssignment objects.
        """
        orm_assignments: List[OrmPlayPersonnelAssignment] = []
        for position, athletes in assignments.items():
            for athlete in athletes:
                orm_assignment = self.to_orm(play_id, team_id, athlete.uid, position)
                orm_assignments.append(orm_assignment)

        if orm_assignments:
            self.db.insert_fact_data(*orm_assignments)
            logger.info(f"Persisted {len(orm_assignments)} personnel assignment(s).")

        return orm_assignments


class PlayParticipantRepository:
    """
    Repository for PlayParticipant fact data.

    Tracks participant roles (passer, rusher, receiver, etc.) for each play.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the PlayParticipantRepository.

        Args:
            db_manager: DatabaseManager instance for persistence.
        """
        self.db = db_manager

    def to_orm(
        self,
        play_id: int,
        athlete_id: str,
        team_id: str,
        participant_type: PlayParticipantType,
    ) -> OrmPlayParticipant:
        """
        Create an ORM PlayParticipant.

        Args:
            play_id: Play fact ID.
            athlete_id: Athlete ID.
            team_id: Team ID.
            participant_type: PlayParticipantType enum.

        Returns:
            ORM PlayParticipant object (not yet persisted).
        """
        orm_participant = OrmPlayParticipant(
            id=str(uuid.uuid4()),
            play_id=play_id,
            athlete_id=athlete_id,
            team_id=team_id,
            participant_type=participant_type,
        )
        return orm_participant

    def save_batch(
        self, play_id: int, participants: Dict[str, PlayParticipantType], team_id: str
    ) -> List[OrmPlayParticipant]:
        """
        Persist participant roles for a play.

        Args:
            play_id: Play fact ID.
            participants: Dict of athlete_id -> PlayParticipantType from play execution.
            team_id: Team ID.

        Returns:
            List of persisted ORM PlayParticipant objects.
        """
        orm_participants: List[OrmPlayParticipant] = []
        for athlete_id, participant_type in participants.items():
            orm_participant = self.to_orm(
                play_id, athlete_id, team_id, participant_type
            )
            orm_participants.append(orm_participant)

        if orm_participants:
            self.db.insert_fact_data(*orm_participants)
            logger.info(f"Persisted {len(orm_participants)} participant(s).")

        return orm_participants


class FactRepository:
    """
    Facade for all fact repositories.

    Provides a unified interface for persisting fact data from game simulations.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize FactRepository with all sub-repositories.

        Args:
            db_manager: DatabaseManager instance.
        """
        self.db = db_manager
        self.drives = DriveRepository(db_manager)
        self.plays = PlayRepository(db_manager)
        self.play_personnel_assignments = PlayPersonnelAssignmentRepository(db_manager)
        self.play_participants = PlayParticipantRepository(db_manager)

    def persist_game_facts(self, game_id: str, game_state: GameState) -> None:
        """
        Persist all fact data from a completed game.

        This includes:
        - Drives (aggregated play data per drive)
        - Plays (individual play execution records)
        - Play personnel assignments (who was on the field)
        - Play participants (who participated in each play)

        Args:
            game_id: Game fact ID.
            game_state: GameState object with completed drives.
        """
        logger.info(f"Persisting game {game_id} fact data...")
        logger.info(f"Game has {len(game_state.drives)} drive(s)")

        # Persist drives
        if game_state.drives:
            orm_drives = self.drives.save_batch(game_state.drives, game_id)

            # Persist plays, personnel assignments, and participants for each drive
            for drive_idx, (drive, orm_drive) in enumerate(
                zip(game_state.drives, orm_drives)
            ):
                logger.info(
                    f"Processing drive {drive_idx + 1}/{len(game_state.drives)} with {len(drive.plays)} play(s)"
                )

                # Get the offensive team for this drive
                assert drive.start.pos_team is not None
                assert drive.start.def_team is not None
                drive_offense_team_id = drive.start.pos_team.uid
                drive_defense_team_id = drive.start.def_team.uid

                for play_number, play_record in enumerate(drive.plays, start=1):
                    # Persist the play - use orm_drive.id which has the composite ID
                    orm_play = self.plays.to_orm(
                        play_record, game_id, orm_drive.id, play_number
                    )
                    self.db.insert_fact_data(orm_play)

                    # Persist offensive personnel assignments
                    if play_record.off_personnel_assignments:
                        self.play_personnel_assignments.save_batch(
                            orm_play.id,
                            play_record.off_personnel_assignments,
                            drive_offense_team_id,
                        )

                    # Persist defensive personnel assignments
                    if play_record.def_personnel_assignments:
                        self.play_personnel_assignments.save_batch(
                            orm_play.id,
                            play_record.def_personnel_assignments,
                            drive_defense_team_id,
                        )

                    # Persist participants
                    if play_record.participants:
                        self.play_participants.save_batch(
                            orm_play.id,
                            play_record.participants,
                            drive_offense_team_id,
                        )

        logger.info(f"Game {game_id} fact data persisted successfully.")
