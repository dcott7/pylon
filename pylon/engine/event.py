from enum import auto, Enum
import logging
from typing import List

from ..entities.athlete import Athlete


logger = logging.getLogger(__name__)


class EventTypeEnum(Enum):
    HIKE = auto()
    PASS_ATTEMPT = auto()
    PASS_INCOMPLETE = auto()
    PASS_COMPLETE = auto()
    INTERCEPTION = auto()
    RUN_ATTEMPT = auto()
    FUMBLE = auto()
    TACKLE = auto()
    SACK = auto()
    PASS_DEFENDED = auto()
    FIELD_GOAL_ATTEMPT = auto()
    FIELD_GOAL_GOOD = auto()
    FIELD_GOAL_MISS = auto()
    PUNT_ATTEMPT = auto()
    PUNT_OUT_OF_BOUNDS = auto()
    KICKOFF_ATTEMPT = auto()
    ONSIDE_KICKOFF_ATTEMPT = auto()
    # EventType.KICK_BLOCKED is used for:
    #   1) FIELD_GOAL_ATTEMPT 
    #   2) EXTRA_POINT_ATTEMPT
    #   3) PUNT_ATTEMPT
    KICK_BLOCKED = auto() 
    PENALTY = auto()
    # EventType.BALL_RECOVERED is used for:
    #   1) EventType.FUMBLE RECOVERY
    #   2) EventType.ONSIDE_KICKOFF_ATTEMPT RECOVERY
    RECOVER_BALL = auto()
    TOUCHDOWN = auto()
    SAFETY = auto()


class EventParticipantTypeEnum(Enum):
    PASSER = auto()
    RECEIVER = auto()
    TACKLER = auto()
    DEFENDER = auto()
    BLOCKER = auto()


class EventParticipant:
    def __init__(self, athlete: Athlete, participant_type: EventParticipantTypeEnum):
        self.athlete = athlete
        self.participant_type = participant_type
       
    def __str__(self) -> str:
        return f"PlayParticipant(athlete={self.athlete}, participant_type={self.participant_type})"
   
    def __repr__(self) -> str:
        return self.__str__()
    

class Event:
    def __init__(
        self,
        event_type: EventTypeEnum,
        participants: List[EventParticipant],
        description: str = ""
    ) -> None:
        self.event_type = event_type
        self.participants = participants
        self.description = description

    def __str__(self):
        return f"Event(event_type={self.event_type}, participants={self.participants}, description={self.description})"
   
    def __repr__(self) -> str:
        return self.__str__()