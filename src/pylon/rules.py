# from abc import ABC, abstractmethod
# from .state import GameState


# class Rule(ABC):
#     """Base class for all rules."""

#     def on_game_start(self, state: GameState) -> None:
#         pass

#     def on_period_start(self, state: GameState) -> None:
#         pass

#     def on_play_end(self, state: GameState) -> None:
#         pass

#     def on_overtime_start(self, state: GameState) -> None:
#         pass

#     def on_game_end(self, state: GameState) -> None:
#         pass


# class TimingRule(Rule):
#     """Rules that affect the game clock."""

#     pass


# class LengthOfGameRule(TimingRule):
#     # number and length of periods
#     ...


# class CoinTossRule(TimingRule):
#     # coin toss caller (home/away) as well ask other specific rules
#     # like The opportunity to receive the kickoff, or to kick off; or
#     # The choice of goal his team will defend. Also half time rules
#     # too
#     # part of this may belong in Event
#     ...


# class FreeKickDownRule(TimingRule):
#     # The game clock operator shall start the game clock (time in) after a free kick when the ball is legally touched in the field of play. The game clock shall not start if:
#     # the receiving team recovers the ball in the end zone and does not carry the ball into the field of play;
#     # the kicking team recovers the ball in the field of play (prior to any other legal touching);
#     # the receiving team signals for and makes a fair catch
#     ...


# class ScrimmageDownRule(TimingRule):
#     # Following any timeout (3-36-1), the game clock shall be started on a scrimmage down when the ball is next snapped, except in the following situations:
#     # Whenever a runner goes out of bounds on a play from scrimmage, the game clock is started on the Referee’s signal that a ball has been returned to play, except that the clock will start on the snap:
#     # after a change of possession;
#     # after the two-minute warning of the first half; or
#     # inside the last five minutes of the second half.
#     # If there is an injury timeout prior to the two-minute warning, the game clock is started as if the injury timeout had not occurred.
#     # If there is an excess team timeout after the two-minute warning, the game clock is started as if the excess timeout had not occurred, unless the opponent chooses to have the clock start on the snap.
#     # If there is a Referee’s timeout, the game clock is started as if the Referee’s timeout had not occurred.
#     # If the game clock is stopped after a down in which there was a foul by either team, following enforcement or declination of a penalty, the game clock will start as if the foul had not occurred, except that the clock will start on the snap if:
#     # the foul occurs after the two-minute warning of the first half;
#     # the foul occurs inside the last five minutes of the second half;
#     # the offense commits a foul during the fourth period or regular season overtime after the ball has been made ready for play, causing the clock to stop before a snap;
#     # the offense commits two successive delay of game penalties during the same down while time is in (see 12-3-1-n); or
#     # a specific rule prescribes otherwise.
#     # If a fumble or backward pass by any player goes out of bounds, the game clock starts on the Referee’s signal that a ball has been returned to the field of play.
#     # When there is a 10-second runoff, the game clock starts when the Referee signals that the ball is ready for play.
#     # During the Try, which is an untimed down.
#     # When a specific rule prescribes otherwise.
#     ...


# class FairCatchKickDownRule(TimingRule):
#     # The game clock operator shall start the game clock for a fair-catch kick down when the ball is kicked.
#     ...
