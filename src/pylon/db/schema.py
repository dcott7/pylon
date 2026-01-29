"""
Database schema for Pylon game simulations.

Dimension tables focus on static/reference data:
- Teams: Team information
- Athletes: Player information
- Playbooks: Play information
- Positions: Position reference data
- Formations: Formation reference data
- Personnel: Personnel groupings (11 personnel, 12 personnel, etc.)

Fact tables:
- ModelInvocation: Captures typed user model calls, inputs, outputs, and metadata
- Experiment: Metadata for simulation experiments (groups of game replications)
- Game: Individual game results (one per simulation rep)
"""

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..domain.athlete import AthletePositionEnum
from ..domain.playbook import PlaySideEnum, PlayTypeEnum
from ..state.play_record import PlayParticipantType


class Base(DeclarativeBase):
    pass


# Association table for Team-Player relationship
team_roster = Table(
    "team_roster",
    Base.metadata,
    Column("team_id", String, ForeignKey("team.id")),
    Column("athlete_id", String, ForeignKey("athlete.id")),
)


class Team(Base):
    """
    Dimension: Team information.

    Represents a team with its basic information and roster.
    Foreign key relationships to athletes through team_roster association table.
    """

    __tablename__ = "team"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Team UID
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    abbreviation: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    athletes: Mapped[List["Athlete"]] = relationship(
        "Athlete",
        secondary=team_roster,
        back_populates="teams",
    )
    plays: Mapped[List["PlayCall"]] = relationship(
        "PlayCall",
        foreign_keys="PlayCall.team_id",
        back_populates="team",
    )

    def __repr__(self) -> str:
        return f"Team(id={self.id}, name={self.name})"


class Athlete(Base):
    """
    Dimension: Player information.

    Represents an individual player with their position.
    Can belong to multiple teams (through team_roster).
    """

    __tablename__ = "athlete"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Athlete UID
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[AthletePositionEnum] = mapped_column(
        SQLEnum(AthletePositionEnum), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    teams: Mapped[List["Team"]] = relationship(
        "Team",
        secondary=team_roster,
        back_populates="athletes",
    )

    def __repr__(self) -> str:
        return f"Athlete(id={self.id}, name={self.first_name} {self.last_name}, position={self.position})"


class Position(Base):
    """
    Dimension: Position reference data.

    Lookup table for all valid positions in the league.
    Includes position name, hierarchy level, and parent position for tree structure.
    """

    __tablename__ = "position"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Position enum name
    position_enum: Mapped[AthletePositionEnum] = mapped_column(
        SQLEnum(AthletePositionEnum), nullable=False, unique=True
    )
    parent_position_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("position.id"), nullable=True
    )
    is_leaf: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Self-referential relationship for position hierarchy
    children: Mapped[List["Position"]] = relationship(
        "Position",
        remote_side=[id],
        backref="parent",
    )

    def __repr__(self) -> str:
        return f"Position(id={self.id}, enum={self.position_enum})"


class Formation(Base):
    """
    Dimension: Formation information.

    Represents offensive or defensive formations (e.g., "Shotgun Trips Right").
    Can have subformations for more specific alignment variants.
    """

    __tablename__ = "formation"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Formation UID
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    parent_formation_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("formation.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Self-referential relationship for subformations
    subformations: Mapped[List["Formation"]] = relationship(
        "Formation",
        remote_side=[id],
        backref="parent_formation",
    )

    def __repr__(self) -> str:
        return f"Formation(id={self.id}, name={self.name})"


class Personnel(Base):
    """
    Dimension: Personnel groupings.

    Represents personnel packages (e.g., "11 Personnel" = 1 RB, 1 TE, 3 WR).
    Used to standardize player groupings in offensive and defensive packages.
    """

    __tablename__ = "personnel"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Personnel UID
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    plays: Mapped[List["PlayCall"]] = relationship(
        "PlayCall",
        back_populates="personnel",
    )

    def __repr__(self) -> str:
        return f"Personnel(id={self.id}, name={self.name})"


class PlayCall(Base):
    """
    Dimension: Play/Play Call information.

    Represents a play template in a team's playbook.
    References formation, personnel, and play type.
    Linked to offensive and defensive teams.
    """

    __tablename__ = "play_call"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Play UID
    name: Mapped[str] = mapped_column(String, nullable=False)
    play_type: Mapped[PlayTypeEnum] = mapped_column(
        SQLEnum(PlayTypeEnum), nullable=False
    )
    side: Mapped[PlaySideEnum] = mapped_column(SQLEnum(PlaySideEnum), nullable=False)

    # Team reference (owner of this play in the playbook)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("team.id"), nullable=False)

    # Formation and Personnel references
    formation_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("formation.id"), nullable=True
    )
    personnel_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("personnel.id"), nullable=True
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[team_id],
        back_populates="plays",
    )
    formation: Mapped[Optional["Formation"]] = relationship("Formation")
    personnel: Mapped[Optional["Personnel"]] = relationship(
        "Personnel", back_populates="plays"
    )

    def __repr__(self) -> str:
        return f"PlayCall(id={self.id}, name={self.name}, type={self.play_type})"


class Playbook(Base):
    """
    Dimension: Playbook metadata.

    Represents a team's playbook collection.
    Groups plays by side (offensive/defensive).
    """

    __tablename__ = "playbook"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Playbook UID
    team_id: Mapped[str] = mapped_column(String, ForeignKey("team.id"), nullable=False)
    side: Mapped[PlaySideEnum] = mapped_column(SQLEnum(PlaySideEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self) -> str:
        return f"Playbook(id={self.id}, team_id={self.team_id}, side={self.side})"


class ModelInvocation(Base):
    """
    Fact: Model invocation tracking.

    Captures every call to a typed user model, including:
    - Input context (serialized to JSON)
    - Output/return value (serialized to JSON with return type discriminator)
    - Execution metadata (game, drive, play, engine phase)
    - Performance metrics (duration, errors)

    This enables analysis, debugging, and replayability of model decisions.
    """

    __tablename__ = "model_invocation"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Unique invocation ID
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Model identification
    model_name: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., "DefaultOffensivePlayCallModel"
    model_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., "offensive_play_call", "passer_selection"
    model_version: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Optional version tag

    # Game context references (foreign keys optional for flexibility)
    game_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    drive_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    play_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    engine_phase: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # e.g., "play_call", "personnel_selection"

    # Input context (serialized)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Output/return value (serialized)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    return_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Discriminator: "PlayCall", "Athlete", "float", etc.

    # RNG state for replayability (optional)
    rng_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Performance metrics
    duration_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    error: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # If execution failed

    def __repr__(self) -> str:
        return f"ModelInvocation(id={self.id}, model={self.model_name}, type={self.return_type})"


class Experiment(Base):
    """
    Fact: Experiment metadata.

    Represents a simulation experiment—a collection of game replications with
    varying seeds and/or model configurations. Used to track and organize
    multiple runs of the same matchup for statistical analysis.

    Attributes:
        id: Unique experiment identifier (UUID).
        name: Human-readable experiment name.
        description: Detailed description of experiment purpose/configuration.
        num_reps: Number of replications planned/completed.
        base_seed: Base random seed for deterministic rep generation.
        created_at: Timestamp when experiment was created.
    """

    __tablename__ = "experiment"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Experiment UID
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    num_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    base_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    games: Mapped[List["Game"]] = relationship(
        "Game",
        back_populates="experiment",
    )

    def __repr__(self) -> str:
        return f"Experiment(id={self.id}, name={self.name}, reps={self.num_reps})"


class Game(Base):
    """
    Fact: Individual game result.

    Represents a single game simulation result—one replication within an experiment.
    Captures final score, metadata, and links to dimension data (teams) and other
    fact data (model invocations, drives, plays).

    Attributes:
        id: Unique game identifier (UUID).
        experiment_id: Reference to parent experiment (optional for standalone games).
        rep_number: Replication number within experiment (1-based).
        seed: Random seed used for this specific game run.
        home_team_id: Reference to home team dimension.
        away_team_id: Reference to away team dimension.
        home_score: Final score for home team.
        away_score: Final score for away team.
        winner_id: Reference to winning team (nullable for ties).
        total_plays: Total number of plays executed.
        total_drives: Total number of drives executed.
        duration_seconds: Real-world execution time.
        final_quarter: Final quarter when game ended.
        status: Game status ('completed' or 'failed').
        created_at: Timestamp when game was simulated.
    """

    __tablename__ = "game"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Game UID
    experiment_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("experiment.id"), nullable=True
    )
    rep_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)

    # Team references
    home_team_id: Mapped[str] = mapped_column(
        String, ForeignKey("team.id"), nullable=False
    )
    away_team_id: Mapped[str] = mapped_column(
        String, ForeignKey("team.id"), nullable=False
    )

    # Final results
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("team.id"), nullable=True
    )

    # Game statistics
    total_plays: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_drives: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    final_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    experiment: Mapped[Optional["Experiment"]] = relationship(
        "Experiment",
        back_populates="games",
    )
    home_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[home_team_id],
    )
    away_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[away_team_id],
    )
    winner: Mapped[Optional["Team"]] = relationship(
        "Team",
        foreign_keys=[winner_id],
    )

    def __repr__(self) -> str:
        return f"Game(id={self.id}, rep={self.rep_number}, score={self.home_score}-{self.away_score})"


class Drive(Base):
    """
    Fact: Drive-level execution record.

    Captures per-drive metadata for downstream analysis:
    - start/end snapshots (clock, possession, scoreboard)
    - yards gained, plays executed, elapsed time
    - end result and scoring details
    """

    __tablename__ = "drive"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Drive UID
    game_id: Mapped[str] = mapped_column(String, ForeignKey("game.id"), nullable=False)
    drive_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 1-based within game

    # Teams
    offense_team_id: Mapped[str] = mapped_column(
        String, ForeignKey("team.id"), nullable=False
    )
    defense_team_id: Mapped[str] = mapped_column(
        String, ForeignKey("team.id"), nullable=False
    )

    # Start snapshot
    start_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    start_down: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_distance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_yardline: Mapped[int] = mapped_column(Integer, nullable=False)

    # End snapshot
    end_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    end_down: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_distance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_yardline: Mapped[int] = mapped_column(Integer, nullable=False)

    # Aggregates
    plays_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    yards_gained: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_elapsed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Results
    result: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., score, turnover, punt, end_of_half
    scoring_type: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # touchdown/fg/safety/none
    scoring_team_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("team.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Play(Base):
    """
    Fact: Play-level execution record.

    Stores snapshots, call metadata, personnel assignments, participants, and results
    for each executed play. Designed for analytics and replay.
    """

    __tablename__ = "play"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Play execution UID
    game_id: Mapped[str] = mapped_column(String, ForeignKey("game.id"), nullable=False)
    drive_id: Mapped[str] = mapped_column(
        String, ForeignKey("drive.id"), nullable=False
    )
    play_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 1-based within drive

    # Call metadata
    play_call_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("play_call.id"), nullable=True
    )
    play_type: Mapped[Optional[PlayTypeEnum]] = mapped_column(
        SQLEnum(PlayTypeEnum), nullable=True
    )
    side: Mapped[Optional[PlaySideEnum]] = mapped_column(
        SQLEnum(PlaySideEnum), nullable=True
    )
    formation_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("formation.id"), nullable=True
    )
    personnel_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("personnel.id"), nullable=True
    )

    # Teams
    offense_team_id: Mapped[str] = mapped_column(
        String, ForeignKey("team.id"), nullable=False
    )
    defense_team_id: Mapped[str] = mapped_column(
        String, ForeignKey("team.id"), nullable=False
    )

    # Start snapshot
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    time_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    down: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    yardline_start: Mapped[int] = mapped_column(Integer, nullable=False)

    # Outcomes
    yardline_end: Mapped[int] = mapped_column(Integer, nullable=False)
    yards_gained: Mapped[int] = mapped_column(Integer, nullable=False)
    possession_changed: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    turnover: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    scoring_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scoring_team_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("team.id"), nullable=True
    )

    # Optional serialized snapshot for replay/debug (core fields are already columns)
    snapshot_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    assignments: Mapped[List["PlayPersonnelAssignment"]] = relationship(
        "PlayPersonnelAssignment", back_populates="play"
    )
    participants_rel: Mapped[List["PlayParticipant"]] = relationship(
        "PlayParticipant", back_populates="play"
    )


class PlayPersonnelAssignment(Base):
    """
    Fact: On-field personnel mapping for a play.

    Normalized bridge of athlete-to-position participation for a specific play
    and team (offense or defense).
    """

    __tablename__ = "play_personnel_assignment"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    play_id: Mapped[str] = mapped_column(String, ForeignKey("play.id"), nullable=False)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("team.id"), nullable=False)
    athlete_id: Mapped[str] = mapped_column(
        String, ForeignKey("athlete.id"), nullable=False
    )
    position: Mapped[AthletePositionEnum] = mapped_column(
        SQLEnum(AthletePositionEnum), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    play: Mapped["Play"] = relationship("Play", back_populates="assignments")
    team: Mapped["Team"] = relationship("Team")
    athlete: Mapped["Athlete"] = relationship("Athlete")

    def __repr__(self) -> str:
        return (
            "PlayPersonnelAssignment("
            f"play_id={self.play_id}, team_id={self.team_id}, "
            f"athlete_id={self.athlete_id}, position={self.position}"
            ")"
        )


class PlayParticipant(Base):
    """
    Fact: Participant roles tied to a play outcome (passer, rusher, returner, etc.).
    """

    __tablename__ = "play_participant"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    play_id: Mapped[str] = mapped_column(String, ForeignKey("play.id"), nullable=False)
    athlete_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("athlete.id"), nullable=True
    )
    team_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("team.id"), nullable=True
    )
    participant_type: Mapped[PlayParticipantType] = mapped_column(
        SQLEnum(PlayParticipantType), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    play: Mapped["Play"] = relationship("Play", back_populates="participants_rel")
    athlete: Mapped[Optional["Athlete"]] = relationship("Athlete")
    team: Mapped[Optional["Team"]] = relationship("Team")

    def __repr__(self) -> str:
        return (
            "PlayParticipant("
            f"play_id={self.play_id}, athlete_id={self.athlete_id}, "
            f"participant_type={self.participant_type}"
            ")"
        )
