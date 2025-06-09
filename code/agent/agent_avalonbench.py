from agent_base import BaseAgent
from messages import Message, Task, AvalonGameStateUpdate
import numpy as np
from typing import List, Dict, Tuple
import re
import random

# This agent is a signle-file version of the agent in https://github.com/jonathanmli/Avalon-LLM/blob/main/src/server/tasks/avalon/agents/llm_with_discussion.py


from avalonbench.prompts import INTRODUCTION, INFO_ROLE, INFO_YOUR_ROLE, REVEAL_PROMPTS, CHECK_BELIEVED_SIDES_PROMPT, CHOOSE_TEAM_LEADER, VOTE_TEAM_DISCUSSION
from avalonbench.prompts import COTHOUGHT_PROMPT, CHECK_VOTE_ON_TEAM_PROMPT, CHECK_VOTE_ON_QUEST_PROMPT, CHECK_CHOOSE_TEAM_PROMPT, CHECK_ASSASSINATE_PROMPT, CHOOSE_TEAM_ACTION
from avalonbench.prompts import VOTE_TEAM_ACTION, VOTE_MISSION_ACTION, ASSASSINATION_PHASE

class ABenchAgent(BaseAgent):
    def __init__(self, agent_id: str, game_id: str, agent_name: str, config: dict = None):
        super().__init__(agent_id, game_id, agent_name, config)
        self._role_name = ""
        self._num_players = 6
        self._num_good = 4
        self._num_evil = 2
        self._num_merlin = 1
        self._num_percival = 1
        self._num_morgana = 1
        self._initialized = False

        self._prompts = []
        self._state = None
        self._discussion_history = []
        self._observing_discussion_quest = -1
    
    def addMessage(self, message: Message):
        # Handle party votes:
        if message.player == "system" and message.msg.startswith("Party Vote Outcome:"):
            msg = message.msg.split("Party Vote Outcome:")[-1].strip()
            party = self._state.party # These are player IDs [1,6]
            party = ", ".join([f"Player {p}" for p in party])
            votes = [v.split(": ")[1] for v in msg.split(", ")] # Votes are in order of player IDs
            tp, cnts = np.unique(votes, return_counts=True)
            for i in range(len(tp)):
                if tp[i]:
                    cnt = cnts[i]
            if not cnt:
                cnt = 0
            outcome = cnt > len(votes)/2.0
            self.observe_team_result(outcome, party, votes)
        
        # Let's add the remaining messages to the prompts...
        # We need the leader message and then an aggregation of all the messages from other players...
        
        # Let's check if we have a new quest...
        # If so, let's reset the discussion history...
        if message.quest != self._observing_discussion_quest:
            self._observing_discussion_quest = message.quest
            if len(self._discussion_history) > 0:
                self.discussion_end(self._discussion_history)
            self._discussion_history = []

        # We can ignore system messages from here on out...
        if message.player == "system":
            return {}

        # Let's add the message to the discussion history...
        player = f"Player {message.pid}"
        if message.pid == self._state.leader_pid:
            player = f"Leader Player {message.pid}"
        self._discussion_history.append(f"{player}: {message.msg}.")

        return {}
    
    def _setRoleName(self, role: str):
        self._role = role
        if role in ["morgana"]:
            self._role_name = "Minion"
        elif role in ["assassin"]:
            self._role_name = "Assassin"
        elif role in ["servant-1", "servant-2", "percival"]: # Percival is a servant for now...
            self._role_name = "Servant"
        elif role in ["merlin"]:
            self._role_name = "Merlin"
    
    def addState(self, state: AvalonGameStateUpdate):
        # Save the state:
        self._state = state

        # Parse out the role from the state:
        if not self._initialized and state.status == "running":
            self._initialized = True
            self._setRoleName(state.role)
            self._num_players = len(state.players)
            self._side = 0 if self._role in ["assassin", "morgana"] else 1
            self._knowledge = state.knowledge
            self.initialize_game_info()
        return {}
    
    def getAction(self, task: Task, suggestion: str):
        # If we can send a message, do it once per turn...
        if "message" in task.task and task.sequence == 0:
            message = self.team_discussion(self._discussion_history)
            return {"success": True, "action": "message", "data": {"msg": message}}
        # If we have to vote, we need to do it
        elif "vote_quest" in task.task:
            vote = self.vote_on_mission()
            return {"success": True, "action": "vote_quest", "data": {"vote": vote}}
        # If we have to vote on a team, we need to do it
        elif "vote_party" in task.task:
            vote = self.vote_on_team()
            return {"success": True, "action": "vote_party", "data": {"vote": vote}}
        # If we have to vote on the assassin, we need to do it
        elif "vote_assassin" in task.task:
            pid = self.assassinate()
            return {"success": True, "action": "vote_assassin", "data": {"guess": pid}}
        # If we can start a party vote, let's do it
        elif "start_party_vote" in task.task:
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif "propose_party" in task.task and len(self._state.party) != self._state.can_propose_party:
            party = self.propose_team()
            return {"success": True, "action": "propose_party", "data": {"party": party}}

        # If we can't do anything, let's just end our turn...
        return {"success": True, "action": "end_turn"} 
    
    def initialize_game_info(self) -> None:
        """Initiliaze the game info for the agent, which includes game introduction, role, and reveal information for different roles."""
        # Introduction Prompt
        verbal_side = ["Evil", "Good"]
        intro_prompt = INTRODUCTION
        intro_prompt += '\n'
        content_prompt = intro_prompt + INFO_ROLE.format(self._num_players, self._num_good, self._num_merlin, self._num_good - self._num_merlin - self._num_percival, self._num_evil, self._num_evil - self._num_morgana)
        identity_prompt = INFO_YOUR_ROLE.format(f"Player {self._state.pid}", self._role_name, verbal_side[self._side]) # and do not pretend to be other roles throughout the game."
        self.identity_prompt = identity_prompt

        # Reveal Prompt
        pids = [pi[0] for pi in self._knowledge]
        reveal_info = None
        if self._role_name in ["Merlin"]:
            evil = pids
            good = [v+1 for v in range(self._num_players) if v+1 not in evil]
            reveal_info = REVEAL_PROMPTS[self._role_name].format(', '.join([str(v) for v in pids]), ', '.join([str(v) for v in good]))
        elif self._role_name in ["Assassin", "Minion"]:
            evil = pids + [self._state.pid] # Knowledge about self will not be included, so we gotta add that here
            good = [v+1 for v in range(self._num_players) if v+1 not in evil]
            reveal_info = REVEAL_PROMPTS[self._role_name].format(', '.join([str(v) for v in pids]), ', '.join([str(v) for v in good]))
        elif self._role_name == "Percival":
            reveal_info = REVEAL_PROMPTS[self._role_name].format(', '.join([str(v) for v in pids]))

        # Seperately pass the reveal info to the agent, so as to meet the requirement in filer_messages
        # TODO: is `system` allowed? 
        self._prompts.append({
            "role": "user",
            "content": content_prompt,
        })
        if reveal_info:
            self._prompts.append({
                # "role": "system",
                "role": "user",
                "content": identity_prompt + '\n' + reveal_info,
            })
        else:
            self._prompts.append({
                "role": "user",
                "content": identity_prompt,
            })

    def summarize(self):
        """Summarize the game information for the agent."""
        self._prompts.append({
            "role": "user",
            "content": "Please summarize the history. Try to keep all useful information, including your identity, other player's identities, and your observations in the game.",
        })

        response = self._llmInquiry(self._prompts, save_response=False)

        # Make sure the first two prompts are never overwritten (i.e., the ones from initialize_game_info)
        self._prompts = self._prompts[:2]
        # Now add the summary as if it's done by the user...
        self._prompts.append({
            "role": "user",
            "content": response,
        })

    # Runs the current set of prompts...
    def _llmInquiry(self, prompts, save_response = True):
        # Convert the prompts into the format that LLM expects
        messages = []
        for prompt in prompts:
            if not prompt["content"]:
                print("Error: Found a prompt with None content:", prompt)
            messages.append({"role": prompt["role"], "content": prompt["content"]})

        # Now run the prompts through LLM
        response = self._llm_generate(messages)
        if save_response:
            self._prompts.append({"role": "agent", "content": response})

        return response

    def observe_mission(self):
        # This is intentionally left blank...
        # I don't see how the agent would know what the quest status is, but oh well, let's stay consistent with the original code...
        pass
    
    def observe_team_result(self, outcome: bool, team: str, votes: list):
        verbal_vote = {
            0: "reject",
            1: "approve"
        }
        verbalized_result = ""
        if outcome == True:
            verbalized_result = f"The team {team} is approved."
        elif outcome == False:
            verbalized_result = f"The team {team} is rejected."
        else:
            raise ValueError("Invalid outcome %s" % outcome)
        
        for idx, vote in enumerate(votes):
            verbalized_result += f" Player {idx+1} voted {vote}."
        
        self._prompts.append({
            "role": "user",
            "content": verbalized_result,
        })
    
    def get_believed_sides(self):
        self._prompts.append({
            "role": "user",
            "content": "To what extend do you believe each player to be Good, from Player 1 to Player 6? Please output probabilities within [0, 1] and round to two decimal places. If you are not sure, you can simply output 0.5.",
        })
        believed_player_sides = self._llmInquiry(self._prompts)

        # Now let's see if we can parse the results....
        # This is absolutely a job for TypeChat or some structured API, but well... staying consistent with the original code for now...
        templated_response = self._llmInquiry([{
            "role": "user",
            "content": believed_player_sides + '\n\n' + CHECK_BELIEVED_SIDES_PROMPT
        }], save_response=False)
        # "Hope for the best..."
        believed_player_sides = templated_response.split("Answer: ")[-1].strip()
        try:
            believed_player_sides = eval(believed_player_sides)
        except:
            print("Failed to parse believed_player_sides:", believed_player_sides)
            believed_player_sides = {k: 0.5 for k in range(1, self._num_players+1)}
        answer = []
        for i in range(self._num_players):
            if i in believed_player_sides:
                answer.append(believed_player_sides[i])
            else:
                answer.append(0.5)
        return answer
    
    def discussion_end(self, discussion_history: List[str]):
        content_prompt = f"Discussion has ended. Here are the contents, including statements from the leader and words from other players:\n{' '.join(discussion_history)}"
        self._prompts.append({
            "role": "user",
            "content": content_prompt,
        })
        
    def team_discussion(self, discussion_history):
        """Team discussion phase.

        We also summarize the history before this phase at each round. If there's no discussion phase, we summarize the history before the vote phase.
        """
        self.summarize()

        if self._state.pid == self._state.leader_pid:
            content_prompt = CHOOSE_TEAM_LEADER
        else:
            party = self._state.party # These are player IDs [1,6]
            party = ", ".join([f"Player {p}" for p in party])
            content_prompt = ' '.join(discussion_history) + ' ' + VOTE_TEAM_DISCUSSION.format(party)
        
        # Wild guess: let's actually run a prompt here?! This method seems pointless otherwise
        self._prompts.append({
            "role": "user",
            "content": content_prompt
        })
        statement = self._llmInquiry(self._prompts)
        return statement
    
    def propose_team(self):
        def get_team_result(answer: str):
            match_num = r"\d+"
            player_list = []
            
            player_list = re.findall(match_num, answer)

            player_list = [int(id) for id in player_list]

            return player_list
        
        team_size = self._state.can_propose_party
        content_prompt = CHOOSE_TEAM_ACTION.format(team_size, self._num_players)

        thought = COTHOUGHT_PROMPT
        self._prompts.append({
            "role": "user",
            "content": content_prompt + '\n' + thought
        })
        proposed_team = self._llmInquiry(self._prompts)

        # Parse the fun stuff
        input = {
            "role": "user",
            "content": proposed_team + '\n\n' + CHECK_CHOOSE_TEAM_PROMPT
        }
        answer = self._llmInquiry([input], save_response=False)
        answer = get_team_result(answer)
        if len(answer) != team_size:
            # Run another action to get the correct team size
            answer = self._llmInquiry(self._prompts + [{
                "role": "user",
                "content": f"You should choose a team of size {team_size}, instead of size {len(answer)} as you did. Please output a list of player ids with the correct team size."
            }], save_response=False)

            input = {
                "role": "user",
                "content": answer + '\n\n' + CHECK_CHOOSE_TEAM_PROMPT
            }
            answer = self._llmInquiry([input], save_response=False)
            try:
                answer = get_team_result(answer)
                assert len(answer) == team_size
                assert isinstance(answer, list)
            except:
                print("Error: Failed to parse team (choosing randomly instead):", answer)
                answer = random.sample([v for v in range(1, self._num_players+1) if v != self._state.pid], k=team_size-1)
                answer.append(self._state.pid)

        # Wild guess: This has to return something... 
        return answer
    
    def vote_on_team(self):
        def get_vote_result(answer: str):
            match_vote = "Yes|No"
            vote_result = []
            
            vote_result = re.findall(match_vote, answer)

            result = '' if len(vote_result) == 0 else vote_result[-1]

            return result
        """Vote to approve or reject a team.

        If there's no discussion phase, we will summarize the history before the vote phase.
        """
        team = self._state.party
        team = ", ".join([f"Player {p}" for p in team])

        self.summarize()

        content_prompt = VOTE_TEAM_ACTION.format(team)
        
        thought = COTHOUGHT_PROMPT
        self._prompts.append({
            "role": "user",
            "content": content_prompt + "\n" + thought,
        })
        vote_result = self._llmInquiry(self._prompts)

        # Now let's check if it's correct...
        input = {
            "role": "user",
            "content": vote_result + '\n\n' + CHECK_VOTE_ON_TEAM_PROMPT
        }
        answer = self._llmInquiry([input], save_response=False)
        answer = get_vote_result(answer)

        result_dict = {
            "No": 0,
            "Yes": 1
        }

        if answer not in ["No", "Yes"]:
            # Run another action to get the correct vote result
            input = {
                "role": "user",
                "content": f"You surely are a player in the game. Please output `Yes` or `No` to vote on the team."
            }
            answer = self._llmInquiry(self._prompts + [input], save_response=False)

            input = {
                "role": "user",
                "content": answer + '\n\n' + CHECK_VOTE_ON_TEAM_PROMPT
            }
            answer = self._llmInquiry([input], save_response=False)
            answer = get_vote_result(answer)
        try:
            answer = result_dict[answer]
        except:
            print("Error: Failed to parse vote result (approving instead):", answer)
            answer = "Yes"

        return answer == "Yes"
    
    def vote_on_mission(self):
        def get_vote_result(answer: str):
            match_vote = "Yes|No"
            vote_result = []
            
            vote_result = re.findall(match_vote, answer)

            result = '' if len(vote_result) == 0 else vote_result[-1]

            return result
        team = self._state.party
        team = ", ".join([f"Player {p}" for p in team])
        content_prompt = VOTE_MISSION_ACTION.format(list(team))

        thought = COTHOUGHT_PROMPT
        self._prompts.append({
            "role": "user",
            "content": content_prompt + "\n" + thought
        })
        vote_result = self._llmInquiry(self._prompts)

        # Now, let's check the result...
        input = {
            "role": "user",
            "content": vote_result + '\n\n' + CHECK_VOTE_ON_QUEST_PROMPT
        }
        answer = self._llmInquiry([input], save_response=False)
        answer = get_vote_result(answer)

        result_dict = {
            "No": 0,
            "Yes": 1
        }

        if answer not in ["No", "Yes"]:
            # Run another action to get the correct vote result
            input = {
                "role": "user",
                "content": "You surely are a player in the game, and you are a member in the quest. Please output `Yes` or `No` to vote on the quest."
            }
            answer = self._llmInquiry(self._prompts + [input], save_response=False)

            input = {
                "role": "user",
                "content": answer + '\n\n' + CHECK_VOTE_ON_QUEST_PROMPT
            }
            answer = self._llmInquiry([input], save_response=False)
            answer = get_vote_result(answer)
        try:
            answer = result_dict[answer]
        except:
            print("Error: Failed to parse vote result (approving instead):", answer)
            answer = "Yes"
        
        return answer == "Yes"
    
    def assassinate(self):
        def get_assassination_result(message: str, answer: str): 
            match_num = r"\d+"
            player_id = []
                
            player_id = re.findall(match_num, str(message)+str(answer)) 

            player_id = int(player_id[-1])

            return player_id
        
        if self._role_name != "Assassin":
            raise ValueError("Only the Assassin can assassinate.")
        
        thought = COTHOUGHT_PROMPT
        self._prompts.append({
            "role": "user",
            "content": ASSASSINATION_PHASE.format(self.num_players) + "\n" + thought,
        })
        assassinate_result = self._llmInquiry(self._prompts)

        # Now let's check the thing...
        input = {
            "role": "user",
            "content": assassinate_result + '\n\n' + CHECK_ASSASSINATE_PROMPT
        }
        answer = self._llmInquiry([input], save_response=False)
        answer = int(get_assassination_result(assassinate_result, answer))

        if isinstance(assassinate_result, int):
            return assassinate_result
        else:
            print("Error: Failed to parse assassination result (choosing randomly instead):", answer)
            return random.choice([v for v in range(1, self._num_players+1) if v != self._state.pid])