import json
from agent_base import BaseAgent, LLM, LLM, ATEAM, AROLE
from messages import Message, AvalonGameStateUpdate, Task, AvalonGameState
import random
from itertools import combinations
import time
from our.model_reduced_categories import FactorGraphModelV2
from our.policy_models.heuristic import HeuristicOracle
import os
import csv
from our.prompts import PromptHint
from agent_acl import ACLAgent



class ACLAgentGraphOnly(ACLAgent):
    def __init__(self, agent_id: str, game_id: str, agent_name: str, agent_role_preference: str, config: dict = None):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)

    #overwriting this funciton from the ACLAgent class
    def get_llm_vibes_agreement(self, chat):
        probs = {self.game.index_to_players[1]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[2]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[3]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[4]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[5]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[6]: {"evil":0.5, "good":0.5},
                        }
        
        self.debug(f"===== LLM vibes got priors updated: {probs}\n")

        return probs