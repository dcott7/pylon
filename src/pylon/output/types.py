"""Shared output mode types and validation helpers."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, TypedDict, Optional


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
    parent_uid: Optional[str]
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
    description: Optional[str]
    tags: List[str]


class PlaybookOutputPayload(TypedDict):
    """Canonical serialized playbook payload."""

    uid: Optional[str]
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
    description: Optional[str]


class ClockSnapshotOutputPayload(TypedDict):
    """Serialized clock snapshot payload."""

    quarter: Optional[int]
    time_remaining: Optional[int]
    clock_is_running: Optional[bool]


class PossessionSnapshotOutputPayload(TypedDict):
    """Serialized possession snapshot payload."""

    down: Optional[int]
    distance: Optional[int]
    yardline: Optional[int]


class ScoreSnapshotOutputPayload(TypedDict):
    """Serialized score snapshot payload."""

    pos_team: Optional[int]
    def_team: Optional[int]


class SnapshotOutputPayload(TypedDict):
    """Serialized combined snapshot payload used by plays and drives."""

    pos_team_uid: Optional[str]
    def_team_uid: Optional[str]
    clock: ClockSnapshotOutputPayload
    possession: PossessionSnapshotOutputPayload
    score: ScoreSnapshotOutputPayload


class AthleteRefOutputPayload(TypedDict):
    uid: str
    display_name: str
    position: Optional[str]


class PersonnelAssignmentsOutputPayload(TypedDict):
    """Serialized personnel assignments keyed by position code."""

    offense: Dict[str, List[AthleteRefOutputPayload]]
    defense: Dict[str, List[AthleteRefOutputPayload]]


class ParticipantOutputPayload(TypedDict):
    """Serialized play participant entry inspired by ESPN style payloads."""

    athlete: AthleteRefOutputPayload
    position: Optional[str]
    type: str


class PlayExecutionOutputPayload(TypedDict):
    """Serialized play execution payload."""

    play_type: Optional[str]
    off_play_call_uid: Optional[str]
    def_play_call_uid: Optional[str]
    time_elapsed: Optional[int]
    preplay_clock_runoff: Optional[int]
    yards_gained: Optional[int]
    is_possession_change: Optional[bool]
    is_turnover: Optional[bool]
    is_fg_attempt: Optional[bool]
    fg_good: Optional[bool]
    is_clock_running: Optional[bool]
    air_yards: Optional[int]
    yards_after_catch: Optional[int]
    is_complete: Optional[bool]
    is_interception: Optional[bool]
    is_sack: Optional[bool]
    run_gap: Optional[str]
    is_fumble: Optional[bool]
    fumble_recovered_by_team_uid: Optional[str]
    penalty_occurred: Optional[bool]
    penalty_yards: Optional[int]
    penalty_type: Optional[str]
    penalty_team_uid: Optional[str]
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
    scoring_team_uid: Optional[str]
    result: Optional[str]


class DriveRecordOutputPayload(TypedDict):
    """Serialized drive record payload."""

    drive_id: str
    start: SnapshotOutputPayload
    end: SnapshotOutputPayload
    execution: DriveExecutionOutputPayload
    plays: List[PlayRecordOutputPayload]


class CoinTossOutputPayload(TypedDict):
    """Serialized coin toss payload."""

    winner_uid: Optional[str]
    winner_choice: Optional[str]


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
    json_output_path: Optional[Path],
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
