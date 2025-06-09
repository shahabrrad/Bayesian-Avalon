import json
from agent_base import BaseAgent, LLM, LLM, ATEAM, AROLE
from agent_acl import ACLAgent, GameInfo
from messages import Message, AvalonGameStateUpdate, Task, AvalonGameState
import random
from itertools import combinations
import time
from our.model_reduced_categories import FactorGraphModelV2
from our.policy_models.heuristic import HeuristicOracle
import os
import csv
from our.prompts import PromptHint

class ACLAgentLLMOnly(ACLAgent):
    def __init__(self, agent_id: str, game_id: str, agent_name: str, agent_role_preference: str, config: dict = None):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)

    # overwriting this funciton from the ACLAgent class
    def update_predictions(self, probs, with_llm_prior=False):
        """Let's get the beliefs from the latest game state vector"""
        self.debug(f"-- The quest history for vector generation: {self.game.quest_proposals}\n")
        self.debug(f"-- The outcome history for vector generation: {self.game.quest_results}\n")
        state_vector = self.game.get_state_vector()
        self.debug(f"-- Updating beliefs with state vector: {state_vector} \n")
        self.latest_probabilities = probs
        self.quest_updated = False
        self.debug(f"       -- BELIEF UPDATED: {self.latest_probabilities}\n")
        if with_llm_prior:
            self.log (f" ***  BELIEFS with Vibes: {self.latest_probabilities}\n")
        else:
            self.log (f" ***  BELIEFS: {self.latest_probabilities}\n")
        return {}
    

    #overwriting this function from the ACLAgent class
    def update_predictions_based_on_chat(self, chat):
        probs = self.get_llm_vibes_agreement(chat)
        self.log("             UPDATING PRIORS           \n")
        self.update_predictions(probs)
