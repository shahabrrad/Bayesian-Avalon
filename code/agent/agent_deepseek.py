from agent_base import BaseAgent, LLM
from messages import Message, AvalonGameStateUpdate, Task
import random
from typing import Dict, List, Optional
from TypeChat.typechat.typechat import TypeChat
from agent_deepseek_prompts import DeepSeekAgentPrompts
import os
import json

# This is the test agent, which is a very simple agent that just randomly chooses actions and writes pointless messages
# However, this agent is capable to "play", or rather "progress" the game.
class DeepSeekAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        game_id: str,
        agent_name: str,
        agent_role_preference: str,
        config: dict,
    ):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)
        self._last_actions = []
        self._role = agent_role_preference
        self._config = config

        # Game state tracking
        self._round = 0  # Current quest number
        self._turn = 0  # Current turn number
        self._failed_party_votes = 0  # Number of failed party votes
        self._leader = None  # Current leader name
        self._proposed_team = None  # Current proposed team

        # History tracking
        self._previous_leader_list = []  # Track all previous leaders
        self._previous_player_team_list = []  # Track all previous proposed teams
        self._round_result = []  # Track results of each quest

        # Add history tracking
        self._full_history = []  # List to store all game logs

        # Queue messages
        self.queue_messages = []

    def addMessage(self, message: Message):
        # print("Received message", message.msg)
        return {}

    def addState(self, state: AvalonGameStateUpdate):
        if "quest" in self.state_diff:
            self._round = self.state.quest
            if self.state.quest == 1:
                self.log(
                    "Game Start",
                    "Welcome to Avalon Game. This message signifies the start of a new game. "
                    "The game history from this line onwards is the effective historical game history dialogue of this game!",
                )  # Let's also set the party back to None
            self._proposed_team = None

        if "turn" in self.state_diff:
            # Reset the last actions if the turn ID changes
            self._last_actions = []
            self._turn = self.state.turn

        if "failed_party_votes" in self.state_diff:
            print("failed_party_votes", self.state.failed_party_votes)
            self._failed_party_votes = self.state.failed_party_votes

        if "messages" in self.state_diff:
            # Add the message to the game log
            for msg in self.state_diff["messages"]:
                if msg is None:
                    continue
                actual_msg = msg["msg"]
                if actual_msg != "":
                    pname = msg["player"] if msg["player"] != "system" else "Voiceover"
                    self.log(pname, actual_msg)
                    if "Party vote summary:" in actual_msg:
                        self._previous_player_team_list[-1][2] = actual_msg.split("vote summary:")[1].strip()

        if "proposed_party" in self.state_diff:
            plist = [
                self._private_data.order_to_name[str(order_id)]
                # for order_id in self.state_diff["proposed_party"]
                for order_id in self.state.proposed_party
            ]
            if len(plist) > 0:
                self._proposed_team = plist
                self._previous_player_team_list.append([plist, self._leader, None, self.state.quest])

        if "leader_pid" in self.state_diff:
            if self._private_data:
                lname = self._private_data.order_to_name[
                    str(int(self.state.leader_pid))  # removed + 1 here
                ]
                self._leader = lname
                self._previous_leader_list.append(lname)

        # Track round results
        if "quest_results" in self.state_diff:
            print("Quest results", self.state.quest_results)
            self._round_result = [r == "success" for r in self.state.quest_results]

        return {}

    def _createActionSchema(self, path, actions):
        # Load the schema file and replace ### with the valid actions
        with open(path, "r") as f:
            schema = f.read()
        schema = schema.replace("###", '" | "'.join(actions))
        return schema

    def getAction(self, task: Task, suggestion: str):
        # schema = self._createActionSchema(
        #     "./typechat_deepseek/ActionSelectionSchema.ts", candidates
        # )
        # context = self._createModelContext()
        # messages = [
        #     {"role": "user", "content": context},
        #     {
        #         "role": "user",
        #         "content": DeepSeekAgentPrompts.action_selection_prompt.format(
        #             choices=", ".join(candidates),
        #             past_actions=", ".join(self._last_actions)
        #         ),
        #     },
        # ]
        # taken_action = self.call_typechat(
        #     input_messages=messages,
        #     schema=schema,
        #     schema_name="ActionSelectionSchema",
        # )
        # # Handle None return from call_typechat
        # if taken_action is None:
        #     print(" -> Failed to get action from TypeChat, selecting a random action")
        #     taken_action = random.choice(candidates)

                # First, we need to ask the LLM to choose an action
        taken_action = suggestion
        self._last_actions.append(taken_action)

        print("#" * 100)
        print(f"{self.__class__.__name__}:", self._name, f"({self._private_data.role})", "-> Choosing action:", taken_action) 
        print("#" * 100)

        # The choices should be pretty self-explanatory
        if taken_action == "message":
            # Get the message from the queue
            if len(self.queue_messages) > 0:
                message = self.queue_messages.pop(0)
                return {"success": True, "action": "message", "data": {"msg": message}}
   
            path = "./typechat_deepseek/MessageSchema.ts"
            context = self._createModelContext()
            # Format the team string
            current_team = (
                ", ".join(self._proposed_team)
                if self._proposed_team
                else "no team currently proposed"
            )
            agent_task = "YOUR CURRENT TASK:\n" + (
                DeepSeekAgentPrompts.player_discuss_team_evil_side
                if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"]
                else DeepSeekAgentPrompts.player_discuss_team_good_side
            )
            agent_task = agent_task.format(proposed_team_players=current_team, team_player_num=task.target_party_size)
            messages = [
                {"role": "user", "content": context},
                {"role": "user", "content": agent_task},
            ]

            ts_response, llm_data = self.call_typechat(
                input_messages=messages, path=path, schema_name="MessageSchema"
            )
            # Ensure message is a string and handle None return
            message = str(ts_response) if ts_response is not None else "I'm thinking about the current situation."
            return {"success": True, "action": "message", "data": {"msg": message, "llm_data": llm_data}}
        elif taken_action == "vote_quest":
            llm_data = None
            path = "./typechat_deepseek/QuestVoteSchema.ts"
            context = self._createModelContext()
            agent_task = "YOUR CURRENT TASK:\n" + (
                DeepSeekAgentPrompts.evil_player_quest_vote
                if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"]
                else DeepSeekAgentPrompts.good_player_quest_vote
            )
            messages = [
                {"role": "user", "content": context},
                {"role": "user", "content": agent_task},
            ]
            vote, llm_data = self.call_typechat(
                input_messages=messages, path=path, schema_name="QuestVoteSchema"
            )
            # Handle None return from call_typechat for quest vote
            if vote is None:
                print(" -> Failed to get quest vote from TypeChat, defaulting to success")
                vote = "[success]"
                # Evil roles might want to fail quests
                if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"]:
                    # 50% chance to fail the quest for evil roles when TypeChat fails
                    if random.random() < 0.5:
                        vote = "[fail]"
            
            return {
                "success": True,
                "action": "vote_quest",
                "data": {"vote": vote == "[success]",  "llm_data": llm_data},
            }
        elif taken_action == "vote_party":
            llm_data = None
            path = "./typechat_deepseek/PartyVoteSchema.ts"
            context = self._createModelContext()

            # Format the prompt with current team and reject count
            current_team = (
                ", ".join(self._proposed_team) if self._proposed_team else "no team"
            )

            if self._leader == self._name:
                team_leader_addendum = " Keep in mind that this is your proposed team and as such you should approve it."
            else:
                team_leader_addendum = ""

            agent_task = "YOUR CURRENT TASK:\n" + (
                DeepSeekAgentPrompts.player_team_vote_evil_side
                if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"]
                else DeepSeekAgentPrompts.player_team_vote_good_side
            )
            agent_task = agent_task.format(
                current_proposed_team_players=current_team,
                cur_party_rejects=self._failed_party_votes,
                team_leader_addendum=team_leader_addendum
            )

            messages = [
                {"role": "user", "content": context},
                {"role": "user", "content": agent_task},
            ]
            vote, llm_data  = self.call_typechat(
                input_messages=messages, path=path, schema_name="PartyVoteSchema"
            )
            # Handle None return from call_typechat for party vote
            if vote is None:
                print(" -> Failed to get party vote from TypeChat, defaulting to approve")
                vote = "[approve]"
            # If we have many failed votes already, always approve to avoid game stalling
            if self._failed_party_votes >= 4:
                if not (self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"]):
                    vote = "[approve]"
            
            return {
                "success": True,
                "action": "vote_party",
                "data": {"vote": vote == "[approve]", "llm_data": llm_data},
            }
        elif taken_action == "vote_assassin":
            # Only the Assassin should be making this vote
            if self._private_data.role != "Assassin":
                print(
                    " -> Non-Assassin agent chose to assassinate. This should not happen! Ending turn."
                )
                return {"success": True, "action": "end_turn"}

            schema = self._createAssassinActionSchema()
            context = self._createModelContext()
            messages = [
                {"role": "user", "content": context},
                {"role": "user", "content": "YOUR CURRENT TASK:\n" + DeepSeekAgentPrompts.assassin_prompt},
            ]

            # Get the player name from TypeChat
            selected_player, llm_data = self.call_typechat(
                input_messages=messages, schema=schema, schema_name="AssassinVoteSchema"
            )
            
            # Handle None return from call_typechat for assassin vote
            if selected_player is None:
                print(" -> Failed to get assassin target from TypeChat, selecting random player")
                # Get all player names and select a random one that's not the assassin
                player_names = list(self._private_data.order_to_name.values())
                player_names = [name for name in player_names if name != self._name]
                selected_player = random.choice(player_names)
            
            # Convert player name back to ID
            name_to_order = {
                name: int(order)
                for order, name in self._private_data.order_to_name.items()
            }
            player_id = name_to_order.get(
                selected_player, 1
            )  # Default to 1 if conversion fails

            return {
                "success": True,
                "action": "vote_assassin",
                "data": {"guess": player_id, "llm_data": llm_data},
            }
        elif taken_action == "start_party_vote":
            # No prompting needed, no further decisions to make... :)
            return {"success": True, "action": "start_party_vote", "data": {}}
        elif taken_action == "propose_party":
            schema = self._createProposePartySchema()
            context = self._createModelContext()

            # Choose the appropriate prompt based on role
            agent_task = "YOUR CURRENT TASK:\n" + (
                DeepSeekAgentPrompts.propose_team_evil_side
                if self._private_data.role in ["Assassin", "Morgana", "Minion-1", "Minion-2"]
                else DeepSeekAgentPrompts.propose_team_good_side
            )
            agent_task = agent_task.format(team_player_num=task.target_party_size)

            messages = [
                {"role": "user", "content": context},
                {"role": "user", "content": agent_task},
            ]

            # Get the list of player names from TypeChat
            result, llm_data = self.call_typechat(
                input_messages=messages, schema=schema, schema_name="ProposePartySchema"
            )
            
            # Handle None return from call_typechat for propose party
            if result is None:
                print(" -> Failed to get party proposal from TypeChat, selecting random players")
                # Select random players including self
                all_player_names = list(self._private_data.order_to_name.values())
                # Always include self in the party
                selected_players = [self._name]
                # Fill the rest with random selections
                remaining_players = [p for p in all_player_names if p != self._name]
                if len(remaining_players) >= task.target_party_size - 1:
                    selected_players.extend(random.sample(remaining_players, k=task.target_party_size - 1))
                else:
                    selected_players.extend(remaining_players)
                
                selected_action = ", ".join(selected_players)
                selected_player_message = f"I propose a team consisting of {selected_action}."
            else:
                selected_action, selected_player_message = result
                selected_players = selected_action.split(
                    ", "
                )  # Split the comma-separated string into a list

            print("-" * 100)
            print("Selected players for team:", selected_players)
            print("Message:", selected_player_message)
            print("-" * 100)
            # Convert player names back to IDs
            name_to_order = {
                name: int(order)
                for order, name in self._private_data.order_to_name.items()
            }
            player_ids = [
                name_to_order.get(name.strip(), 1) for name in selected_players
            ]  # Default to 1 if conversion fails

            # Ensure we have the correct number of players
            if len(player_ids) != task.target_party_size:
                print(
                    f"Warning: Selected wrong number of players. Using random selection."
                )
                player_ids = random.sample([1, 2, 3, 4, 5, 6], k=task.target_party_size)

            # queue the message
            self.queue_messages.append(selected_player_message)

            return {
                "success": True,
                "action": "propose_party",
                "data": {"party": player_ids, "llm_data": llm_data},
            }
        elif taken_action == "end_turn":
            # Nothing to decide here
            return {"success": True, "action": "end_turn"}
        else:
            return {"success": False, "message": "Unknown action option"}

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

    def call_typechat(
        self,
        input_messages: List[Dict],
        schema_name: str,
        system_prompt: Optional[str] = None,
        schema: str = None,
        path: str = None,
    ):
        response = None
        try:
            ts = TypeChat()
            ts.createLanguageModel(
                # model=self._config["agent"]["local_model"],
                model=self._config["agent"]["deepseek_model"],
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                # base_url="http://ollama:11434/api/chat",
                base_url=self._config["agent"]["deepseek_base_url"],
                use_ollama=self._config["agent"]["deepseek_use_ollama"],
                remove_think_tags=True,
                retryMaxAttempts=10,
                retryPauseSec=15,
                temperature=self._config["agent"]["typechat_temperature"],
                context_length=self._config["agent"]["typechat_context_length"]
            )
            ts.loadSchema(path=path, schema=schema)
            tns = ts.createJsonTranslator(
                name=schema_name, basedir="./TypeChat/typechat/schemas"
            )
            input_messages = self._tshelper_mergeMessages(input_messages)
            # Save the input messages to a file
            with open(f"deepseek_input_{self._name}.txt", "w") as f:
                # Pretty-print the content as text
                for message in input_messages:
                    if "content" in message:
                        content = message["content"]  # Don't replace newlines
                        f.write(f"Role: {message['role']}\nContent: {content}\n\n")
            
            response = tns.translate(input_messages, image=None, return_query=False)
            if response.success:
                res = None
                if "selected_action" in response.data.keys():
                    res = response.data["selected_action"]
                elif "vote" in response.data.keys():
                    res = f"[{response.data['vote']}]"
                elif "party" in response.data.keys():
                    res = (", ".join(response.data["party"]), response.data["message"])
                elif "message" in response.data.keys():  # MessageSchema has 'message' field
                    res = response.data["message"]
                elif "succeed_quest" in response.data.keys():  # QuestVoteSchema has 'quest' field
                    res = "[success]" if response.data["succeed_quest"] else "[fail]"
                elif "assassinate" in response.data.keys():
                    res = response.data["assassinate"]
                else:
                    print("TypeChat response had unexpected schema")
                    print(f"Schema: {schema_name}, Data: {response.data}")
                    res = str(response.data)
                # return response as array to match recon/o1
                return res, [response]
            else:
                print("@" * 100)
                print(f"TypeChat error for schema {schema_name}:")
                print(response)
                print("@" * 100)
                if response and hasattr(response, "llm_data"):
                    return None, [response]
                else:
                    return None, None
        except Exception as e:
            print("!" * 100)
            print(f"Exception in call_typechat for schema {schema_name}:")
            print(f"Error: {str(e)}")
            print("!" * 100)
            return None, None

    def _tshelper_mergeMessages(self, input_messages):
        merged_input_messages = []
        cur_user_prompt, cur_assistant_prompt = "", ""
        for message in input_messages:
            if message["role"] == "user":
                if len(cur_assistant_prompt) > 0:
                    merged_input_messages.append(
                        {"role": "assistant", "content": cur_assistant_prompt}
                    )
                    cur_assistant_prompt = ""
                cur_user_prompt = cur_user_prompt + message["content"] + "\n\n\n"
            elif message["role"] == "assistant":
                if len(cur_user_prompt) > 0:
                    merged_input_messages.append(
                        {"role": "user", "content": cur_user_prompt}
                    )
                    cur_user_prompt = ""
                cur_assistant_prompt = (
                    cur_assistant_prompt + message["content"] + "\n\n\n"
                )
            else:
                raise ValueError(f"Invalid role: {message['role']}")
        if len(cur_user_prompt) > 0 and len(cur_assistant_prompt) == 0:
            merged_input_messages.append({"role": "user", "content": cur_user_prompt})
        else:
            raise ValueError(f"The last prompt must be user!")
        return merged_input_messages

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
        quest_results = (
            "Quest Results: "
            + " | ".join(
                [
                    f"Quest {i+1}: {'Success' if result else 'Fail'}"
                    for i, result in enumerate(self._round_result)
                ]
            )
            if self._round_result
            else "No quests completed yet"
        )

        # Format current state
        current_leader = (
            f"Current Leader: {self._leader}" if self._leader else "No current leader"
        )
        current_team = (
            f"Proposed Team: {', '.join(self._proposed_team)}"
            if self._proposed_team
            else "No team proposed"
        )

        # Format game history summaries
        # previous_leaders = (
        #     f"Previous Leaders: {', '.join(self._previous_leader_list)}"
        #     if self._previous_leader_list
        #     else "No previous leaders"
        # )
        previous_teams = (
            "Previous Teams:\n    - "
            + "\n    - ".join(
                [
                    f"Team {i+1} (proposed by {proposer} in quest {quest}): {', '.join(team)} | Votes: {votes if votes is not None else 'No votes yet'}" for i, (team, proposer, votes, quest) in enumerate(self._previous_player_team_list)
                ]
            )
            if self._previous_player_team_list
            else "No previous teams"
        )

        # Get role-specific hints
        hint_key = self._role.lower().split("-")[0]
        role_hint = DeepSeekAgentPrompts.role_hints[hint_key].format(name=self._name)

        # String for last actions
        last_actions_string = (
            "None" if len(self._last_actions) == 0 else ", ".join(self._last_actions)
        )

        # Special Knowledge
        special_knowledge = (
            "Your special information, just for you, is: "
            + ", ".join(
                [
                    f"{self._private_data.named_knowledge[pid]}: {self._private_data.knowledge[pid]}"
                    for pid in self._private_data.knowledge
                ]
            )
            if hasattr(self._private_data, "knowledge")
            else "None"
        )

        # Build the complete context
        context = [
            DeepSeekAgentPrompts.game_rule,
            "",
            "YOUR ROLE AND INFORMATION:",
            # f"You are playing as {self._name} and your role is {self._role}.",
            role_hint,
            special_knowledge,
            DeepSeekAgentPrompts.non_disclosure_prompt,
            "",
            "YOUR PRIOR ACTIONS THIS TURN:",
            f"{last_actions_string}",
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
            # f" - {previous_leaders}",
            f"{previous_teams}",
            "",
            "DETAILED GAME LOG (most recent messages are last):\n", # Adding a final \n because it doesn't get one from the join as it's the last item
        ]
        # TODO: We might need to match which leaders lead to what quest outcome?
        context = "\n".join(context)

        # Add the last 10 messages from game history for context
        for subject, message in self._full_history:
            context += f" - {subject}: {message}\n"

        return context

    def _createAssassinActionSchema(self) -> str:
        """Creates schema for assassin vote with valid player names"""
        # Get all player names from private data
        player_names = list(self._private_data.order_to_name.values())

        # Load and customize the schema
        with open("./typechat_deepseek/AssassinVoteSchema.ts", "r") as f:
            schema = f.read()
        schema = schema.replace("###", '" | "'.join(player_names))
        return schema

    def _createProposePartySchema(self) -> str:
        """Creates schema for party proposal with valid player names"""
        # Get all player names from private data
        player_names = list(self._private_data.order_to_name.values())

        # Load and customize the schema
        with open("./typechat_deepseek/ProposePartySchema.ts", "r") as f:
            schema = f.read()
        schema = schema.replace("###", '" | "'.join(player_names))
        return schema
