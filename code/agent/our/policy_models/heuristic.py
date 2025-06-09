"""This class uses a simple heuristic to select actions for the agent:
 vote no on parties with evil players
 propose parties with the highest probability of the good players
"""

from enum import Enum
from agent_base import ATEAM
import random

# class ATEAM(Enum):
#     GOOD = 1
#     EVIL = 2


class HeuristicOracle(object):
    def __init__(self, role):
        self.role = role    # good is 1, evil is 2. This will be of type ATEAM

    def get_action(self, state):
        """place holder for action selection funciton. Right now this does nothing"""
        return {}
    
    def opinion_on_party(self, party, probabilities):
        """"Do not accept parties with evil players"""
        for memeber in party:
            if probabilities[memeber]['evil'] > probabilities[memeber]['good']:
                return False
        return True

    
    def vote_for_party(self, party, probabilities):
        """"Do not vote for a party that you think has evil players"""
        # TODO we will have to change this if the agent can be evil.
        if len(party) == 2: # always agree to the first party
            return True
        if probabilities == None:
            raise ValueError("Probabilities are None")
        for memeber in party: # TODO change this so that these are the top k players in the party
            # add a threshold of confidence: if you think the guy is more than 65% evil, then vote no
            if (probabilities[memeber]['evil'] - probabilities[memeber]['good']) > 0:
                return False
        return True
    
    def propose_party(self, party_size, probabilities):
        """"This will propose a party with the highest n good players"""
        players_in_oreder = self.order_players(probabilities)
        if party_size ==2:
            return [players_in_oreder[0], random.choice(players_in_oreder[1:])]
        return players_in_oreder[:party_size]
    
    def vote_for_quest(self):
        """if you are evil, fail the quest if you are good, pass the quest"""
        if self.role == ATEAM.EVIL:
            return False
        return True

    def order_players(self, probabilities):
        """Order players by the probability of being good"""
        return sorted(probabilities.keys(), key=lambda x: probabilities[x]['good'], reverse=True)