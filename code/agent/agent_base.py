from messages import (
    Message,
    AvalonGameStateUpdate,
    Typing,
    Reset,
    Task,
    AvalonGameState,
)
from openai import OpenAI
import hashlib
import json
from TypeChat.typechat.typechat import TypeChatResult
from utils import bcolors
from enum import Enum
import os


class LLM(Enum):
    LOCAL = 1
    GPT = 2
    DEEPSEEK = 3


class ATEAM(Enum):
    GOOD = 1
    EVIL = 2


class AROLE(Enum):
    MERLIN = 1
    PERCIVAL = 2
    SERVANT = 3
    MORGANA = 4
    ASSASSIN = 5
    EVIL = 6


class BaseAgent(object):
    def __init__(
        self,
        agent_id: str,
        game_id: str,
        agent_name: str,
        agent_role_preference: str,
        config: dict = None,
    ):
        self._id = agent_id
        self._gid = game_id
        self._name = agent_name
        self._config = config
        # OpenAI Setup, redirected to our local servers...
        self._llm_local = OpenAI(api_key="EMPTY", base_url="http://ollama:11434/v1")
        self._model_local = self._config["agent"]["local_model"]
        # self._model_local = "gemma2:9b"

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if "deepseek" in self._config["agent"]["model"]:
            api_key=os.environ.get("DEEPSEEK_API_KEY", "")

        self._llm_gpt = OpenAI(
            api_key=api_key,
            base_url=self._config["agent"]["openai_base_url"],
        )
        self._model_gpt = self._config["agent"]["model"]  # gpt-4-1106-preview, gpt-3.5-turbo-1106

        self._llm_deepseek = OpenAI(
            api_key=api_key,
            # base_url="http://localhost:11434/api/generate",
            base_url = 'https://api.deepseek.com',
        )
        self._model_deepseek = self._config["agent"]["model"]

        # Cache setup
        self._cache = {}
        with open("cache.json", "r") as fh:
            self._cache = json.load(fh)

        # State tracker
        self.state = AvalonGameState()
        self.state_diff = {}
        self._private_data = None
        self.as_heuristic = {
            "turn": None,
            "history": [],
            "this_leaders_turn": 0,
            "leader": -1
        }

    def getID(self):
        return self._id

    def getGameID(self):
        return self._gid

    # This function is called when any player or agent (including this agent) sends a message
    def addMessage(self, message: Message):
        raise NotImplementedError("addMessage must be implemented by all agents")

    def addState(self, state: AvalonGameStateUpdate):
        raise NotImplementedError("addState must be implemented by all agents")

    # This function is called whenever the game sends a state update
    def addStateInternal(self, state: AvalonGameStateUpdate):
        """
        Update the current game state with values from the update.
        Lists are extended or updated while preserving existing values where updates are None.
        """
        update = state.changes
        if update is not None:
            # Iterate over each field in the update
            for field, value in update.dict(exclude_unset=True).items():
                current_value = getattr(self.state, field)

                # Handle lists: extend or update while preserving non-None values
                if isinstance(current_value, list) and isinstance(value, list):
                    # Combine lists by updating non-None values and extending as needed
                    updated_list = current_value[:]  # Copy current list
                    for i, new_val in enumerate(value):
                        if i < len(updated_list):
                            if new_val is not None:
                                updated_list[i] = new_val
                        else:
                            updated_list.append(new_val)
                    setattr(self.state, field, updated_list)
                else:
                    # For non-list fields, update only if the value is not None
                    if value is not None:
                        setattr(self.state, field, value)
            # Calculate the diff
            self.state_diff = {k: v for k, v in update.dict().items() if v is not None}
        
        # Set the full state
        self.state = state.full

        # Update our own action selection heuristic
        if self.state.turn != self.as_heuristic["turn"]:
            self.as_heuristic["turn"] = self.state.turn
            self.as_heuristic["history"] = []
            self.as_heuristic["this_leaders_turn"] += 1

        if self.state.leader_pid != self.as_heuristic["leader"]:
            self.as_heuristic["this_leaders_turn"] = 0
            self.as_heuristic["leader"] = self.state.leader_pid

        # Call the agent's addState function
        state.changes = None
        self.addState(state)

        return {}

    def agentActionInternal(self, task: Task, state: AvalonGameStateUpdate):
        self.addStateInternal(state)

        suggestion = None
        # Action Selection Heuristic for all agents 
        # If there are no possible actions, return a failure
        if len(task.task) == 0:
            return {"success": False, "message": "No possible actions"}
        # If there is only one possible action, return it
        elif len(task.task) == 1:
            suggestion = task.task[0]
        # If the action is to vote for a quest, then vote
        elif "vote_quest" in task.task:
            suggestion = "vote_quest"
        # If the action is to vote for a party, then vote
        elif "vote_party" in task.task:
            suggestion = "vote_party"
        # If the action is to vote for an assassin, then vote
        elif "vote_assassin" in task.task:
            suggestion = "vote_assassin"
        # If the action is to propose a party, then propose, but only if there is no party currently proposed
        elif ("propose_party" in task.task and # If we can propose a party
                (
                    len(self.state.proposed_party) == 0 or  # If there is no party currently proposed ...
                    "propose_party" not in self.as_heuristic["history"] # ..., or we haven't proposed a party in this turn yet
                )
             ):
            suggestion = "propose_party"
        # If the action is to send a message, then send a message, but only if we haven't sent a message yet
        elif "message" in task.task and "message" not in self.as_heuristic["history"]:
            suggestion = "message"
        # If the action is to start a party vote and it's not the first turn, then start a vote
        elif "start_party_vote" in task.task and self.as_heuristic["this_leaders_turn"] > 4:
            suggestion = "start_party_vote"
        # If there is no other action to take, then end the turn
        else:
            suggestion = "end_turn"

        res = self.getAction(task, suggestion)
        self.as_heuristic["history"].append(res["action"])

        # Make sure proposed parties are good...
        if res["action"] == "propose_party":
            # Compare the proposed party to the current one (Note: Order might be different, but if the unique members are the same, then it's a duplicate
            proposal = res["data"]["party"]
            if len(self.state.proposed_party) > 0 and (len(set(proposal) & set(self.state.proposed_party)) == len(proposal)):
                # Just move on to the next action (recursively call this function)
                print("Directive overwriting agent party proposal: Duplicate party proposal, skipping party of ", proposal)
                res = self.agentActionInternal(task, state)
            # Check for duplicates in the proposal
            elif len(set(proposal)) < task.target_party_size:
                # Add additional players to the proposal until we have the correct number without duplicates (Note: we want player IDs here, not names)
                print("Directive overwriting agent party proposal: Incorrect party size, adding players")
                for i in range(1, len(self.state.players)+1, 1):
                    if i not in proposal:
                        proposal.append(i)
                    if len(set(proposal)) == task.target_party_size:
                        break
                res["data"]["party"] = proposal
            elif len(set(proposal)) > task.target_party_size:
                # Remove players from the proposal until we have the correct number without duplicates
                print("Directive overwriting agent party proposal: Incorrect party size, removing players")
                proposal = proposal[:task.target_party_size]
                res["data"]["party"] = proposal
            else:
                pass # This should be a good party proposal

        return res

    # This function is called whenever the agent needs to take an action
    # Note, this function must return an action
    def getAction(self, task: Task, suggestion: str):
        raise NotImplementedError("getAction must be implemented by all agents")

    # This function is called whenever the game sends a typing update
    def addTyping(self, typing: Typing):
        # This function is optional, but can be overwritten
        return {}

    # This function is called whenever the game sends a reset update
    def addReset(self, reset: Reset):
        # This function is optional, but can be overwritten
        return {}

    # Adding the private data
    def addPrivateData(self, data):
        # This function is optional, but can be overwritten
        self._private_data = data
        return {}

    # The purpose of this function is to cache the inference results for a given prompt
    # This basically saves money when using OpenAI models... :D
    def _cacheOrInference(self, tns, prompt, llm=LLM.LOCAL):
        self._use_llm = llm
        # First, hash the prompt
        prompt_hash = hashlib.sha256(
            (prompt + f" LLM {self._use_llm}").encode("utf-8")
        ).hexdigest()
        # Check if the prompt is in the cache
        if self._cacheExists(prompt_hash):
            # If it is, load it from the cache, but also print a warning
            print(bcolors.WARNING + "Using query cache hit" + bcolors.ENDC)
            return self._loadCache(prompt_hash)
        else:
            # Otherwise, run the inference
            response = tns.translate(prompt, image=None, return_query=False)
            # And save it to the cache
            if llm == LLM.GPT:  # Save cache only for GPT (because it costs money...)
                self._saveCache(prompt_hash, response)
            return response

    # This function checks if a prompt is in the cache
    def _cacheExists(self, prompt_hash):
        return prompt_hash in self._cache

    # This function loads a prompt from the cache
    def _loadCache(self, prompt_hash):
        res = TypeChatResult()
        res.from_dict(self._cache[prompt_hash])
        return res

    # This function saves a prompt to the cache
    def _saveCache(self, prompt_hash, response):
        self._cache[prompt_hash] = response.to_dict()
        # Save the cache to disk
        with open("cache.json", "w+") as fh:
            json.dump(self._cache, fh, indent=4)

    # Implements a simple OpenAI interface... this may be mostly for testing atm
    def _llm_generate(
        self, message, max_tokens=512, temperature=0.0, json_mode=None, model=None
    ):
        if model is None:
            model = self._use_llm
        if type(message) == str:
            message = [{"role": "user", "content": message}]

        # Special handling for Starling, which wants "assistant" instead of "agent"
        if "tarling" in self._model_local:
            for p in message:
                if p["role"] == "agent":
                    p["role"] = "assistant"

        # Run the LLM
        completion = None
        if model == LLM.LOCAL:
            completion = self._llm_local.chat.completions.create(
                model=self._model_local,
                messages=message,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}, # this is testing
            )
        elif model == LLM.GPT:
            if self._model_gpt == "deepseek-reasoner":
                    completion = self._llm_gpt.chat.completions.create(
                    model=self._model_gpt,
                    messages=message,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            else:
                completion = self._llm_gpt.chat.completions.create(
                    model=self._model_gpt,
                    messages=message,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
        
        elif model == LLM.DEEPSEEK:
            completion = self._llm_deepseek.chat.completions.create(
                model=self._model_deepseek,
                messages=message,
                max_tokens=max_tokens,
                temperature=temperature,
                # response_format={"type": "json_object"},
            )
        else:
            raise NotImplementedError("Unknown LLM model", model)
        return completion

    def _roleToEnum(self, role):
        role = role.lower()
        if role == "merlin":
            return AROLE.MERLIN
        elif role == "percival":
            return AROLE.PERCIVAL
        elif "servant" in role:
            return AROLE.SERVANT
        elif "minion" in role:
            return AROLE.EVIL
        elif role == "morgana":
            return AROLE.MORGANA
        elif role == "assassin":
            return AROLE.ASSASSIN
        elif role == "evil":
            return AROLE.EVIL
        else:
            return None

    def _enumToRole(self, role):
        if role == AROLE.MERLIN:
            return "Merlin"
        elif role == AROLE.PERCIVAL:
            return "Percival"
        elif role == AROLE.SERVANT:
            return "Servant"
        elif role == AROLE.MORGANA:
            return "Morgana"
        elif role == AROLE.ASSASSIN:
            return "Assassin"
        elif role == AROLE.EVIL:
            return "Evil"
        else:
            return None
