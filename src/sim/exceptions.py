"""Custom exceptions for the domain-agnostic simulation package."""

from __future__ import annotations


class SimulationError(Exception):
    """Base exception for all simulation framework errors."""


class SimulationConfigurationError(SimulationError):
    """Raised for invalid simulation runner configuration."""


class SimulationExecutionError(SimulationError):
    """Raised when a simulation replication fails to execute."""


class OutputSinkError(SimulationError):
    """Raised when writing simulation output to a sink fails."""
