from agent_base import BaseAgent, LLM
from messages import Message, AvalonGameStateUpdate, Task
import random
from typing import Dict, List, Optional
from TypeChat.typechat.typechat import TypeChat
from agent_deepseek_prompts import DeepSeekAgentPrompts
from agent_deepseek import DeepSeekAgent
import os
import json

# This is the test agent, which is a very simple agent that just randomly chooses actions and writes pointless messages
# However, this agent is capable to "play", or rather "progress" the game.
class O1Agent(DeepSeekAgent):
    def __init__(
        self,
        agent_id: str,
        game_id: str,
        agent_name: str,
        agent_role_preference: str,
        config: dict,
    ):
        super().__init__(agent_id, game_id, agent_name, agent_role_preference, config)
        
    def call_typechat(
        self,
        input_messages: List[Dict],
        schema_name: str,
        system_prompt: Optional[str] = None,
        schema: str = None,
        path: str = None,
    ):
        try:
            ts = TypeChat()
            ts.createLanguageModel(
                model=self._config["agent"]["openai_model"],
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=self._config["agent"]["openai_base_url"],
                use_ollama=False,
                temperature=self._config["agent"]["typechat_temperature"],
                context_length=self._config["agent"]["typechat_context_length"]
            )
            ts.loadSchema(path=path, schema=schema)
            tns = ts.createJsonTranslator(
                name=schema_name, basedir="./TypeChat/typechat/schemas"
            )
            input_messages = self._tshelper_mergeMessages(input_messages)
            # Save the input messages to a file
            with open(f"openai_o1_input_{self._name}.txt", "w") as f:
                # Pretty-print the content as text
                for message in input_messages:
                    if "content" in message:
                        content = message["content"]  # Don't replace newlines
                        f.write(f"Role: {message['role']}\nContent: {content}\n\n")
            
            response = tns.translate(input_messages, image=None, return_query=False)
            res = None
            if response.success:
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
                    return str(response.data)
                # return response as array to match recon/deepseek
                return res, [response]
            else:
                print("@" * 100)
                print(f"TypeChat error for schema {schema_name}:")
                print(response)
                print("@" * 100)
                return None, None
        except Exception as e:
            print("!" * 100)
            print(f"Exception in call_typechat for schema {schema_name}:")
            print(f"Error: {str(e)}")
            print("!" * 100)
            return None, None