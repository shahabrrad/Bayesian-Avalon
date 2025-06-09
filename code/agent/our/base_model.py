# import seaborn; seaborn.set_style('whitegrid')
from enum import Enum
import torch

import numpy as np
from tqdm import tqdm

# from pomegranate.distributions import Categorical
# from pomegranate.distributions import JointCategorical
# from pomegranate.distributions import NeuralDistribution
# from pomegranate.distributions import EgoNeuralDistribution
from .pomegranate.factor_graph import FactorGraph

from agent_base import ATEAM

import sys
import argparse
import time
import json
import pandas as pd

# class ATEAM(Enum):
#     GOOD = 1
#     EVIL = 2

class BaselModel(object):
    def __init__(self, egocentric=True):
        self.egocentric = egocentric
        self.model = FactorGraph()
    
    def construct(self, num_categories_list, embedding_dim_list, hidden_dim):
        raise NotImplementedError("Must be implemented in subclass")
    
    def train(self, history_vector, history_valid, save_directory="base"):
        """Train the model on the history vector, save models into a specific directory once they are finished"""
        history_vector = torch.tensor(history_vector, dtype=torch.int32)
        self.model.fit(history_vector, X_valid=history_valid, from_file=save_directory)
    
    # DONE chang ethe factor graph training to use folder path for loading and saving the model
    def load_from_file(self, folder_path="/base/"):
        """All model files should be stored in a specific folder"""
        # if not self.model.trained:
        #     raise ValueError("Model is not trained yet")
        # self.model.fit([], X_valid=[], from_file=folder_path)
        self.model.load_from_file(folder_path)
    
    def predict_probs(self, game_state, self_role, self_index, algorithm="max"):
        """
        Game state is given as a vector
        the algorithm can be either "max" or "sum" for max-product or sum-product
        returns a dictionary of probabilities for each player
        The format of the results is {1: {'good': 0.5, 'evil': 0.5}, ...}
        """

        raise NotImplementedError("Must be implemented in subclass")
    
    
    def update_priors(self, priors):
        """Update the priors of the model"""
        raise NotImplementedError("Must be implemented in subclass")