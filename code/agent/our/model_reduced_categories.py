# import seaborn; seaborn.set_style('whitegrid')
import torch

import numpy as np
from tqdm import tqdm


from .pomegranate.distributions import Categorical
from .pomegranate.distributions import JointCategorical
from .pomegranate.distributions import NeuralDistribution
from .pomegranate.distributions import EgoNeuralDistribution
from .pomegranate.factor_graph import FactorGraph

from agent_base import ATEAM

import sys
import argparse
import time
import json
import pandas as pd

from .base_model import BaselModel

def array_filler_evil(number_of_players=6):
    """this function is used to create the array for the evil constraint"""
    array = np.zeros((2,)*number_of_players)
    for i, j, k, l, m, n in np.ndindex(array.shape):
        if sum([i,j,k, l, m, n]) == 2:
            # print([i,j,k, l, m, n] , 2)
            array[i][j][k][l][m][n] = (1 / 15)
        else:
            # print([i,j,k, l, m, n] ,0)
            array[i][j][k][l][m][n] = 0
    # print(array)
    return array

class FactorGraphModelV2(BaselModel):
    def __init__(self, egocentric=True):
        super().__init__(egocentric=egocentric)
    
    def construct(self, hidden_dim=16, num_categories_list=[2, 16, 23, 3, 21, 23, 3, 16, 23, 3, 21, 23, 3, 16, 23, 3],
                     embedding_dim_list=[4, 4, 1, 4, 4, 1, 4, 4, 1, 4, 4, 1, 4, 4, 1]):
        # role variables
        r1 = Categorical([[0.5, 0.5]])
        r2 = Categorical([[0.5, 0.5]])
        r3 = Categorical([[0.5, 0.5]])
        r4 = Categorical([[0.5, 0.5]])
        r5 = Categorical([[0.5, 0.5]])
        r6 = Categorical([[0.5, 0.5]])
        # party 1 will have 15 possible configurations
        p1 = Categorical([[1/16,]*16])
        # party 2 will have 20 possible configurations
        p2 = Categorical([[1/21,]*21])
        # party 3 will have 15 possible configurations
        p3 = Categorical([[1/16,]*16])
        # party 4 will have 20 possible configurations
        p4 = Categorical([[1/21,]*21])
        # party 5 will have 15 possible configurations
        p5 = Categorical([[1/16,]*16])

        # each vote will have 2**6 possible configurations
        v1 = Categorical([[1/23,]*23])
        v2 = Categorical([[1/23,]*23])
        v3 = Categorical([[1/23,]*23])
        v4 = Categorical([[1/23,]*23])
        v5 = Categorical([[1/23,]*23])

        # outcomes can be either success (2) or fail (1) or unknown (0)
        o1 = Categorical([[1/3,]*3])
        o2 = Categorical([[1/3,]*3])
        o3 = Categorical([[1/3,]*3])
        o4 = Categorical([[1/3,]*3])
        o5 = Categorical([[1/3,]*3])

        # num_categories_list = [2, 16, 65, 3, 21, 65, 3, 16, 65, 3, 21, 65, 3, 16, 65, 3]
        # embedding_dim_list = [4, 8, 2, 5, 8, 2, 4, 8, 2, 5, 8, 2, 4, 8, 2]  # Specify embedding dimensions for each variable

        # hidden_dim = 32
        # hidden_dim = 16
        # hidden_dim = 8
        output_dim = 1

        # DONE: change the from_file configuration to be from the train function
        if self.egocentric: 
            EgoNeuralDistribution.initialize(num_categories_list, embedding_dim_list, hidden_dim, output_dim)
            f1 = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=0, graph=True)
            f2 = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=1, graph=True)
            f3 = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=2, graph=True)
            f4 = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=3, graph=True)
            f5 = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=4, graph=True)
            f6 = EgoNeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name=5, graph=True)
            
        else:

            f1 = NeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name="f1", from_file=True, graph=True)
            f2 = NeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name="f2", from_file=True, graph=True)
            f3 = NeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name="f3", from_file=True, graph=True)
            f4 = NeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name="f4", from_file=True, graph=True)
            f5 = NeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name="f5", from_file=True, graph=True)
            f6 = NeuralDistribution(num_categories_list, embedding_dim_list, hidden_dim, output_dim, name="f6", from_file=True, graph=True)

        evil_array = array_filler_evil(6)
        f_evil_constraint = JointCategorical(evil_array/np.sum(evil_array), frozen=True)

        # add the nodes to the model
        self.model.add_factor(f1)
        self.model.add_factor(f2)
        self.model.add_factor(f3)
        self.model.add_factor(f4)
        self.model.add_factor(f5)
        self.model.add_factor(f6)
        self.model.add_factor(f_evil_constraint)

        self.model.add_marginal(r1)
        self.model.add_marginal(r2)
        self.model.add_marginal(r3)
        self.model.add_marginal(r4)
        self.model.add_marginal(r5)
        self.model.add_marginal(r6)

        self.model.add_marginal(p1)
        self.model.add_marginal(v1)
        self.model.add_marginal(o1)

        self.model.add_marginal(p2)
        self.model.add_marginal(v2)
        self.model.add_marginal(o2)

        self.model.add_marginal(p3)
        self.model.add_marginal(v3)
        self.model.add_marginal(o3)

        self.model.add_marginal(p4)
        self.model.add_marginal(v4)
        self.model.add_marginal(o4)

        self.model.add_marginal(p5)
        self.model.add_marginal(v5)
        self.model.add_marginal(o5)

        # add edges for factor 1:
        self.model.add_edge(r1, f1)
        self.model.add_edge(p1, f1)
        self.model.add_edge(v1, f1)
        self.model.add_edge(o1, f1)
        self.model.add_edge(p2, f1)
        self.model.add_edge(v2, f1)
        self.model.add_edge(o2, f1)
        self.model.add_edge(p3, f1)
        self.model.add_edge(v3, f1)
        self.model.add_edge(o3, f1)
        self.model.add_edge(p4, f1)
        self.model.add_edge(v4, f1)
        self.model.add_edge(o4, f1)
        self.model.add_edge(p5, f1)
        self.model.add_edge(v5, f1)
        self.model.add_edge(o5, f1)

        # add edges for factor 2:
        self.model.add_edge(r2, f2)
        self.model.add_edge(p1, f2)
        self.model.add_edge(v1, f2)
        self.model.add_edge(o1, f2)
        self.model.add_edge(p2, f2)
        self.model.add_edge(v2, f2)
        self.model.add_edge(o2, f2)
        self.model.add_edge(p3, f2)
        self.model.add_edge(v3, f2)
        self.model.add_edge(o3, f2)
        self.model.add_edge(p4, f2)
        self.model.add_edge(v4, f2)
        self.model.add_edge(o4, f2)
        self.model.add_edge(p5, f2)
        self.model.add_edge(v5, f2)
        self.model.add_edge(o5, f2)

        # add edges for factor 3:
        self.model.add_edge(r3, f3)
        self.model.add_edge(p1, f3)
        self.model.add_edge(v1, f3)
        self.model.add_edge(o1, f3)
        self.model.add_edge(p2, f3)
        self.model.add_edge(v2, f3)
        self.model.add_edge(o2, f3)
        self.model.add_edge(p3, f3)
        self.model.add_edge(v3, f3)
        self.model.add_edge(o3, f3)
        self.model.add_edge(p4, f3)
        self.model.add_edge(v4, f3)
        self.model.add_edge(o4, f3)
        self.model.add_edge(p5, f3)
        self.model.add_edge(v5, f3)
        self.model.add_edge(o5, f3)

        # add edges for factor 4:
        self.model.add_edge(r4, f4)
        self.model.add_edge(p1, f4)
        self.model.add_edge(v1, f4)
        self.model.add_edge(o1, f4)
        self.model.add_edge(p2, f4)
        self.model.add_edge(v2, f4)
        self.model.add_edge(o2, f4)
        self.model.add_edge(p3, f4)
        self.model.add_edge(v3, f4)
        self.model.add_edge(o3, f4)
        self.model.add_edge(p4, f4)
        self.model.add_edge(v4, f4)
        self.model.add_edge(o4, f4)
        self.model.add_edge(p5, f4)
        self.model.add_edge(v5, f4)
        self.model.add_edge(o5, f4)

        # add edges for factor 5:
        self.model.add_edge(r5, f5)
        self.model.add_edge(p1, f5)
        self.model.add_edge(v1, f5)
        self.model.add_edge(o1, f5)
        self.model.add_edge(p2, f5)
        self.model.add_edge(v2, f5)
        self.model.add_edge(o2, f5)
        self.model.add_edge(p3, f5)
        self.model.add_edge(v3, f5)
        self.model.add_edge(o3, f5)
        self.model.add_edge(p4, f5)
        self.model.add_edge(v4, f5)
        self.model.add_edge(o4, f5)
        self.model.add_edge(p5, f5)
        self.model.add_edge(v5, f5)
        self.model.add_edge(o5, f5)

        # add edges for factor 6:
        self.model.add_edge(r6, f6)
        self.model.add_edge(p1, f6)
        self.model.add_edge(v1, f6)
        self.model.add_edge(o1, f6)
        self.model.add_edge(p2, f6)
        self.model.add_edge(v2, f6)
        self.model.add_edge(o2, f6)
        self.model.add_edge(p3, f6)
        self.model.add_edge(v3, f6)
        self.model.add_edge(o3, f6)
        self.model.add_edge(p4, f6)
        self.model.add_edge(v4, f6)
        self.model.add_edge(o4, f6)
        self.model.add_edge(p5, f6)
        self.model.add_edge(v5, f6)
        self.model.add_edge(o5, f6)

        self.model.add_edge(r1, f_evil_constraint)
        self.model.add_edge(r2, f_evil_constraint)
        self.model.add_edge(r3, f_evil_constraint)
        self.model.add_edge(r4, f_evil_constraint)
        self.model.add_edge(r5, f_evil_constraint)
        self.model.add_edge(r6, f_evil_constraint)
    
    def train(self, history_vector, history_valid, save_directory="v1/"):
        """Train the model on the history vector, save models into a specific directory once they are finished"""
        super().train(history_vector, history_valid, save_directory=save_directory)
        # history_vector = torch.tensor(history_vector, dtype=torch.int32)
        # self.model.fit(history_vector, X_valid=history_valid, from_file=save_directory)
        # raise NotImplementedError("Must be implemented in subclass")
    
    # DONE chang ethe factor graph training to use folder path for loading and saving the model
    def load_from_file(self, folder_path="v2/"):
        """All model files should be stored in a specific folder"""
        super().load_from_file(folder_path)
    
    def predict_probs(self, game_state, self_role, self_index, algorithm="sum"):
        """
        Game state is given as a vector
        the algorithm can be either "max" or "sum" for max-product or sum-product
        returns a dictionary of probabilities for each player
        The format of the results is {'player_1': {'good': 0.5, 'evil': 0.5}, ...}
        """
        assert algorithm in ["max", "sum"]

        # algorithm = "sum"

        if self_role == ATEAM.GOOD:
            game_state[self_index] = 0
        elif self_role == ATEAM.EVIL:
            game_state[self_index] = 1
        else:
            raise ValueError("Role must be either good or evil")
        X_torch = torch.tensor(game_state, dtype=torch.int32)

        mask_array = ([False,]*6) + ([True,]*15)  # mask the game state vector for the values we want to predict
        mask_array[self_index] = True # we know the role of ourslef
        # mask_array[5] = True
        # print(self.model.marginals[5].probs)
        mask = torch.tensor([mask_array])
        X_masked = torch.masked.MaskedTensor(X_torch.unsqueeze(0), mask=mask)


        start_time = time.time()
        predicted_prob = self.model.predict_proba(X_masked, alg=algorithm)
        end_time = time.time()
        print(f"Time taken to run predict_proba: {end_time - start_time} seconds")

        results = {}
        for i in range(6):
            results[i+1] = {'good': predicted_prob[i][0][0].item(),
                                        'evil': predicted_prob[i][0][1].item()}
        return results

    def update_priors(self, priors):
        """Update the priors of the model
            priors should be in the form of {1: {"evil": 0.5, "good":0.5}, 2: ...}
        """
        # Since the role marginals are always the first marginals added to the factor graph structure, we have to update the marginal probs of the first 6 nodes.
        for index, probs in priors.items():
            self.model.marginals[index-1].update_probs([[probs['good'], probs['evil']]])

