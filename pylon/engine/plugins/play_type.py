# src\pylon\engine\plugins\play_type.py
from abc import abstractmethod
import importlib.resources
import random

import joblib
import pandas as pd

from pylon.engine.plugins.base import GamePluginModel
from pylon.model.game.play import PlayType

class PlayTypeModel(GamePluginModel):
    @abstractmethod
    def run(self, game_state, *args, **kwargs) -> dict:
        """Run logic with access to full game state."""
        pass

class DefaultPlayTypeModel(PlayTypeModel):
    def __init__(self):
        super().__init__()
        with importlib.resources.open_binary('pylon.engine.plugins.models.coaching', 'rf_play_call_model.pkl') as f:
            self.model = joblib.load(f)
        with importlib.resources.open_binary('pylon.engine.plugins.models.coaching', 'play_type_label_encoder.pkl') as f:
            self.label_encoder = joblib.load(f)
    
    def game_state_to_df(self, game_state):
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
            'is_clock_running': int(game_state.clock.is_running)
        }])
    
    def predict_most_likely(self, game_state):
        gs = self.game_state_to_df(game_state)
        prediction = self.model.predict(gs)
        play_type_str = self.label_encoder.inverse_transform(prediction)
        return PlayType[play_type_str[0]]

    def predict_all(self, game_state):
        gs = self.game_state_to_df(game_state)
        probas = self.model.predict_proba(gs)[0]
        class_labels = self.label_encoder.inverse_transform(self.model.classes_)
        predictions = [(PlayType[label], prob) for label, prob in zip(class_labels, probas)]
        return dict(sorted(predictions, key=lambda x: x[1], reverse=True))
    
    def run(self, game_state, seed=None):
        prob_dist = self.predict_all(game_state)
        play_types = list(prob_dist.keys())
        probabilities = list(prob_dist.values())
        
        rng = random.Random(seed)
        selected = rng.choices(play_types, weights=probabilities, k=1)[0]
        return {'type': selected}