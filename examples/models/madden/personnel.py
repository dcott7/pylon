from typing import Dict, List

from pylon.domain.athlete import Athlete, AthletePositionEnum
from pylon.models.personnel import (
    PlayerAssignmentContext,
    RusherSelectionContext,
    PasserSelectionContext,
    TargettedSelectionContext,
    PunterSelectionContext,
    PuntReturnerSelectionContext,
    KickerSelectionContext,
    PlaceKickerSelectionContext,
    KickoffReturnerSelectionContext,
    OffensivePlayerAssignmentModel,
    DefensivePlayerAssignmentModel,
    RusherSelectionModel,
    PasserSelectionModel,
    TargettedSelectionModel,
    PunterSelectionModel,
    PuntReturnerSelectionModel,
    KickerSelectionModel,
    PlaceKickerSelectionModel,
    KickoffReturnerSelectionModel
)


class MaddenOffensivePlayerAssignmentModel(OffensivePlayerAssignmentModel):
    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        ...

class MaddenDefensivePlayerAssignmentModel(DefensivePlayerAssignmentModel):
    def execute(
        self, context: PlayerAssignmentContext
    ) -> Dict[AthletePositionEnum, List[Athlete]]:
        ...
        
class MaddenRusherSelectionModel(RusherSelectionModel):
    def execute(self, context: RusherSelectionContext) -> Athlete:
        ...

class MaddenPasserSelectionModel(PasserSelectionModel):
    def execute(self, context: PasserSelectionContext) -> Athlete:
        ...

class MaddenTargettedSelectionModel(TargettedSelectionModel):
    def execute(self, context: TargettedSelectionContext) -> Athlete:
        ...

class MaddenPunterSelectionModel(PunterSelectionModel):
    def execute(self, context: PunterSelectionContext) -> Athlete:
        ...

class MaddenPuntReturnerSelectionModel(PuntReturnerSelectionModel):
    def execute(self, context: PuntReturnerSelectionContext) -> Athlete:
        ...

class MaddenKickerSelectionModel(KickerSelectionModel):
    def execute(self, context: KickerSelectionContext) -> Athlete:
        ...

class MaddenPlaceKickerSelectionModel(PlaceKickerSelectionModel):
    def execute(self, context: PlaceKickerSelectionContext) -> Athlete:
        ...

class MaddenKickoffReturnerSelectionModel(KickoffReturnerSelectionModel):
    def execute(self, context: KickoffReturnerSelectionContext) -> Athlete:
        ...
