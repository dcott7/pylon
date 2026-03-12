"""Canonical serializers for output payloads.

These functions keep domain and persistence layers decoupled by building
output dictionaries from domain entities in one place.
"""

from typing import Dict, List

from ..domain.athlete import Athlete
from ..domain.playbook import Formation, PersonnelPackage, PlayCall, Playbook
from ..domain.team import Team
from ..state.drive_record import DriveRecord
from ..state.game_state import GameState
from ..state.play_record import PlayRecord
from ..state.play_record import PlaySnapshot
from ..state.drive_record import DriveSnapshot
from .types import (
    AthleteRefOutputPayload,
    AthleteOutputPayload,
    DriveRecordOutputPayload,
    FormationOutputPayload,
    GameStateOutputPayload,
    ParticipantOutputPayload,
    PersonnelAssignmentsOutputPayload,
    PersonnelOutputPayload,
    PlaybookOutputPayload,
    PlayCallOutputPayload,
    PlayRecordOutputPayload,
    SnapshotOutputPayload,
    TeamOutputPayload,
)


def serialize_athlete(athlete: Athlete) -> AthleteOutputPayload:
    """Serialize a domain athlete into canonical output structure."""
    return {
        "uid": athlete.uid,
        "first_name": athlete.first_name,
        "last_name": athlete.last_name,
        "position": athlete.position.value,
    }


def serialize_formation(formation: Formation) -> FormationOutputPayload:
    """Serialize a domain formation into canonical output structure."""
    return {
        "uid": formation.uid,
        "name": formation.name,
        "parent_uid": formation.parent.uid if formation.parent is not None else None,
        "position_counts": {
            position.value: count
            for position, count in formation.position_counts.items()
        },
        "tags": list(formation.tags),
    }


def serialize_personnel(personnel: PersonnelPackage) -> PersonnelOutputPayload:
    """Serialize a domain personnel package into canonical output structure."""
    return {
        "uid": personnel.uid,
        "name": personnel.name,
        "counts": {
            position.value: count for position, count in personnel.counts.items()
        },
    }


def serialize_play_call(play_call: PlayCall) -> PlayCallOutputPayload:
    """Serialize a domain play call into canonical output structure."""
    return {
        "uid": play_call.uid,
        "name": play_call.name,
        "play_type": play_call.play_type.value,
        "side": play_call.side.value,
        "description": play_call.description,
        "tags": list(play_call.tags),
        "formation": serialize_formation(play_call.formation),
        "personnel_package": serialize_personnel(play_call.personnel_package),
    }


def serialize_playbook(playbook: Playbook | None) -> PlaybookOutputPayload:
    """Serialize a playbook or a missing playbook into canonical output structure."""
    if playbook is None:
        return {"uid": None, "plays": []}

    return {
        "uid": playbook.uid,
        "plays": [serialize_play_call(play_call) for play_call in playbook.plays],
    }


def serialize_team(team: Team) -> TeamOutputPayload:
    """Serialize a full team with roster and playbooks into canonical output."""
    return {
        "uid": team.uid,
        "name": team.name,
        "athletes": [serialize_athlete(athlete) for athlete in team.roster],
        "playbooks": {
            "offense": serialize_playbook(team.off_playbook),
            "defense": serialize_playbook(team.def_playbook),
        },
    }


def _serialize_snapshot(
    snapshot: PlaySnapshot | DriveSnapshot,
) -> SnapshotOutputPayload:
    """Serialize clock/possession/score snapshots in a compact shape."""
    return {
        "pos_team_uid": snapshot.pos_team.uid if snapshot.pos_team else None,
        "def_team_uid": snapshot.def_team.uid if snapshot.def_team else None,
        "clock": {
            "quarter": snapshot.clock_snapshot.quarter,
            "time_remaining": snapshot.clock_snapshot.time_remaining,
            "clock_is_running": snapshot.clock_snapshot.clock_is_running,
        },
        "possession": {
            "down": snapshot.possession_snapshot.down,
            "distance": snapshot.possession_snapshot.distance,
            "yardline": snapshot.possession_snapshot.yardline,
        },
        "score": {
            "pos_team": snapshot.scoreboard_snapshot.pos_team_score,
            "def_team": snapshot.scoreboard_snapshot.def_team_score,
        },
    }


def _serialize_personnel_assignments(
    play_record: PlayRecord,
) -> PersonnelAssignmentsOutputPayload:
    """Serialize offensive/defensive personnel assignments for a play."""
    offense_assignments: Dict[str, List[AthleteRefOutputPayload]] = {
        position.value: [_serialize_athlete_ref(athlete) for athlete in athletes]
        for position, athletes in play_record.execution_data.off_personnel_assignments.items()
    }
    defense_assignments: Dict[str, List[AthleteRefOutputPayload]] = {
        position.value: [_serialize_athlete_ref(athlete) for athlete in athletes]
        for position, athletes in play_record.execution_data.def_personnel_assignments.items()
    }

    payload: PersonnelAssignmentsOutputPayload = {
        "offense": offense_assignments,
        "defense": defense_assignments,
    }
    return payload


def _serialize_athlete_ref(athlete: Athlete) -> AthleteRefOutputPayload:
    """Serialize an athlete into a compact, self-describing reference object."""
    return {
        "uid": athlete.uid,
        "display_name": f"{athlete.first_name} {athlete.last_name}",
        "position": athlete.position.value,
    }


def _find_athlete_for_participant(
    play_record: PlayRecord, athlete_uid: str
) -> Athlete | None:
    """Resolve a participant athlete UID from assignment sets or team rosters."""
    for athletes in play_record.execution_data.off_personnel_assignments.values():
        for athlete in athletes:
            if athlete.uid == athlete_uid:
                return athlete

    for athletes in play_record.execution_data.def_personnel_assignments.values():
        for athlete in athletes:
            if athlete.uid == athlete_uid:
                return athlete

    for team in (play_record.start.pos_team, play_record.start.def_team):
        if team is None:
            continue
        for athlete in team.roster:
            if athlete.uid == athlete_uid:
                return athlete

    return None


def _serialize_participants(play_record: PlayRecord) -> List[ParticipantOutputPayload]:
    """Serialize participant map into ESPN-style ordered participant entries."""
    payload: List[ParticipantOutputPayload] = []
    for athlete_uid in play_record.execution_data.participants.keys():
        participant_type = play_record.execution_data.participants[athlete_uid]
        athlete = _find_athlete_for_participant(play_record, athlete_uid)

        if athlete is not None:
            athlete_ref: AthleteRefOutputPayload = _serialize_athlete_ref(athlete)
        else:
            athlete_ref = {
                "uid": athlete_uid,
                "display_name": "Unknown Athlete",
                "position": None,
            }

        payload.append(
            {
                "athlete": athlete_ref,
                "position": athlete_ref["position"],
                "type": participant_type.value,
            }
        )

    return payload


def serialize_play_record(play_record: PlayRecord) -> PlayRecordOutputPayload:
    """Serialize one finalized play record including execution data."""
    return {
        "play_id": play_record.uid,
        "start": _serialize_snapshot(play_record.start),
        "end": _serialize_snapshot(play_record.end),
        "execution": {
            "play_type": (
                play_record.execution_data.play_type.value
                if play_record.execution_data.play_type
                else None
            ),
            "off_play_call_uid": (
                play_record.execution_data.off_play_call.uid
                if play_record.execution_data.off_play_call
                else None
            ),
            "def_play_call_uid": (
                play_record.execution_data.def_play_call.uid
                if play_record.execution_data.def_play_call
                else None
            ),
            "time_elapsed": play_record.execution_data.time_elapsed,
            "preplay_clock_runoff": play_record.execution_data.preplay_clock_runoff,
            "yards_gained": play_record.execution_data.yards_gained,
            "is_possession_change": play_record.execution_data.is_possession_change,
            "is_turnover": play_record.execution_data.is_turnover,
            "is_fg_attempt": play_record.execution_data.is_fg_attempt,
            "fg_good": play_record.execution_data.fg_good,
            "is_clock_running": play_record.execution_data.is_clock_running,
            "air_yards": play_record.execution_data.air_yards,
            "yards_after_catch": play_record.execution_data.yards_after_catch,
            "is_complete": play_record.execution_data.is_complete,
            "is_interception": play_record.execution_data.is_interception,
            "is_sack": play_record.execution_data.is_sack,
            "run_gap": play_record.execution_data.run_gap,
            "is_fumble": play_record.execution_data.is_fumble,
            "fumble_recovered_by_team_uid": (
                play_record.execution_data.fumble_recovered_by_team.uid
                if play_record.execution_data.fumble_recovered_by_team
                else None
            ),
            "penalty_occurred": play_record.execution_data.penalty_occurred,
            "penalty_yards": play_record.execution_data.penalty_yards,
            "penalty_type": play_record.execution_data.penalty_type,
            "penalty_team_uid": (
                play_record.execution_data.penalty_team.uid
                if play_record.execution_data.penalty_team
                else None
            ),
            "participants": _serialize_participants(play_record),
            "personnel_assignments": _serialize_personnel_assignments(play_record),
        },
    }


def serialize_drive_record(drive_record: DriveRecord) -> DriveRecordOutputPayload:
    """Serialize one finalized drive record including nested play records."""
    return {
        "drive_id": drive_record.uid,
        "start": _serialize_snapshot(drive_record.start),
        "end": _serialize_snapshot(drive_record.end),
        "execution": {
            "status": drive_record.execution_data.status.value,
            "time_elapsed": drive_record.execution_data.time_elapsed,
            "yards_gained": drive_record.execution_data.yards_gained,
            "is_scoring_drive": drive_record.execution_data.is_scoring_drive,
            "scoring_type": drive_record.execution_data.scoring_type.value,
            "scoring_team_uid": (
                drive_record.execution_data.scoring_team.uid
                if drive_record.execution_data.scoring_team
                else None
            ),
            "result": (
                drive_record.execution_data.result.value
                if drive_record.execution_data.result
                else None
            ),
        },
        "plays": [serialize_play_record(play) for play in drive_record.plays],
    }


def serialize_game_state(
    game_state: GameState,
    rep_number: int,
    seed: int,
) -> GameStateOutputPayload:
    """Serialize full game execution details from GameState/GameExecutionData."""
    return {
        "game_id": game_state.game_data.game_id,
        "rep_number": rep_number,
        "seed": seed,
        "status": game_state.game_data.status.name,
        "coin_toss": {
            "winner_uid": (
                game_state.game_data.coin_toss_winner.uid
                if game_state.game_data.coin_toss_winner
                else None
            ),
            "winner_choice": (
                game_state.game_data.coin_toss_winner_choice.name
                if game_state.game_data.coin_toss_winner_choice
                else None
            ),
        },
        "drives": [serialize_drive_record(drive) for drive in game_state.drives],
    }
