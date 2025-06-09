from agent_base import BaseAgent, LLM
from messages import Message, AvalonGameStateUpdate, Task
import random

# This is the test agent, which is a very simple agent that just randomly chooses actions and writes pointless messages
# However, this agent is capable to "play", or rather "progress" the game.
class TestAgent(BaseAgent):
    def __init__(self, agent_id: str, game_id: str, agent_name: str, agent_role_preference: str, config: dict):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)
        self._last_action = None
    
    def addMessage(self, message: Message):
        # print("Received message", message.msg)
        return {}
    
    def addState(self, state: AvalonGameStateUpdate):
        # print("Received state", state)
        return {}
    
    def getAction(self, task: Task, suggestion: str):
        taken_action = suggestion
        print("#" * 100)
        print("Test Agent:", self._name, f"({self._private_data.role})", "-> Choosing action:", taken_action) 
        print("#" * 100)
        
        # The choices should be pretty self-explanatory
        if taken_action == "message":
            # Randomly just end our turn
            # Just end turn here for random agents
            #return {"success": True, "action": "end_turn"}
            #if random.random() < 0.5 and task.sequence > 0:
            #    print(" --> Ending turn")
            #    return {"success": True, "action": "end_turn"}
            #prompt = f"You are a player in the game of Avalon, named {self._name}. Can you say hello to the rest of the group? Only respond from the perspective of {self._name}. Don't be overly verbose or enthusiastic, but say a few words."
            #result = self._llm_generate(message=prompt, model=LLM.LOCAL)
            #result = result.choices[0].message.content
            #print(" --> Sending message", result)
            return {"success": True, "action": "message", "data": {"msg": f"Idk rn tbh"}}
        elif taken_action == "vote_quest":
            return {"success": True, "action": "vote_quest", "data": {"vote": random.choice([True, False])}}
        elif taken_action == "vote_party":
            # return {"success": True, "action": "vote_party", "data": {"vote": random.choice([True, False])}}
            # For now, let's just always vote yes for testing TODO change this back
            return {"success": True, "action": "vote_party", "data": {"vote": True}}

        elif taken_action == "vote_assassin":
            return {"success": True, "action": "vote_assassin", "data": {"guess": random.choice([1, 2, 3, 4, 5, 6])}} # Choose a random player ID
        elif taken_action == "start_party_vote":
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif taken_action == "propose_party":
            return {"success": True, "action": "propose_party", "data": {"party": random.sample([1, 2, 3, 4, 5, 6], k=task.target_party_size)}} # Choose a random party
        elif taken_action == "end_turn":
            return {"success": True, "action": "end_turn"}
        else:
            return {"success": False, "message": "Unknown action option"}