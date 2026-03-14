"""Shared output mode types and validation helpers."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, TypedDict


OUTPUT_SCHEMA_VERSION = "1.0"


class OutputModeValidationError(ValueError):
    """Custom exception for invalid output mode configurations."""

    pass


class OutputMode(Enum):
    """Enum for supported output modes."""

    JSON = "json"
    DB = "db"
    BOTH = "both"
    NONE = "none"


class AthleteOutputPayload(TypedDict):
    """Canonical serialized athlete payload."""

    uid: str
    first_name: str
    last_name: str
    position: str


class FormationOutputPayload(TypedDict):
    """Canonical serialized formation payload."""

    uid: str
    name: str
    parent_uid: str | None
    position_counts: Dict[str, int]
    tags: List[str]


class PersonnelOutputPayload(TypedDict):
    """Canonical serialized personnel package payload."""

    uid: str
    name: str
    counts: Dict[str, int]


class PlayCallOutputPayload(TypedDict):
    """Canonical serialized play call payload."""

    uid: str
    name: str
    play_type: str
    formation: FormationOutputPayload
    personnel_package: PersonnelOutputPayload
    side: str
    description: str | None
    tags: List[str]


class PlaybookOutputPayload(TypedDict):
    """Canonical serialized playbook payload."""

    uid: str | None
    plays: List[PlayCallOutputPayload]


class TeamOutputPayload(TypedDict):
    """Canonical serialized team payload used by all output writers."""

    uid: str
    name: str
    athletes: List[AthleteOutputPayload]
    playbooks: Dict[str, PlaybookOutputPayload]


class ExperimentOutputPayload(TypedDict):
    """Canonical serialized experiment metadata payload."""

    id: str
    name: str
    num_reps: int
    base_seed: int
    elapsed_time: float
    description: str | None


class ClockSnapshotOutputPayload(TypedDict):
    """Serialized clock snapshot payload."""

    quarter: int | None
    time_remaining: int | None
    clock_is_running: bool | None


class PossessionSnapshotOutputPayload(TypedDict):
    """Serialized possession snapshot payload."""

    down: int | None
    distance: int | None
    yardline: int | None


class ScoreSnapshotOutputPayload(TypedDict):
    """Serialized score snapshot payload."""

    pos_team: int | None
    def_team: int | None


class SnapshotOutputPayload(TypedDict):
    """Serialized combined snapshot payload used by plays and drives."""

    pos_team_uid: str | None
    def_team_uid: str | None
    clock: ClockSnapshotOutputPayload
    possession: PossessionSnapshotOutputPayload
    score: ScoreSnapshotOutputPayload


class AthleteRefOutputPayload(TypedDict):
    uid: str
    display_name: str
    position: str | None


class PersonnelAssignmentsOutputPayload(TypedDict):
    """Serialized personnel assignments keyed by position code."""

    offense: Dict[str, List[AthleteRefOutputPayload]]
    defense: Dict[str, List[AthleteRefOutputPayload]]


class ParticipantOutputPayload(TypedDict):
    """Serialized play participant entry inspired by ESPN style payloads."""

    athlete: AthleteRefOutputPayload
    position: str | None
    type: str


class PlayExecutionOutputPayload(TypedDict):
    """Serialized play execution payload."""

    play_type: str | None
    off_play_call_uid: str | None
    def_play_call_uid: str | None
    time_elapsed: int | None
    preplay_clock_runoff: int | None
    yards_gained: int | None
    is_possession_change: bool | None
    is_turnover: bool | None
    is_fg_attempt: bool | None
    fg_good: bool | None
    is_clock_running: bool | None
    air_yards: int | None
    yards_after_catch: int | None
    is_complete: bool | None
    is_interception: bool | None
    is_sack: bool | None
    run_gap: str | None
    is_fumble: bool | None
    fumble_recovered_by_team_uid: str | None
    penalty_occurred: bool | None
    penalty_yards: int | None
    penalty_type: str | None
    penalty_team_uid: str | None
    participants: List[ParticipantOutputPayload]
    personnel_assignments: PersonnelAssignmentsOutputPayload


class PlayRecordOutputPayload(TypedDict):
    """Serialized play record payload."""

    play_id: str
    start: SnapshotOutputPayload
    end: SnapshotOutputPayload
    execution: PlayExecutionOutputPayload


class DriveExecutionOutputPayload(TypedDict):
    """Serialized drive execution payload."""

    status: str
    time_elapsed: int
    yards_gained: int
    is_scoring_drive: bool
    scoring_type: str
    scoring_team_uid: str | None
    result: str | None


class DriveRecordOutputPayload(TypedDict):
    """Serialized drive record payload."""

    drive_id: str
    start: SnapshotOutputPayload
    end: SnapshotOutputPayload
    execution: DriveExecutionOutputPayload
    plays: List[PlayRecordOutputPayload]


class CoinTossOutputPayload(TypedDict):
    """Serialized coin toss payload."""

    winner_uid: str | None
    winner_choice: str | None


class GameStateOutputPayload(TypedDict):
    """Serialized game execution payload."""

    game_id: str
    rep_number: int
    seed: int
    status: str
    coin_toss: CoinTossOutputPayload
    drives: List[DriveRecordOutputPayload]


class SimulationResultsPayload(TypedDict):
    """Canonical results payload with summaries, aggregate stats, and detailed execution."""

    games: List[Dict[str, Any]]
    aggregate: Dict[str, Any]
    game_details: List[GameStateOutputPayload]


class SimulationOutputPayload(TypedDict):
    """Canonical serialized simulation payload for JSON and DB projections."""

    schema_version: str
    experiment: ExperimentOutputPayload
    teams: Dict[str, TeamOutputPayload]
    results: SimulationResultsPayload


def wants_json_output(output_mode: OutputMode) -> bool:
    """Return True when JSON output should be written."""
    return output_mode in (OutputMode.JSON, OutputMode.BOTH)


def wants_db_output(output_mode: OutputMode) -> bool:
    """Return True when database output should be persisted."""
    return output_mode in (OutputMode.DB, OutputMode.BOTH)


def validate_output_config(
    output_mode: OutputMode,
    has_db_manager: bool,
    json_output_path: Path | None,
) -> None:
    """Validate required dependencies for the selected output mode."""
    if wants_db_output(output_mode) and not has_db_manager:
        raise OutputModeValidationError(
            "db_manager is required when output_mode is 'db' or 'both'."
        )

    if wants_json_output(output_mode) and json_output_path is None:
        raise OutputModeValidationError(
            "json_output_path is required when output_mode is 'json' or 'both'."
        )
