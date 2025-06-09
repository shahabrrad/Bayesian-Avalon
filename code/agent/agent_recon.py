import json

from agent_base import BaseAgent, LLM, ATEAM, AROLE
from messages import Message, AvalonGameStateUpdate, Task
import random
import enum

# Import the paths in a way such that the recon submodule works...
import sys
import os

submodule_path = os.path.join(os.path.dirname(__file__), "recon")
sys.path.insert(0, submodule_path)
import importlib
import copy
import time
from easydict import EasyDict
from recon.Avalon.Player import Player
from recon.Avalon.prompt.identity_prompt import IdentityHint, IdentityHintWithoutHide
from recon.Avalon.utils import mark_memory_position


class ReConGame:
    def __init__(self):
        self.role_hints = {}
        self.role_hints_without_hide = {}
        self.propose_count = [2, 3, 4, 3, 4]
        self.round = 0
        self._memory_dict_list = []
        self._full_history = []
        self.proposed_team = None
        self.round_result = []
        self.failed_party_votes = 0
        self.round_vote_result = []
        self.previous_player_team_list = []
        self.previous_leader_list = []
        self.discussion_round_begin_sign = "A new discussion round begins."
        self.leader = ""
        self.player_names = None

    @property
    def full_history(self):
        return copy.deepcopy(self._full_history)

    @property
    def memory_dict_list(self):
        return copy.deepcopy(self._memory_dict_list)

    def memory_dict_list_append(self, item):
        return self._memory_dict_list.append(item)

    def log(self, subject, message):
        # Append the new log entry
        self._full_history.append([subject, message])

        # Capture the current memory status
        memory_status = mark_memory_position(
            round_info=self.round,
            team_info=self.proposed_team,
            mission_results_info=self.round_result,  # "Success" or "Fail"
            mission_vote_results=self.round_vote_result,  # This is for the quest vote.... This is technically hidden information?! Not needed anyways?
            previous_mission_player=self.previous_player_team_list,  # List of player names
            previous_mission_leader=self.previous_leader_list,  # List of leader names
        )

        # Update the memory dictionary list with the new status
        self.memory_dict_list_append(memory_status)

    def get_full_history_list(self) -> list:
        ret = [(_[0], _[1]) for _ in self._full_history]
        return ret

    def get_team_size(self):
        return self.propose_count[self.round - 1]

    def get_pid_from_names(self, names):
        print("Looking up names", names, "in", self.player_names)

        def _lookup_player(name):
            lower_name = name.lower()
            if lower_name in self.player_names:
                # convert to number
                return int(self.player_names[lower_name])
            return None

        if type(names) == str:
            return [_lookup_player(names)]
        return [_lookup_player(name) for name in names]


class ReCon:
    # This class is largely replacing the ReCon Game class and is basically a translation layer between their Player, and our Game
    def __init__(self, agent_id, role, use_mod):
        print(f"Setting up ReCon Agent with ID {agent_id} and role {role}")
        # Roles as defined by ReCon
        role_list = [
            "Merlin",
            "Percival",
            "Loyal servant of arthur",
            "Loyal servant of arthur",
            "Loyal servant of arthur",
            "Loyal servant of arthur",
            "Morgana",
            "Assassin",
            "Minion of Mordred",
            "Minion of Mordred",
        ]
        # Convert the role to the ReCon role (if necessary)
        if "Servant" in role:
            role = "Loyal servant of arthur"

        if "Evil" in role:
            role = "Minion of Mordred"

        # Basic COT agent is also possible with baseline_gpt config
        self.recon_config = self._load_config_file("ours_gpt")
        self.role = role
        self.player = Player(agent_id, role, role_list, self.recon_config, use_mod)

    def _load_config_file(self, _cfg_name: str):
        _config_module = importlib.import_module(f"Avalon.configs.{_cfg_name}")
        _config = _config_module.config
        # _config.update(vars(args))
        _config = EasyDict(_config)
        return _config


# This is the test agent, which is a very simple agent that just randomly chooses actions and writes pointless messages
# However, this agent is capable to "play", or rather "progress" the game.
class ReConAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        game_id: str,
        agent_name: str,
        agent_role_preference: str,
        config: dict,
        use_mod: bool = False,
    ):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)
        self._use_mod = use_mod
        self._last_action = None
        self._agent_id = agent_id
        self._game_id = game_id
        self._name = agent_name
        self._role_preference = (
            agent_role_preference  # Keep this around just in case...
        )
        self._recon_game = ReConGame()

        ## Save the role and decide good or evil
        self._role = self._roleToEnum(agent_role_preference)
        self._team = (
            ATEAM.EVIL
            if self._role in [AROLE.MORGANA, AROLE.ASSASSIN, AROLE.EVIL]
            else ATEAM.GOOD
        )

        # Message queue
        self._messages = []
        self._last_action = []

        # Track some variables
        self._turn = 0

        self.recon = ReCon(self._name, self._enumToRole(self._role), self._use_mod)

    def addMessage(self, message: Message):
        # print("Received message", message.msg)
        return {}

    def addState(self, state: AvalonGameStateUpdate):
        # print("player names before:", self._recon_game.player_names)
        if "quest" in self.state_diff:
            self._recon_game.round = self.state.quest
            if self.state.quest == 1:
                self._recon_game.log(
                    "Game Start",
                    "Welcome to Avalon Game. This message signifies the start of a new game. "
                    "All previous information, such as completed tasks or team alignments, is reset. "
                    "The game history from this line onwards is the effective historical game history dialogue of this game!",
                )
            if self.recon.recon_config["short_memory"]:
                self._recon_game.log(
                    f"Voiceover", self._recon_game.discussion_round_begin_sign
                )
            # Let's also set the party back to None
            self._recon_game.proposed_team = None

        if "turn" in self.state_diff:
            # Reset the last actions if the turn ID changes
            self._last_action = []
            self._turn = self.state.turn

        if "failed_party_votes" in self.state_diff:
            print("failed_party_votes", self.state.failed_party_votes)
            self._recon_game.failed_party_votes = self.state.failed_party_votes

        if "messages" in self.state_diff:
            # Add the message to the game log
            for msg in self.state_diff["messages"]:
                if msg is None:
                    continue
                actual_msg = msg["msg"]
                if actual_msg != "":
                    pname = msg["player"] if msg["player"] != "system" else "Voiceover"
                    self._recon_game.log(pname, actual_msg)

        # ISSUE - TODO: This does not have the intended effect
        # If the player only changes one player in the team, proposed_team gets equal to only the changed player
        if "proposed_party" in self.state_diff:
            plist = [
                self._private_data.order_to_name[str(order_id)]
                for order_id in self.state.proposed_party
            ]
            if len(plist) > 0:
                self._recon_game.proposed_team = plist
                self._recon_game.previous_player_team_list.append(plist)

        if "leader_pid" in self.state_diff:
            lname = self._private_data.order_to_name[
                str(int(self.state.leader_pid))  # removed + 1 here
            ]
            self._recon_game.leader = lname
            self._recon_game.previous_leader_list.append(lname)

        # Track round results
        if "quest_results" in self.state_diff:
            print("Quest results", self.state.quest_results)
            self._recon_game.round_result = self.state.quest_results
        
        # print("player names after:", self._recon_game.player_names)
        print("------------round vote results" , self._recon_game.round_vote_result)

        return {}

    def addPrivateData(self, data):
        super().addPrivateData(data)
        # print(self._private_data)

        # Setup role hints
        self.role_hint = ""
        self.role_hint_without_hide = ""
        role_lookup = {v: k for k, v in self._private_data.all_players.items()}
        hint_args = {
            "assassin": role_lookup.get("Assassin", "None"),
            "morgana": role_lookup.get("Morgana", "None"),
            "merlin": role_lookup.get("Merlin", "None"),
            "percival": role_lookup.get("Percival", "None"),
            "loyal_1": role_lookup.get("Servant-1", "None"),
            "loyal_2": role_lookup.get("Servant-2", "None"),
            "loyal_3": role_lookup.get("Servant-3", "None"),
            "loyal_4": role_lookup.get("Servant-4", "None"),
            "evil_1": role_lookup.get("Minion-1", "None"),
            "evil_2": role_lookup.get("Minion-2", "None"),
        }

        # Switch over agent role
        if self._role == AROLE.MERLIN:
            self.role_hint = IdentityHint.get_hint_for_merlin(**hint_args)
            self.role_hint_without_hide = IdentityHintWithoutHide.get_hint_for_merlin(
                **hint_args
            )
        elif self._role == AROLE.PERCIVAL:
            self.role_hint = IdentityHint.get_hint_for_percival(**hint_args)
            self.role_hint_without_hide = IdentityHintWithoutHide.get_hint_for_percival(
                **hint_args
            )
        elif self._role == AROLE.ASSASSIN:
            self.role_hint = IdentityHint.get_hint_for_assassin(**hint_args)
            self.role_hint_without_hide = IdentityHintWithoutHide.get_hint_for_assassin(
                **hint_args
            )
        elif self._role == AROLE.MORGANA:
            self.role_hint = IdentityHint.get_hint_for_morgana(**hint_args)
            self.role_hint_without_hide = IdentityHintWithoutHide.get_hint_for_morgana(
                **hint_args
            )
        elif self._role == AROLE.SERVANT:
            self.role_hint = IdentityHint.get_hint_for_loyal(**hint_args)
            self.role_hint_without_hide = IdentityHintWithoutHide.get_hint_for_loyal(
                **hint_args
            )
        elif self._role == AROLE.EVIL:
            self.role_hint = IdentityHint.get_hint_for_evil(**hint_args)
            self.role_hint_without_hide = IdentityHintWithoutHide.get_hint_for_evil(
                **hint_args
            )

        self._recon_game.role_hints[self.recon.role] = self.role_hint
        self._recon_game.role_hints_without_hide[self.recon.role] = (
            self.role_hint_without_hide
        )

        if self._recon_game.player_names is None:
            self._recon_game.player_names = {
                v.lower(): k for k, v in self._private_data.order_to_name.items()
            }

        self.recon.player.set_game_belong_to(self._recon_game)
        return {}

    def getAction(self, task: Task, suggestion: str):
        taken_action = suggestion
        print("#" * 100)
        if self._use_mod:
            print("ReConMod Agent:", self._name, f"({self._private_data.role})", "-> Choosing action:", taken_action) 
        else:
            print("ReCon Agent:", self._name, f"({self._private_data.role})", "-> Choosing action:", taken_action) 
        print("#" * 100)

        if (taken_action == "propose_party"):
            self._last_action.append(taken_action)
            print(" --> Proposing party")
            ## DEBUG: Just send an empty message instead of waitinng for the LLM
            # plist = [1,2,3,4,5,6]
            # return {"success": True, "action": "propose_party", "data": {"party": plist[:task.target_party_size]}}
            ## END DEBUG
            # To save configuration stuff, just set the propose count to the target party size from the request
            self._recon_game.propose_count = [task.target_party_size] * 5
            # Let's propose a party
            party, message, all_llm_data  = self.recon.player.propose_team()
            self._messages.append(message)
            # Make sure the proposed party has the right length:
            party = party[: task.target_party_size]

            # remove any duplicated players from the proposed party
            party = list(set(party))

            while len(party) < task.target_party_size:
                for i in range(1, 7):
                    if i not in party:
                        party.append(i)
                        break
            return {
                "success": True,
                "action": "propose_party",
                "data": {"party": party, "llm_data": all_llm_data},
            }
        elif "message" in task.task and len(self._messages) > 0:
            # This is if a certain other action also generated a message, so we send that here
            self._last_action.append("message")
            message = self._messages.pop(-1)
            return {"success": True, "action": "message", "data": {"msg": message}}
        elif taken_action == "message":
            # If we have nothing to send right now, we will discuss if we haven't said anything yet...
            self._last_action.append("message")
            print(" --> Sending message")
            ## DEBUG: Just send an empty message instead of waitinng for the LLM
            # return {"success": True, "action": "message", "data": {"msg": "Dbg Message"}}
            ## END DEBUG
            message, all_llm_data = self.recon.player.discuss_proposed_team()
            return {"success": True, "action": "message", "data": {"msg": message, "llm_data": all_llm_data}}
        elif taken_action == "start_party_vote":
            self._last_action.append("start_party_vote")
            print(" --> Starting party vote")
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif taken_action == "vote_party":
            all_llm_data = []
            self._last_action.append("vote_party")
            print(" --> Voting for party")
            if (self._recon_game.round == 1 and self._team == ATEAM.GOOD) or (
                self._recon_game.failed_party_votes == 4 and self._team == ATEAM.GOOD
            ):
                # first quest always vote yes.
                # if we are about to fail vote yes
                vote = True
                vote_str = "support"
            else:
                vote, vote_str, all_llm_data = self.recon.player.vote_on_team()
            print(f"VOTE {self.recon.player.id}: {vote} {vote_str}")
            self._recon_game.log(
                f"Player {self.recon.player.id}",
                f"Player {self.recon.player.id} votes: {'support' if vote else 'disagree'} with this team proposal.",
            )
            return {"success": True, "action": "vote_party", "data": {"vote": vote, "llm_data": all_llm_data}}
        elif taken_action == "vote_quest":
            self._last_action.append("vote_quest")
            print(" --> Voting for quest")
            vote, all_llm_data  = self.recon.player.vote_on_mission()
            vote = True if vote == "Success" else False  # game is expecting boolean
            return {"success": True, "action": "vote_quest", "data": {"vote": vote, "llm_data": all_llm_data}}
        elif taken_action == "vote_assassin":
            self._last_action.append("vote_assassin")
            print(" --> Voting for assassin")
            vote = self.recon.player.guess_merlin()
            print(f"assassin vote: {vote}")
            return {"success": True, "action": "vote_assassin", "data": vote}
        else:
            print(" --> Ending turn")
            # This needs a tiny delay such that the server can process prior messages
            time.sleep(2)
            return {"success": True, "action": "end_turn"}
