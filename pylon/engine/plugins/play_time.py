# src\pylon\engine\plugins\play_type.py
from abc import abstractmethod
import importlib.resources
import random

import joblib
import pandas as pd

from pylon.engine.plugins.base import GamePluginModel

class PlayTimeModel(GamePluginModel):
    @abstractmethod
    def run(self, game_state, *args, **kwargs) -> dict:
        """Run logic with access to full game state."""
        pass

class DefaultPlayTimeModel(PlayTimeModel):
    def __init__(self):
        super().__init__()
        
    def inputs_to_df(self, game_state, play_call, play_result):
        score = game_state.get_score()
        pos_team = game_state.possession
        def_team = game_state.away_team if pos_team == game_state.home_team else game_state.home_team
        return pd.DataFrame([{
            'quarter': game_state.clock.quarter,
            'game_seconds_remaining': game_state.clock.total_time_sec,
            'posteam_score': score[pos_team],
            'defteam_score': score[def_team],
            'down': game_state.down,
            'ydstogo': game_state.distance,
            'yardline_100': game_state.ball_position,
            'posteam_timeouts_remaining': game_state.timeouts[pos_team],
            'defteam_timeouts_remaining': game_state.timeouts[def_team],
            'is_clock_running': play_result.get('is_clock_running', False),
            'yards_gained': play_result.get('yards', 0),
            'play_type': play_call.get('type').name, 
        }])
        
    def make_prediction(self, game_state, play_call, play_result):
        # df = self.inputs_to_df(game_state, play_call, play_result)
        return random.randint(8,30)
        
    def run(self, game_state, play_call, play_result, seed):
        return {'time_elapsed': self.make_prediction(game_state, play_call, play_result)}