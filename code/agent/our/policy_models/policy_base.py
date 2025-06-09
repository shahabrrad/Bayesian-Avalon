"""The base class that selects actions of the agent in the game
The functions should be implemented int the subclasses
"""



class BaseOracle(object):
    def __init__(self, role):
        self.role = role

    def get_action(self, state):
        """place holder for action selection funciton. Right now this does nothing because the action is selected within the agent"""
        return {}
    
    def opinion_on_party(self, party, probabilities):
        raise NotImplementedError("Must be implemented in subclass")
        # return self.env.action_space.sample()
    
    def vote_for_party(self, party, probabilities):
        """TODO In later versions of the policy oracle, this will include the history of the dialogue
        This history of dialogue can be used to change the opinion of the agent on the party"""

        raise NotImplementedError("Must be implemented in subclass")
        # return self.env.action_space.sample()
    
    def propose_party(self, party_size, probabilities):
        raise NotImplementedError("Must be implemented in subclass")
        # return self.env.action_space.sample()
    
    def vote_for_quest(self, quest):
        raise NotImplementedError("Must be implemented in subclass")
        # return self.env.action_space.sample()
    
    def chose_assassin_target(self, probabilities):
        raise NotImplementedError("Must be implemented in subclass")