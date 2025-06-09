from agent_base import BaseAgent, LLM
from messages import Message, AvalonGameStateUpdate, Task
import random
from typing import Dict, List, Optional
import torch
from transformers import pipeline
from agent_deepseek_prompts import DeepSeekAgentPrompts

class HuggingfaceAgent(BaseAgent):
    def __init__(self, agent_id: str, game_id: str, agent_name: str, agent_role_preference: str, config: dict):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)
        self._last_actions = []
        self._role = agent_role_preference
        self._config = config

        print("This agent is broken due to the role names")
        exit()
        
        # Initialize the HuggingFace pipeline
        self.pipe = pipeline(
            "text-generation",
            model=self._config["agent"]["hf_base_model"],
            torch_dtype=torch.float16,
            device_map="auto",
        )
        
        # Game state tracking (same as DeepSeekAgent)
        self._round = 0
        self._turn = 0
        self._failed_party_votes = 0
        self._leader = None
        self._proposed_team = None
        self._previous_leader_list = []
        self._previous_player_team_list = []
        self._round_result = []
        self._full_history = []

    def addMessage(self, message: Message):
        # print("Received message", message.msg)
        return {}
    
    def addState(self, state: AvalonGameStateUpdate):
        print("STATE UPDATE", self.state_diff)

        if "quest" in self.state_diff:
            self._round = self.state.quest
            if self.state_diff["quest"] == 1:
                self.log(
                    "Game Start",
                    "Welcome to Avalon Game. This message signifies the start of a new game. "
                    "The game history from this line onwards is the effective historical game history dialogue of this game!",
                )            # Let's also set the party back to None
            self._proposed_team = None

        if "turn" in self.state_diff:
            # Reset the last actions if the turn ID changes
            self._last_actions = []
            self._turn = self.state_diff["turn"]

        if "failed_party_votes" in self.state_diff:
            print("failed_party_votes", self.state_diff["failed_party_votes"])
            self._failed_party_votes = self.state_diff["failed_party_votes"]

        if "messages" in self.state_diff:
            # Add the message to the game log
            for msg in self.state_diff["messages"]:
                if msg is None:
                    continue
                actual_msg = msg["msg"]
                if actual_msg != "":
                    pname = (
                        msg["player"] if msg["player"] != "system" else "Voiceover"
                    )
                    self.log(pname, actual_msg)

        if "proposed_party" in self.state_diff:
            plist = [
                self._private_data.order_to_name[str(order_id)]
                for order_id in self.state_diff["proposed_party"]
            ]
            self._proposed_team = plist
            self._previous_player_team_list.append(plist)

        if "leader_pid" in self.state_diff:
            lname = self._private_data.order_to_name[
                str(int(self.state_diff["leader_pid"]))  # removed + 1 here
            ]
            self._leader = lname
            self._previous_leader_list.append(lname)

        # Track round results
        if "quest_results" in self.state_diff:
            print("Quest results", self.state_diff["quest_results"])
            for msg in self.state_diff["quest_results"]:
                print(f"message for quest {msg}")
                if msg is not None:
                    self._round_result.append(msg)

        return {}

    def log(self, subject: str, message: str):
        """
        Log a message with its subject to the game history.
        
        Args:
            subject (str): The source/subject of the message (e.g., player name, "Voiceover", "Game Start")
            message (str): The actual message content
        """
        self._full_history.append([subject, message])
        
    def get_full_history_list(self) -> list:
        """
        Returns a copy of the full game history.
        
        Returns:
            list: List of (subject, message) tuples
        """
        return [(entry[0], entry[1]) for entry in self._full_history]

    def call_huggingface(self, context: str, prompt: str) -> str:
        """
        Replace TypeChat with direct HuggingFace model calls
        """
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ]
        
        outputs = self.pipe(
            messages,
            max_new_tokens=self._config["agent"]["typechat_context_length"],
            do_sample=True,
            temperature=self._config["agent"]["typechat_temperature"],
            top_p=0.9,
        )
        
        # Get the generated conversation
        response = outputs[0]["generated_text"]
        
        # Find the last assistant message
        try:
            for msg in reversed(response):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    return msg.get("content", "").strip()
        except:
            # Fallback: if we can't parse the response, return the raw output
            return str(response).strip()

    def getAction(self, task: Task, suggestion: str):
        # context = self._createModelContext()
        # prompt = DeepSeekAgentPrompts.action_selection_prompt.format(choices=", ".join(candidates))
        # response = self.call_huggingface(context, prompt)
        # taken_action = self._extract_action(response, candidates)

        taken_action = suggestion
        print("#" * 100)
        print("HuggingFace Agent:", self._name, f"({self._private_data.role})", "-> Choosing action:", taken_action) 
        print("#" * 100)
        
        # Handle different actions
        if taken_action == "message":
            context = self._createModelContext()
            # Format the team string
            current_team = ", ".join(self._proposed_team) if self._proposed_team else "no team currently proposed"
            agent_task = (DeepSeekAgentPrompts.player_discuss_team_evil_side 
                         if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"] 
                         else DeepSeekAgentPrompts.player_discuss_team_good_side)
            agent_task = agent_task.format(proposed_team_players=current_team)
            message = self.call_huggingface(context, agent_task)
            return {"success": True, "action": "message", "data": {"msg": message}}
        elif taken_action == "vote_quest":
            context = self._createModelContext()
            agent_task = (DeepSeekAgentPrompts.evil_player_quest_vote 
                         if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"] 
                         else DeepSeekAgentPrompts.good_player_quest_vote)
            vote = self.call_huggingface(context, agent_task)
            return {"success": True, "action": "vote_quest", "data": {"vote": "[success]" in vote.lower()}}
        elif taken_action == "vote_party":
            context = self._createModelContext()
            
            # Format the prompt with current team and reject count
            current_team = ", ".join(self._proposed_team) if self._proposed_team else "no team"
            agent_task = (DeepSeekAgentPrompts.player_team_vote_evil_side 
                         if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"] 
                         else DeepSeekAgentPrompts.player_team_vote_good_side)
            agent_task = agent_task.format(
                current_proposed_team_players=current_team,
                cur_party_rejects=self._failed_party_votes
            )
            
            vote = self.call_huggingface(context, agent_task)
            return {"success": True, "action": "vote_party", "data": {"vote": "[approve]" in vote.lower()}}
        elif taken_action == "vote_assassin":
            # Only the Assassin should be making this vote
            if self._private_data.role != "Assassin":
                print(" -> Non-Assassin agent chose to assassinate. This should not happen! Ending turn.")
                return {"success": True, "action": "end_turn"}
            
            context = self._createModelContext()
            response = self.call_huggingface(context, DeepSeekAgentPrompts.assassin_prompt)
            
            # Extract player name from response
            # Convert player name back to ID
            name_to_order = {name: int(order) for order, name in self._private_data.order_to_name.items()}
            # Look for each player name in response and use first match
            selected_player = None
            for name in self._private_data.order_to_name.values():
                if name.lower() in response.lower():
                    selected_player = name
                    break
            player_id = name_to_order.get(selected_player, 1) if selected_player else 1  # Default to 1 if no match
            
            return {"success": True, "action": "vote_assassin", "data": {"guess": player_id}}
        elif taken_action == "start_party_vote":
            # No prompting needed, no further decisions to make
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif taken_action == "propose_party":
            context = self._createModelContext()
            
            # Choose the appropriate prompt based on role
            agent_task = (DeepSeekAgentPrompts.propose_team_evil_side 
                         if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"] 
                         else DeepSeekAgentPrompts.propose_team_good_side)
            agent_task = agent_task.format(team_player_num=task.target_party_size)
            
            response = self.call_huggingface(context, agent_task)
            
            # Extract player names from response
            # Look for each player name in response
            selected_players = []
            for name in self._private_data.order_to_name.values():
                if name.lower() in response.lower():
                    selected_players.append(name)
            
            # Convert player names back to IDs
            name_to_order = {name: int(order) for order, name in self._private_data.order_to_name.items()}
            player_ids = [name_to_order.get(name, 1) for name in selected_players]  # Default to 1 if conversion fails
            
            # Ensure we have the correct number of players
            if len(player_ids) != task.target_party_size:
                print(f"Warning: Selected wrong number of players. Using random selection.")
                player_ids = random.sample([1, 2, 3, 4, 5, 6], k=task.target_party_size)
            
            return {"success": True, "action": "propose_party", "data": {"party": player_ids}}
        elif taken_action == "end_turn":
            # Nothing to decide here
            return {"success": True, "action": "end_turn"}

        return {"success": False, "message": "Unknown action option"}

    def _extract_action(self, response: str, candidates: List[str]) -> str:
        """
        Extract the action from the model's response
        """
        # Simple extraction - look for each candidate in the response
        for action in candidates:
            if action.lower() in response.lower():
                return action
        # Default to the first candidate if no match is found
        return candidates[0]

    def _createModelContext(self) -> str:
        """
        Creates a comprehensive context string for the LLM containing game state, 
        player information, role hints, and game history.
        """
        # Get basic game information
        current_round = f"Current Quest: {self._round}"
        current_turn = f"Current Turn: {self._turn}"
        failed_votes = f"Failed Party Votes: {self._failed_party_votes}"
        
        # Format quest results
        quest_results = "Quest Results: " + ", ".join(
            [f"Quest {i+1}: {'Success' if result else 'Fail'}" 
             for i, result in enumerate(self._round_result)]
        ) if self._round_result else "No quests completed yet"
        
        # Format current state
        current_leader = f"Current Leader: {self._leader}" if self._leader else "No current leader"
        current_team = f"Proposed Team: {', '.join(self._proposed_team)}" if self._proposed_team else "No team proposed"
        
        # Format game history summaries
        previous_leaders = f"Previous Leaders: {', '.join(self._previous_leader_list)}" if self._previous_leader_list else "No previous leaders"
        previous_teams = "Previous Teams: " + " | ".join(
            [f"Team {i+1}: {', '.join(team)}" 
             for i, team in enumerate(self._previous_player_team_list)]
        ) if self._previous_player_team_list else "No previous teams"
        
        # Get role-specific hints
        role_hint = DeepSeekAgentPrompts.role_hints.get(self._role, "")
        
        # String for last actions
        last_actions_string = "None" if len(self._last_actions) == 0 else ', '.join(self._last_actions)

        # Special Knowledge
        special_knowledge = "Your special information, just for you, is: " + ", ".join([f"{self._private_data.named_knowledge[pid]}: {self._private_data.knowledge[pid]}" for pid in self._private_data.knowledge]) if hasattr(self._private_data, "knowledge") else "None"

        # Build the complete context
        context = [
            DeepSeekAgentPrompts.game_rule,
            "",
            "YOUR ROLE AND INFORMATION:",
            f"You are playing as {self._name} and your role is {self._role}.",
            role_hint,
            special_knowledge,
            DeepSeekAgentPrompts.non_disclosure_prompt,
            "",
            "YOUR PRIOR ACTIONS THIS TURN:",
            f"{last_actions_string}"
            "",
            "CURRENT GAME STATE:",
            f" - {current_round}",
            f" - {current_turn}",
            f" - {failed_votes}",
            f" - {quest_results}",
            f" - {current_leader}",
            f" - {current_team}",
            "",
            "GAME HISTORY:",
            f" - {previous_leaders}",
            f" - {previous_teams}",
            "",
            "DETAILED GAME LOG:"
        ]
        # TODO: We might need to match which leaders lead to what quest outcome?
        context = "\n".join(context)
        
        # Add the last 10 messages from game history for context
        recent_history = self._full_history[-10:] if len(self._full_history) > 10 else self._full_history
        for subject, message in recent_history:
            context += f" - {subject}: {message}\n"
        
        return context

    def _createAssassinActionSchema(self) -> str:
        """Creates schema for assassin vote with valid player names"""
        # Get all player names from private data
        player_names = list(self._private_data.order_to_name.values())
        
        # Load and customize the schema
        with open("./typechat_deepseek/AssassinVoteSchema.ts", "r") as f:
            schema = f.read()
        schema = schema.replace("###", "\" | \"".join(player_names))
        return schema

    def _createProposePartySchema(self) -> str:
        """Creates schema for party proposal with valid player names"""
        # Get all player names from private data
        player_names = list(self._private_data.order_to_name.values())
        
        # Load and customize the schema
        with open("./typechat_deepseek/ProposePartySchema.ts", "r") as f:
            schema = f.read()
        schema = schema.replace("###", "\" | \"".join(player_names))
        return schema
