"""
Database module for Pylon game simulations.

Provides schema definitions and data access layer for persisting
game data to SQL databases.
"""

from .database import DatabaseManager
from .repositories import (
    DimensionRepository,
    TeamRepository,
    AthleteRepository,
    FormationRepository,
    PersonnelRepository,
    PlayRepository,
    ExperimentRepository,
    GameRepository,
)
from .schema import (
    Base,
    Team,
    Athlete,
    Position,
    Formation,
    Personnel,
    Play,
    Playbook,
    ModelInvocation,
    Experiment,
    Game,
)
from ..domain.athlete import AthletePositionEnum
from ..domain.playbook import PlaySideEnum, PlayTypeEnum

__all__ = [
    "DatabaseManager",
    "DimensionRepository",
    "TeamRepository",
    "AthleteRepository",
    "FormationRepository",
    "PersonnelRepository",
    "PlayRepository",
    "ExperimentRepository",
    "GameRepository",
    "Base",
    "Team",
    "Athlete",
    "Position",
    "Formation",
    "Personnel",
    "Play",
    "Playbook",
    "ModelInvocation",
    "Experiment",
    "Game",
    "AthletePositionEnum",
    "PlaySideEnum",
    "PlayTypeEnum",
]
