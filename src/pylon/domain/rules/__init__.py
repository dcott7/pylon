"""
League rules and configurations for Pylon game simulations.

Provides abstract base rules, specific implementations (e.g., NFL),
and supporting classes for managing game flow, scoring, and play setup.
"""

from .base import (
    LeagueRules,
    LeagueRulesError,
    FirstDownRule,
    KickoffSetup,
    ExtraPointSetup,
)
from .nfl import NFLRules

__all__ = [
    "LeagueRules",
    "LeagueRulesError",
    "FirstDownRule",
    "KickoffSetup",
    "ExtraPointSetup",
    "NFLRules",
]
