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



class GameInfo():
    """A class to save and store information about the state of the game"""
    def __init__(self):
        self.players_to_index = {}
        self.index_to_players = {}
        self.state = AvalonGameState()
        self.state_diff = {}
        self.party_leader = None
        self.current_proposed_party = None # ["name of player 1", "name of player 2", ...]

        # votes within the proposals should be in the form of {name:true/false, ...}
        # each proposal entry should be in the form of {'comp': [name1, name2, ...], 'votes': {name1: True, name2: False, ...}}
        # this only contains the parties that have been voted on
        self.quest_proposals = {
            1: [], 2: [], 3: [], 4: [], 5: []
        }
        self.quest_results = [] # True for success, False for fail
        self.current_party_rejects = []
    
    def add_party_proposal(self, party_comp, party_votes, quest_number):
        self.quest_proposals[quest_number].append({'comp': [name.lower() for name in party_comp],
                                                   'votes': party_votes})
        if sum(party_votes.values()) > 3: # the party has been accepted
            self.current_party_rejects = []
            print( f"Party {party_comp} has been accepted for quest {quest_number} with votes: {party_votes}")
        else:
            self.current_party_rejects.append(party_comp)
            print(f"Party {party_comp} has been rejected for quest {quest_number} with votes: {party_votes}")
    
    def add_quest_result(self, result):
        self.quest_results.append(result)
    
    def get_state_vector(self):
        """Turns the game state into a vector to be used by the graphical model"""
        roles = [0, 0, 0, 0, 0, 0]
        state_vector = roles

        possible_vote_compositions = [] # this variable is used to find the index of the votes composition
        for L in range(4, 6 + 1): 
            for subset in combinations([1,2,3,4,5,6], L):
                possible_vote_compositions.append(subset)

        for i in range(5):  # add each quest information to the array
            if i < len(self.quest_results): # this quest has not finished yet.
                party = self.quest_proposals[i+1][-1]['comp']
                votes = self.quest_proposals[i+1][-1]['votes']
                print("+++++++++", party, votes)
                party_numbers = tuple(sorted([self.players_to_index[name.lower()] for name in party]))
                vote_numbers = tuple(sorted([self.players_to_index[name.lower()] for name in votes if votes[name.lower()]]))
                party_index = list(combinations([1,2,3,4,5,6], len(party_numbers))).index(party_numbers)
                vote_index = possible_vote_compositions.index(vote_numbers)
                quest_vector = [party_index+1, vote_index+1, int(self.quest_results[i])+1]
            else:
                quest_vector = [0, 0, 0]
            state_vector.extend(quest_vector)
        return state_vector

    def failed_proposals(self):
        """returns the number of failed proposals"""
        return len([r for r in self.quest_proposals[len(self.quest_results)+1] if not r])



# This is the GRAIL agent that uses the graphical model. We can change this to create variations
class ACLAgent(BaseAgent):
    def __init__(self, agent_id: str, game_id: str, agent_name: str, agent_role_preference: str, config: dict = None):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)

        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Create a log file
        self._log_file = f"logs/LOG_({self._name})_{game_id}.log"
        self._debug_log_file = f"logs/DEBUG_({self._name})_{game_id}.log"
        self._llm_log_file = f"logs/LLM_({self._name})_{game_id}.log"
        self.csv_file = f"logs/CSV_({self._name})_{game_id}.csv"

        self.debug(f"""Log file created for agent {self._name} with ID {self._id} in game {self._gid}
                 Agent role is: {agent_role_preference}\n\n\n""")
        
        self.log(f"Agent {self._name} with ID {self._id} and type ACL is starting...Agent role is: {agent_role_preference}\n")

        self._last_action = None
        self._role = self._roleToEnum(agent_role_preference)
        self.role_string = agent_role_preference
        self._team = (
            ATEAM.EVIL if self._role in [AROLE.MORGANA, AROLE.ASSASSIN] else ATEAM.GOOD # good is 1, evil is 2
        )
        self.graph_model = FactorGraphModelV2()
        self.graph_model.construct()
        self.graph_model.load_from_file()

        # the party that is proposed and is being discussed
        self.self_proposed_party = None # this will hold the party that the agent proposed

        self.latest_probabilities = None # {"name of player": {'good': 0.5, 'evil': 0.5}, ...}
        self.game = GameInfo()
        self.policy_selector = HeuristicOracle(self._team)
        self.quest_updated = False # a flag to know to update the beliefs after the quest is updated

        self._messages = []
        self._last_action = []
        self._turn = 0
        self._prompt_hint = PromptHint
        self.game_log = []

        self.vote_next = False # this is used to check if the agent has to vote for the party

        self.reset_logs_on_round = True  # True has the unwanted effect that the agent cannot retrieve previous info in the messages. for example it says person x was in a failed mission but it was not
        self.party_leader = None
        self.quest_history = []
    
    def addMessage(self, message: Message):
        # log the recieved message
        self.debug(f"-- Message recieved: {message}\n")

        # save the vote for a party
        if message.player == "system" and message.msg.startswith("Party vote summary:"):
            msg = message.msg.split("Party vote summary:")[-1].strip()
            votes = {}
            # turn the votes from yes/no to True/False
            for v in msg.split(", "):
                name, vote = v.split(": ")
                if vote.lower() == "yes":
                    votes[name.lower()] = True
                elif vote.lower() == "no":
                    votes[name.lower()] = False
            print("*********  votes", votes)
            self.game.add_party_proposal(self.game.current_proposed_party, votes, len(self.game.quest_results)+1)

        return {}
    
    def addState(self, state: AvalonGameStateUpdate):
        print("recieved state update")

        self.game.state = self.state
        self.game.state_diff = self.state_diff

        self.debug(f"++ State diff recieved: {self.state_diff}\n")

        if "turn" in self.state_diff:
            self._turn = self.state_diff["turn"]
            self._last_action = []
            self.debug(f"########### Turn updated: {self.state_diff['turn']}\n")

        if "quest" in self.state_diff:
            self.debug(f"########### Quest updated: {self.state_diff['quest']}\n")
            self.round = self.state.quest

            if self.reset_logs_on_round:
                self.game_log = []

            if self.state_diff["quest"] == 1:
                self.game_log.append(
                    ["Game Start",
                    "Welcome to Avalon Game. This message signifies the start of a new game. "
                    "All previous information, such as completed tasks or team alignments, is reset. "
                    "The game history from this line onwards is the effective historical game history dialogue of this game!",]
                )
            self.game.current_proposed_party = None
        
        # Track round results
        if "quest_results" in self.state_diff:
            self.debug(f"########### Quest results updated: {self.state_diff['quest_results']}\n")
            result = self.state_diff["quest_results"][-1].lower()
            if result == "success":
                self.game.add_quest_result(True)
            else:
                self.game.add_quest_result(False)

            proposed_party = None
            # Party comp has been wiped by this point. Re-create it from the gamestate by getting the last proposed party
            for party in self.game.quest_proposals[self.state.quest-1][::-1]:
                if len(party["comp"]) > 0:
                    proposed_party = party["comp"]
                    break

            self.quest_history.append((proposed_party, result))

            self.quest_updated = True   # this flag is used for updating the belief graph model
        
        if "proposed_party" in self.state_diff:
            # This can be either a party being proposed, or party becoming empty after round
            if len(self.state_diff['proposed_party']) > 0: # There is actually a party being proposed
                self.debug(f"########### Proposed party updated: state diff:{self.state_diff['proposed_party']} --- state: {self.state.proposed_party}\n")
                self.party_leader = self.state_diff["messages"][-1]["msg"].split()[0]
                # self.game.party_leader = self.party_leader

                plist = [
                    self._private_data.order_to_name[str(order_id)].lower()
                    for order_id in self.state.proposed_party 

                ]
                proposed_team = plist
                self.game.current_proposed_party = proposed_team 
                print(f"Proposed team: {proposed_team}")
            else: # the round has ended:
                self.game.current_proposed_party = []
                self.party_leader = None
        
        if "messages" in self.state_diff:
            self.debug(f"########### Messages updated: {self.state_diff['messages']}\n")
            # Add the message to the game log
            for msg in self.state_diff["messages"]:
                if msg is None:
                    continue
                actual_msg = msg["msg"]
                if actual_msg != "":
                    pname = (
                        msg["player"] if msg["player"] != "system" else "Voiceover"
                    )
                    self.game_log.append([pname, actual_msg])
                    self.log(f"{pname}: {actual_msg}\n")

        return {}

    def addPrivateData(self, data):
        super().addPrivateData(data)
        # Setup role hints
        role_lookup = {v: k for k, v in self._private_data.all_players.items()}
        self.debug(f"Private role of the players are: {role_lookup}\n")
        self.log(f"Roles: {role_lookup}\n\n")
        self.initialize_csv()
        # save player names and their relation with indexes
        player_names = {
                v.lower(): int(k) for k, v in self._private_data.order_to_name.items()
            }
        self.game.index_to_players = {v: k for k, v in player_names.items()}
        self.game.players_to_index = player_names

        self.debug(f"player to index: {self.game.players_to_index}\n")
        self.debug(f"index to player: {self.game.index_to_players}\n")

        return {}
    

    def update_predictions(self, with_llm_prior=False):
        """Let's get the beliefs from the latest game state vector"""
        self.debug(f"-- The quest history for vector generation: {self.game.quest_proposals}\n")
        self.debug(f"-- The outcome history for vector generation: {self.game.quest_results}\n")
        state_vector = self.game.get_state_vector()
        self.debug(f"-- Updating beliefs with state vector: {state_vector} \n")
        index = self.game.players_to_index[self._name.lower()] - 1
        probabilities = self.graph_model.predict_probs(game_state=state_vector, self_role=self._team, self_index=index, algorithm="max")
        self.latest_probabilities = {self.game.index_to_players[i+1]: probabilities[i+1] for i in range(6)}
        self.quest_updated = False
        self.debug(f"       -- BELIEF UPDATED: {self.latest_probabilities}\n")
        if with_llm_prior:
            self.log (f" ***  BELIEFS with Vibes: {self.latest_probabilities}\n")
        else:
            self.log (f" ***  BELIEFS: {self.latest_probabilities}\n")
        # self.data_csv() # this will add the turn number and probabilities to the csv file
        return {}
    
    # we dont need this function right now
    def get_evil_probabilities(self):
        """based on the predicted probabilittes, gets the names of the evil players"""
        evil_probs = {}
        for k,v in self.latest_probabilities.items():
            if v['evil'] > v['good']:
                evil_probs[str(k).lower()] = v['evil']
        return evil_probs

    def getAction(self, task: Task, suggestion: str):
        self.debug(f"Received action request for agent. Options: {task.task}, suggestions: {suggestion}\n")
        taken_action = suggestion
        if (taken_action == "propose_party"):
            self.debug(f"------> selected action: propose party\n")
            self.update_predictions_based_on_chat(None) # TODO this will change from None if we want to filter and use chat
            if  self.game.current_proposed_party and len( self.game.current_proposed_party) == 2:
                party = self.game.current_proposed_party
            else: 
                self.debug(f"+=+= Agent is selecting a party composition")
                party = self.policy_selector.propose_party(task.target_party_size, self.latest_probabilities)

            # Make sure the proposed party has the right length:
            party = party[:task.target_party_size]
            while len(party) < task.target_party_size:
                for i in range(1, 7):
                    if i not in party:
                        party.append(i)
                        break
            self.log(f"current proposed party: {self.game.current_proposed_party}  and party is {party}\n")
            message = self.make_prompt_propose_party(party)
            self._messages.append(message)
            self.self_proposed_party = party
            party = sorted([self.game.players_to_index[i] for i in party])
            self._last_action.append("propose_party")
            # self.self_proposed_party = party
            self.debug(f"===== Proposed party: {party}\n")
            return {
                "success": True,
                "action": "propose_party",
                "data": {"party": party},
            }
        elif "message" in task.task and len(self._messages) > 0:
            self.debug(f"------> selected action: message from condition 1\n")
            self._last_action.append("message")
            message = self._messages.pop(-1)
            self.debug(f"+++++++ Agent is Sending message: {message}\n")
            return {"success": True, "action": "message", "data": {"msg": message}}
        elif (taken_action == "message"):
            self.debug(f"------> selected action: message from condition 2\n")
            self.update_predictions_based_on_chat(None)
            self._last_action.append("message")
            print(" --> Sending message")
            message = self.make_prompt_message()
            return {"success": True, "action": "message", "data": {"msg": message}}
        elif (taken_action == "start_party_vote"):
            self.vote_next = False
            self.debug(f"------> selected action: start_party_vote\n")
            self._last_action.append("start_party_vote")
            print(" --> Starting party vote")
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif taken_action == "vote_party":
            self.debug(f"------> selected action: vote_party\n")

            print(" --> Voting for party")
            if not("vote_party" in self._last_action):
                self.update_predictions_based_on_chat(None) # TODO this will change from None if we want to filter chat
            else:
                self.debug(f" ### Already calculated beliefs and voted for party in this turn, using previous beliefs\n")
            self._last_action.append("vote_party")
            vote = self.policy_selector.vote_for_party(self.game.current_proposed_party, self.latest_probabilities)
            self.debug(f"**** current party rejects: {self.state.failed_party_votes} === {self.game.current_party_rejects} ****\n")

            if self.state.failed_party_votes >= 4: 
                self.debug(f"===== Changing {vote} into True due to last attempt\n")
                vote = True
            self.debug(f"===== Voting for party: {self.game.current_proposed_party} with vote: {vote}\n")

            vote_str = "This is where any thought process would be, if there was any. But there is none."
            self.data_csv()
            print(f"VOTE {self._id}: {vote} {vote_str}")
            return {"success": True, "action": "vote_party", "data": {"vote": vote}}
        elif taken_action == "vote_quest":
            self.debug(f"------> selected action: vote_quest\n")
            self._last_action.append("vote_quest")
            print(" --> Voting for quest")
            vote = self.policy_selector.vote_for_quest()
            self.debug(f"=+=+= Voting for quest: {vote}\n")
            return {"success": True, "action": "vote_quest", "data": {"vote": vote}}
        elif taken_action == "vote_assassin":
            self.debug(f"------> selected action: vote_assassin\n")
            self._last_action.append("vote_assassin")
            print(" --> Voting for assassin")
            self.update_predictions_based_on_chat(None) # TODO this will change from None if we want to filter chat
            vote = self.policy_selector.chose_assassin_target(self.latest_probabilities)
            print(f"assassin vote: {vote}")
            return {"success": True, "action": "vote_assassin", "data": vote}
        else:
            print(" --> Ending turn")
            # This needs a tiny delay such that the server can process prior messages
            time.sleep(2)
            return {"success": True, "action": "end_turn"}




    # TODO this function is deprecated to create a simpler situation
    def getAction_deprecated(self, task: Task, suggestion: str):
        print(
            f"Received action request for agent {self._id} ({self._name}). Options: {task.task}"
        )
        self.debug(f"** Action request with options: {task.task} , last actions were: {self._last_action}\n")

        # Here the agent would need to decide which action to take, but let's build a simple heuristic
        # The original recon agent does not have multiple discussion rounds and the assassion onle tries when it needs to guess merlin
        if len(task.task) == 0:
            print("Error: No valid actions... this should not happen!")
            return {"success": True, "action": "end_turn"}
        
        if self.quest_updated:
            self.debug("UPDATING BELIEFS in getAction due to quest_updated\n")


        self.debug(f"State for Action Selection: self.game.current_proposed_party: {self.game.current_proposed_party}, self.vote_next: {self.vote_next}\n")

        if (
            "propose_party" in task.task
            and "propose_party" not in self._last_action
            and not self.vote_next
        ):
            self.debug(f"------> selected action: propose party\n")
            print(" --> Proposing party")
            # Let's propose a party
            self.update_predictions_based_on_chat(None) # TODO this will change from None if we want to filter and use chat
            if  self.game.current_proposed_party :
                if len( self.game.current_proposed_party) == 2:
                    party = self.game.current_proposed_party
                else: 
                    party = self.policy_selector.propose_party(task.target_party_size, self.latest_probabilities)
            else: 
                party = self.policy_selector.propose_party(task.target_party_size, self.latest_probabilities)

            # Make sure the proposed party has the right length:
            party = party[:task.target_party_size]
            while len(party) < task.target_party_size:
                for i in range(1, 7):
                    if i not in party:
                        party.append(i)
                        break

            print(f"===== Proposed party before making LLM message: {party}\n")
            if not(self.game.current_proposed_party is None or self.game.current_proposed_party == []) :
                self.log(f"current proposed party: {self.game.current_proposed_party}  and party is {party}\n")

                if sorted([i.lower() for i in self.self_proposed_party]) == sorted([i.lower() for i in party]):
                    # the same party is being proposed
                    self.vote_next = True
                    if len(self._last_action) == 0:
                        message = self.make_prompt_opinion_not_changed_vote(party)
                        if 'message' in task.task:
                            self._last_action.append("message")
                            return {"success": True, "action": "message", "data": {"msg": message}}
                        raise ValueError("This should not happen")
                    if self._last_action[-1] != "message":
                        message = self.make_prompt_opinion_not_changed_vote(party)
                    
                        if 'message' in task.task:
                            self._last_action.append("message")
                            return {"success": True, "action": "message", "data": {"msg": message}}
                        raise ValueError("This should not happen")

            message = self.make_prompt_propose_party(party)
            print(message)
            self._messages.append(message)

            self.self_proposed_party = party
            party = sorted([self.game.players_to_index[i] for i in party])
            self._last_action.append("propose_party")

            self.debug(f"===== Proposed party: {party}\n")
            return {
                "success": True,
                "action": "propose_party",
                "data": {"party": party},
            }
        elif "message" in task.task and len(self._messages) > 0:
            # This is if a certain other action also generated a message, so we send that here
            self.debug(f"------> selected action: message from condition 1\n")
            self._last_action.append("message")
            message = self._messages.pop(-1)
            self.debug(f"+++++++ Agent is Sending message: {message}\n")
            return {"success": True, "action": "message", "data": {"msg": message}}
        elif "message" in task.task and "message" not in self._last_action:
            # If we have nothing to send right now, we will discuss if we haven't said anything yet...
            self.debug(f"------> selected action: message from condition 2\n")
            self.update_predictions_based_on_chat(None)
            self._last_action.append("message")
            print(" --> Sending message")

            message = self.make_prompt_message()
            return {"success": True, "action": "message", "data": {"msg": message}}

        elif (
            "start_party_vote" in task.task
            and "start_party_vote" not in self._last_action
            and "propose_party" not in self._last_action
            and self._turn > 2
        ):
            self.vote_next = False
            self.debug(f"------> selected action: start_party_vote\n")
            self._last_action.append("start_party_vote")
            print(" --> Starting party vote")
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif "vote_party" in task.task:
            self.debug(f"------> selected action: vote_party\n")
            # self._last_action.append("vote_party")
            print(" --> Voting for party")
            if not("vote_party" in self._last_action):
                self.update_predictions_based_on_chat(None) # TODO this will change from None if we want to filter chat
            else:
                self.debug(f" ### Already calculated beliefs and voted for party in this turn, using previous beliefs\n")
            self._last_action.append("vote_party")
            vote = self.policy_selector.vote_for_party(self.game.current_proposed_party, self.latest_probabilities)
            self.debug(f"**** current party rejects: {self.state.failed_party_votes} === {self.game.current_party_rejects} ****\n")
            if self.state.failed_party_votes >= 4:
                self.debug(f"===== Changing {vote} into True due to last attempt\n")
                vote = True
            self.debug(f"===== Voting for party: {self.game.current_proposed_party} with vote: {vote}\n")
            vote_str = "This is where any thought process would be, if there was any. But there is none."
            print(f"VOTE {self._id}: {vote} {vote_str}")
            return {"success": True, "action": "vote_party", "data": {"vote": vote}}
        elif "vote_quest" in task.task:
            self.debug(f"------> selected action: vote_quest\n")
            self._last_action.append("vote_quest")
            print(" --> Voting for quest")
            vote = self.policy_selector.vote_for_quest()
            self.debug(f"=+=+= Voting for quest: {vote}\n")
            return {"success": True, "action": "vote_quest", "data": {"vote": vote}}
        elif (
            "vote_assassin" in task.task and len(task.task) == 1
        ): 
            self.debug(f"------> selected action: vote_assassin\n")
            self._last_action.append("vote_assassin")
            print(" --> Voting for assassin")
            self.update_predictions_based_on_chat(None)
            vote = self.policy_selector.chose_assassin_target(self.latest_probabilities)
            print(f"assassin vote: {vote}")
            return {"success": True, "action": "vote_assassin", "data": vote}
        else:
            self.debug(f"------> selected action: ending turn\n")
            print(" --> Ending turn")
            # This needs a tiny delay such that the server can process prior messages
            time.sleep(2)
            return {"success": True, "action": "end_turn"}


    def update_predictions_based_on_chat(self, chat):
        probs = self.get_llm_vibes_agreement(chat)
        probs = {self.game.players_to_index[k]: v for k,v in probs.items()}
        self.log("             UPDATING PRIORS           \n")
        self.update_predictions()
        self.graph_model.update_priors(probs)
        self.update_predictions(with_llm_prior=True)
        probs = {1: {"evil":0.5, "good":0.5},
                        2: {"evil":0.5, "good":0.5},
                        3: {"evil":0.5, "good":0.5},
                        4: {"evil":0.5, "good":0.5},
                        5: {"evil":0.5, "good":0.5},
                        6: {"evil":0.5, "good":0.5},
                        }
        self.graph_model.update_priors(probs) #TODO I am not doing this for ablation purpose
        

    

    def get_llm_vibes_agreement(self, chat):
        probs = {self.game.index_to_players[1]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[2]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[3]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[4]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[5]: {"evil":0.5, "good":0.5},
                        self.game.index_to_players[6]: {"evil":0.5, "good":0.5},
                        }
        if self.game.quest_results == []:
            return probs
        
        logs = '\n'.join([" : ".join(i) for i in self.game_log])
        probabilities = self.make_prompt_probabilities()
        history = self.make_prompt_quest_history()
        prompt = self._prompt_hint.get_vibes_player_agreement.format(name=self._name, latest_probabilities=probabilities, logs=logs, quest_history=history, quest_num=self.state.quest)

        response = self.prompt_llm(prompt)
        response = response.replace("'", '"')
        new_probs = json.loads(response)

        self.log(f" ###  LLM vibes: {new_probs}\n")

        for player in new_probs.keys():
            player_name = player.lower()
            if player_name in probs:
                if new_probs[player] == "increase":
                    if self.state.quest >= 3:
                        probs[player_name] = {"evil":0.75, "good":0.25}
                    else:
                        probs[player_name] = {"evil":0.6, "good":0.4}
                elif new_probs[player] == "decrease":
                    if self.state.quest >= 3:
                        probs[player_name] = {"evil":0.25, "good":0.75}
                    else:
                        probs[player_name] = {"evil":0.4, "good":0.6}

        self.debug(f"===== LLM vibes got priors updated: {probs}\n")

        return probs

    def make_prompt_probabilities(self):
        if self.latest_probabilities is None:
            return {player_name.capitalize(): 0.5 for player_name in self.game.index_to_players.values()}

        return {key.capitalize(): round(value["evil"], 1) for key, value in self.latest_probabilities.items()}
    
    def make_prompt_team_comp(self, team_comp=None):
        if team_comp is None:
            return [name.capitalize() for name in self.game.current_proposed_party]
        
        return [name.capitalize() for name in team_comp]
    
    def make_prompt_quest_history(self):
        if len(self.quest_history) > 0:
            history = ""
            quest_num = 1
            for party, outcome in self.quest_history:
                history += "Quest {}. Party: {}. Outcome: {}.\n".format(quest_num, [name.capitalize() for name in party], outcome)
                quest_num += 1

            return history

        else:
            return "No prior Quests; this is the first Round."
    
    def make_prompt_message(self):
        logs = '\n'.join([" : ".join(i) for i in self.game_log]) # make the game logs that we will use in the prompt
        probabilities = self.make_prompt_probabilities()
        team_comp = self.make_prompt_team_comp()
        history = self.make_prompt_quest_history()
        prompt = self._prompt_hint.generate_message_from_log_good.format(name=self._name, logs=logs, latest_probabilities=probabilities, role=self.role_string, team_comp=team_comp, party_leader=self.party_leader, quest_history=history, quest_num=self.state.quest, party_size=len(team_comp))

        try:
            result = json.loads(self.prompt_llm(prompt))
        except json.JSONDecodeError as e:
            self.debug(f"Error decoding JSON: {e}")
            self.debug(f"Prompt: {prompt}")
            self.debug(f"Response: {self.prompt_llm(prompt)}")
            print(f"Error decoding JSON: {e} prompting again")
            return self.make_prompt_message()
        return result["message"]
    
    def make_prompt_propose_party(self, team_comp):
        logs = '\n'.join([" : ".join(i) for i in self.game_log]) # make the game logs that we will use in the prompt
        probabilities = self.make_prompt_probabilities()
        team_comp = self.make_prompt_team_comp(team_comp)
        history = self.make_prompt_quest_history()
        prompt = self._prompt_hint.generate_proposal_message_good.format(name=self._name, logs=logs, latest_probabilities=probabilities, role=self.role_string, team_comp=team_comp, quest_history=history, quest_num=self.state.quest, party_size=len(team_comp))

        try:
            result = json.loads(self.prompt_llm(prompt))
        except json.JSONDecodeError as e:
            self.debug(f"Error decoding JSON: {e}")
            self.debug(f"Prompt: {prompt}")
            self.debug(f"Response: {self.prompt_llm(prompt)}")
            print(f"Error decoding JSON: {e} prompting again")
            return self.make_prompt_propose_party(team_comp)
        return result["message"]
    
    def make_prompt_opinion_not_changed_vote(self, team_comp):
        logs = '\n'.join([" : ".join(i) for i in self.game_log]) # make the game logs that we will use in the prompt
        probabilities = self.make_prompt_probabilities()
        team_comp = self.make_prompt_team_comp(team_comp)
        history = self.make_prompt_quest_history()
        prompt = self._prompt_hint.confirm_proposal_message_good.format(name=self._name, logs=logs, latest_probabilities=probabilities, role=self.role_string, team_comp=team_comp, quest_history=history, quest_num=self.state.quest, party_size=len(team_comp))

        try:
            result = json.loads(self.prompt_llm(prompt))
        except json.JSONDecodeError as e:
            self.debug(f"Error decoding JSON: {e}")
            self.debug(f"Prompt: {prompt}")
            self.debug(f"Response: {self.prompt_llm(prompt)}")
            print(f"Error decoding JSON: {e} prompting again")
            return self.make_prompt_opinion_not_changed_vote(team_comp)
        return result["message"]


    def log(self, message):
        with open(self._log_file, "a") as log:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            log.write(f"[{timestamp}] {message}")
    
    def debug(self, message):
        with open(self._debug_log_file, "a") as log:
            log.write(message)

    def data_csv(self):
        """This function adds the turn number and probabilities calculated for all the players to a csv file"""
        # Read only the header row to determine the column order
        with open(self.csv_file, mode='r', newline='', encoding='utf-8') as f_read:
            reader = csv.reader(f_read)
            header = next(reader)  # First row as list of columns

        col_index_map = {col_name.lower(): i for i, col_name in enumerate(header)}
        new_row = [''] * len(header)
        data_dict = self.latest_probabilities.copy()
        new_row[col_index_map["round"]] = str(self.round)
        # Place values from data_dict into the correct column based on case-insensitive keys
        for key, value in data_dict.items():
            lower_key = key.lower()
            if lower_key in col_index_map:
                new_row[col_index_map[lower_key]] = str(value['evil'])

        with open(self.csv_file, mode='a', newline='', encoding='utf-8') as f_append:
            writer = csv.writer(f_append)
            writer.writerow(new_row)

    def initialize_csv(self):
        """This function initializes the csv file with the header"""
        roles = self._private_data.all_players
        names = sorted(roles)
        names_string = ",".join([f"{name}" for name in names])
        roles_string = ",".join([f"{roles[name]}" for name in names])
        with open(self.csv_file, "w") as csv:
            csv.write(f"round," + names_string + "\n")
            csv.write(f"round," + roles_string + "\n")


    def prompt_llm(self, prompt):
        result = self._llm_generate(message=prompt, model=LLM.GPT, temperature=1.0)
        # result = self._llm_generate(message=prompt, model=LLM.DEEPSEEK, temperature=1.0)


        self.log_llm(prompt, result)
        return result.choices[0].message.content
    
    def log_llm(self, prompt, result):
        with open(self._llm_log_file, "a") as log:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            log.write(f"[{timestamp}] ---- prompt : {prompt}\n")
            log.write(f"[{timestamp}] ---- response : {result.choices[0].message.content}\n")
            stats =  {"prompt_tokens": result.usage.prompt_tokens, "completion_tokens": result.usage.completion_tokens}
            log.write(f"[{timestamp}] ---- stats : {stats}\n")
            log.write("\n")
            log.write("*****************************************************")
            log.write("\n")
        