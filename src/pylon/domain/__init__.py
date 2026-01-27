"""
Domain models for Pylon game simulations.

Provides core abstractions for representing football teams, players, playbooks,
and league rules.

Key components:
- Athlete: Individual player with position and unique identifier.
- AthletePositionEnum: Enumeration of all valid football positions.
- PositionTree: Hierarchical structure for position relationships and fallbacks.
- Team: Football team with roster, offensive/defensive playbooks.
- Playbook: Collection of plays organized by side (offensive/defensive).
- Play/PlayCall: Individual play template with formation and personnel.
- LeagueRules: Abstract interface for league-specific game rules.
- NFLRules: Concrete implementation of NFL ruleset.
"""

from .athlete import Athlete, AthletePositionEnum, PositionTree, POSITION_TREE
from .team import Team
from .playbook import (
    Playbook,
    PlayCall,
    PlaySideEnum,
    PlayTypeEnum,
    Formation,
    FormationInitializationError,
    PlayCallInitializationError,
)
from .rules import (
    LeagueRules,
    LeagueRulesError,
    FirstDownRule,
    KickoffSetup,
    ExtraPointSetup,
    NFLRules,
)

__all__ = [
    # Athlete module
    "Athlete",
    "AthletePositionEnum",
    "PositionTree",
    "POSITION_TREE",
    # Team module
    "Team",
    # Playbook module
    "Playbook",
    "PlayCall",
    "PlaySideEnum",
    "PlayTypeEnum",
    "Formation",
    "FormationInitializationError",
    "PlayCallInitializationError",
    # Rules module
    "LeagueRules",
    "LeagueRulesError",
    "FirstDownRule",
    "KickoffSetup",
    "ExtraPointSetup",
    "NFLRules",
]
