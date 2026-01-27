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
    plays: Mapped[List["Play"]] = relationship(
        "Play",
        foreign_keys="Play.team_id",
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
    side: Mapped[PlaySideEnum] = mapped_column(SQLEnum(PlaySideEnum), nullable=False)
    parent_formation_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("formation.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Self-referential relationship for subformations
    subformations: Mapped[List["Formation"]] = relationship(
        "Formation",
        remote_side=[id],
        backref="parent_formation",
    )

    def __repr__(self) -> str:
        return f"Formation(id={self.id}, name={self.name}, side={self.side})"


class Personnel(Base):
    """
    Dimension: Personnel groupings.

    Represents personnel packages (e.g., "11 Personnel" = 1 RB, 1 TE, 3 WR).
    Used to standardize player groupings in offensive and defensive packages.
    """

    __tablename__ = "personnel"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Personnel UID
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    side: Mapped[PlaySideEnum] = mapped_column(SQLEnum(PlaySideEnum), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    plays: Mapped[List["Play"]] = relationship(
        "Play",
        back_populates="personnel",
    )

    def __repr__(self) -> str:
        return f"Personnel(id={self.id}, name={self.name}, side={self.side})"


class Play(Base):
    """
    Dimension: Play/Play Call information.

    Represents a play template in a team's playbook.
    References formation, personnel, and play type.
    Linked to offensive and defensive teams.
    """

    __tablename__ = "play"

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
        return f"Play(id={self.id}, name={self.name}, type={self.play_type})"


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
