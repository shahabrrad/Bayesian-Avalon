# This file contains the agent manager that handles the communication between the game server and the agents.
# The manager handles all agents and mapps API calls to the respective endpoints

from fastapi import FastAPI, Request, HTTPException
import uvicorn
import socket
from contextlib import closing
import requests
import json
import argparse
from contextlib import asynccontextmanager
import random
import socket
import transformers
import logging
import time
import os
import sys
import threading

from messages import Message, AvalonGameStateUpdate, Task, Reset, Typing, PrivateData
from agent_acl import ACLAgent
from agent_acl_graph_only import ACLAgentGraphOnly
from agent_acl_llm_only import ACLAgentLLMOnly
from agent_avalonbench import ABenchAgent
from agent_recon import ReConAgent
from agent_test import TestAgent
from agent_deepseek import DeepSeekAgent
from agent_o1 import O1Agent
from agent_huggingface import HuggingfaceAgent
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from hashids import Hashids
from requests.adapters import HTTPAdapter, Retry

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Just connect this to the local machine's IP
# local_ip = socket.gethostbyname(socket.gethostname())
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
local_ip = s.getsockname()[0]
local_ip = "0.0.0.0"  # Listen on all interfaces
AGENT_MANAGER_SERVER = "http://agentmanager:23003/api"
LLM_SERVER = "http://llmserver:23004/api"  # Use Docker service name
print("=== Starting Agent Manager Service ===")
print(f"Expecting LLM server at: {LLM_SERVER}")


class Agent:
    def __init__(self):
        self._idgen = Hashids()
        self.role = os.getenv("ROLE", "random")
        self.agent = None
        print(f"Initializing Agent {self.role}...")
        # Load config from file
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            with open(config_path, "r") as f:
                self._config = json.load(f)
                print("Successfully loaded config.json")
        except FileNotFoundError:
            print(
                "Warning: config.json not found at",
                config_path,
                ". Using empty config.",
            )
            self._config = {}
        except json.JSONDecodeError:
            print(
                "Warning: config.json is invalid at",
                config_path,
                ". Using empty config.",
            )
            self._config = {}

    # If there are any agents connected, disconnect them
    def shutdown(self):
        print(f"Disconnecting agent {self.role}...")
        # for agent_id, agent in self._valid_agents.items():
        #     print("  -> Disconnecting agent", agent_id)
        #     res = requests.get(GAME_SERVER, json={"action": "leave_game", "agent_id": agent.getID(), "game_id": agent.getGameID()})
        #     res = json.loads(res.text)
        #     print("  -> Response:", res)
        self.agent = None

    def generateRandomID(self):
        mtime = time.time()
        keys = [int(v) for v in str(mtime).split(".")]
        return self._idgen.encode(keys[0], keys[1])

    # This is the startup endpoint that is called by the user to initialize a new agent
    # Parameters:
    #   game_id: The game ID that the agent should join
    def startAgent(self, game_id: str, agent_type: str, agent_name: str):
        print(f"\nStarting agent request:")
        print(f"  Type: {agent_type}")
        print(f"  Name: {agent_name}")
        print(f"  Game: {game_id}")
        print(f"  Role: {self.role}")

        if agent_type not in [
            "recon",
            "ours",
            "ours_llm_only",
            "ours_graph_only",
            "random",
            "reconmod",
            "reason_bl",
            "hf",
            "reason_openai",
        ]:
            print(f"Error: Invalid agent type '{agent_type}'")
            return {
                "success": False,
                "message": "Unknown agent type '"
                + agent_type
                + "'. Select one of Ours, ReCon, ReCon+, Reason BL, Huggingface, or Random",
            }

        agent_id = self.generateRandomID()
        print(f"  Generated ID: {agent_id}")

        try:
            if agent_type == "recon":
                print("  Creating ReConAgent...")
                self.agent = ReConAgent(agent_id, game_id, agent_name, self.role, self._config, use_mod=False)
            elif agent_type == "reconmod":
                print("  Creating modified ReConAgent...")
                self.agent = ReConAgent(
                    agent_id,
                    game_id,
                    agent_name,
                    self.role.capitalize(),
                    self._config,
                    use_mod=True,
                )
            elif agent_type == "random":
                print("  Creating TestAgent...")
                self.agent = TestAgent(agent_id, game_id, agent_name, self.role, self._config)
            elif agent_type == "ours":
                print("  Creating ACLAgent...")
                self.agent = ACLAgent(agent_id, game_id, agent_name, self.role, self._config)
            elif agent_type == "ours_llm_only":
                print("  Creating ACLAgent LLM Only...")
                self.agent = ACLAgentLLMOnly(agent_id, game_id, agent_name, self.role, self._config)
            elif agent_type == "ours_graph_only":
                print("  Creating ACLAgent Graph Only...")
                self.agent = ACLAgentGraphOnly(agent_id, game_id, agent_name, self.role, self._config)
            elif agent_type == "reason_bl":
                print("  Creating DeepSeekAgent...")
                self.agent = DeepSeekAgent(
                    agent_id,
                    game_id,
                    agent_name,
                    self.role,
                    self._config,
                )
            elif agent_type == "reason_openai":
                print("  Creating O1Agent...")
                self.agent = O1Agent(
                    agent_id,
                    game_id,
                    agent_name,
                    self.role,
                    self._config,
                )
            elif agent_type == "hf":
                print("  Creating HuggingfaceAgent...")
                print(f"  Using config: {self._config}")
                self.agent = HuggingfaceAgent(
                    agent_id,
                    game_id,
                    agent_name,
                    self.role,
                    self._config,
                )
            print(f"  Successfully created agent of type {agent_type}")
        except Exception as e:
            print(f"  Error creating agent: {str(e)}")
            print(f"  Full error: ", e)
            return {"success": False, "message": f"Failed to create agent: {str(e)}"}

        return {
            "success": True,
            "agent_id": agent_id,
            "agent_role_preference": self.role,
            "agent_name_preference": agent_name,
        }

    # This is the message endpoint, called whenever a message is sent by any user in the same game as the agent
    def agentMessage(self, agent_id: str, message: Message):
        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in message request")
            return {"success": False, "message": "Agent ID not valid"}

        res = self.agent.addMessage(message)
        if res:
            return {"success": False, "message": "Message failed to be added"}
        return {"success": True, "message": "Message added"}

    # This is the state endpoint. This endpoint is called irregularly, but covers the main game changes.
    # Here, the agent that is updated should keep track of it to make inferences.
    def agentState(self, agent_id: str, state: AvalonGameStateUpdate):
        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in state request")
            return {"success": False, "message": "Agent ID not valid"}

        # state_dict = state.changes
        # state_dict = {k: v for k, v in state_dict.dict().items() if v is not None}
        # if len(state_dict) > 0:
        result = self.agent.addStateInternal(state)
        # Merge the result with the return values
        return {"success": True}

    # This is the typing endpoint. This endpoint is called whenever a user is typing a message.
    def agentIsTyping(self, agent_id: str, typing: Typing):
        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in state request")
            return {"success": False, "message": "Agent ID not valid"}

        res = self.agent.addTyping(typing)
        if res:
            return res
        return {}

    # This is the reset endpoint. This endpoint is called whenever a turn is over.
    def agentReset(self, agent_id: str, reset: Reset):
        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in state request")
            return {"success": False, "message": "Agent ID not valid"}

        res = self.agent.addReset(reset)
        if res:
            return res
        return {}

    # This endpoint is called whenever the agent needs to take an action
    def agentAction(self, agent_id: str, task: Task, state: AvalonGameStateUpdate):
        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in action request")
            return {"success": False, "message": "Agent ID not valid"}

        res = self.agent.agentActionInternal(task, state)
        if res:
            return res
        return {"success": False, "message": "Agent failed to produce an action"}

    # Stop the agents
    def shutdownAgent(self, agent_id: str):
        global SHUTDOWN_IN_PROGRESS

        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in shutdown request")
            return {"success": False, "message": "Agent ID not valid"}

        # Set the shutdown flag to block new requests
        SHUTDOWN_IN_PROGRESS = True
        print("Setting shutdown flag - rejecting new requests")
        
        self.agent = None
        
        # Schedule application termination after a short delay to allow response to be sent
        def terminate_program():
            print("Agent shutdown successful, terminating program...")
            time.sleep(2)  # Give FastAPI time to send the response
            sys.exit(0)
            
        # Start termination in a separate thread
        threading.Thread(target=terminate_program, daemon=True).start()
        
        return {"success": True, "message": "Agent shutdown successful, terminating program"}

    def agentPrivate(self, agent_id: str, data: PrivateData):
        if not self.agent:
            return {"success": False, "message": "Agent not initialized"}
        
        if agent_id != self.agent._id:
            print("Invalid agent ID", agent_id, "in private data request")
            return {"success": False, "message": "Agent ID not valid"}

        res = self.agent.addPrivateData(data)
        return {"success": True, "message": "Private data added"}


# The lifespan of the agent manager
# This is handles the startup and shutdown code of the agent manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global manager
    # During startup, initialize the list of valid agents
    manager = Agent()
    print("Delaying agent registration for 5 seconds")
    time.sleep(10)
    register(ROLE, PORT)
    # Now wait for shutdown
    yield

    # Disconnect all agents...
    manager.shutdown()


# Globally define the app and agent manager...
app = FastAPI(lifespan=lifespan)
manager = None
# Global shutdown flag to prevent new requests after shutdown is initiated
SHUTDOWN_IN_PROGRESS = False


# Exception handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation error: {exc.errors()}")
    errors = []
    for err in exc.errors():
        error_detail = {
            "loc": err.get("loc", ["unknown location"]),
            "msg": err.get("msg", "Unknown error"),
            "type": err.get("type", "Unknown type"),
        }
        errors.append(error_detail)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": errors,
            "body": exc.body,
        },
    )


# Define all routes
# Adds a new agent to the thing
@app.get("/api/startup/")
def startAgent(game_id: str, agent_type: str, agent_name: str):
    """
    Start a new agent and connect it to a game. Before using any other calls, you need to call this first and send some private data to the agent (see examples). A good example is to ask the agent to produce an action (see example below). Here are some examples:
    - game_id: "12345"
    - agent_type: "hf"
    - agent_name: "Kira"
    
    Parameters:
    - game_id: A string identifier for the game (can be any string, e.g., "12345")
    - agent_type: The type of agent to create. Options: "recon", "ours", "random", "reconmod", "reason_bl", "hf", "reason_openai"
    - agent_name: The display name for the agent (can be any string, e.g. 'Kira')
    
    Returns:
    - JSON with agent details if successful, or error message if failed
    - This also returns the agent's ID which you will need for all other calls!
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    return manager.startAgent(game_id, agent_type, agent_name)


# This is the message endpoint, called whenever a message is sent by any user in the same game as the agent
@app.post("/api/agent/{agent_id}/message/")
def agentMessage(agent_id: str, message: Message):
    """
    Send a message to the agent.
    
    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    - message: The message object containing the text and metadata
    
    Returns:
    - Success status and confirmation message
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    return manager.agentMessage(agent_id, message)


# This is the state endpoint. This endpoint is called irregularly, but covers the main game changes.
@app.post("/api/agent/{agent_id}/state/")
def route_state(agent_id: str, state: AvalonGameStateUpdate):
    """
    Update the agent with the current game state.
    
    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    - state: The game state update object
    
    Returns:
    - Success status
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    return manager.agentState(agent_id, state)


# This is the typing endpoint. This endpoint is called whenever a user is typing a message.
@app.post("/api/agent/{agent_id}/is_typing/")
def route_is_typing(agent_id: str, typing: Typing):
    """
    Notify the agent that a user is typing.
    
    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    - typing: The typing notification object
    
    Returns:
    - Response from the agent or empty object
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    return manager.agentIsTyping(agent_id, typing)


# This is the reset endpoint. This endpoint is called whenever a turn is over.
@app.post("/api/agent/{agent_id}/reset/")
def route_reset(agent_id: str, reset: Reset):
    """
    Reset the agent's state at the end of a turn.
    
    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    - reset: The reset notification object
    
    Returns:
    - Response from the agent or empty object
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    return manager.agentReset(agent_id, reset)


# This endpoint is called whenever the agent needs to take an action
@app.post("/api/agent/{agent_id}/action/")
def agentAction(agent_id: str, task: Task, state: AvalonGameStateUpdate):
    """
    Request the agent to take an action in the game. As an example, you can ask the agent to produce a message. Here is an example:
    {
        "task": [
            "message"
        ],
        "target_party_size": 0,
        "sequence": 1
    }
    
    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    - task: The task object describing what action is needed (see example above)
    - state: The current game state (this makes sure to tell the agents what state exactly they should be using in case the addState is delayed)

    Returns:
    - The agent's action response or error message
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    return manager.agentAction(agent_id, task, state)


# Stop the agents
@app.get("/api/agent/{agent_id}/shutdown/")
def shutdownAgent(agent_id: str):
    """
    Shutdown and disconnect the agent.
    
    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    
    Returns:
    - Success status
    """
    # We still allow shutdown requests even during shutdown
    return manager.shutdownAgent(agent_id)


# Provide the agent's private data
@app.post("/api/agent/{agent_id}/private_data/")
def agentPrivate(agent_id: str, data: PrivateData):
    """
    Send private game data to the agent. This is necessary before you can ask the agent to do anything else. Here is an example that would be suitable for a good servant:
    {
        "name": "Kira",
        "role": "Servant-1",
        "pid": 4,
        "knowledge": {},
        "named_knowledge": {},
        "all_players": {"Jane": "Servant-2", "Mia": "Morgana", "Paul": "Assassin", "Kira": "Servant-1", "Sam": "Percival", "Luca": "Merlin"},
        "order_to_name": {"1": "Jane", "2": "Mia", "3": "Paul", "4": "Kira", "5": "Sam", "6": "Luca"}
    }

    Parameters:
    - agent_id: The unique identifier for the agent (you get this from the startup call)
    - data: The private data object
    
    Returns:
    - Success status and confirmation message
    """
    if SHUTDOWN_IN_PROGRESS:
        raise HTTPException(status_code=503, detail="Server is shutting down, no new requests accepted")
    print("Received private data: ", data)
    return manager.agentPrivate(agent_id, data)


def register(role: str, port: int):
    ENDPOINT = f"{AGENT_MANAGER_SERVER}/register_agent"
    params = {
        "role": role,
        "port": port,
    }
    print("registering agent: ", role)
    print(ENDPOINT)
    try:
        response = requests.post(ENDPOINT, params=params)
        if response.status_code == 404:
            print(f"{role} is not needed")
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        print("An unexpected error occurred:", e)


# This is the main function that starts the agent manager
if __name__ == "__main__":
    print("\n=== Starting FastAPI Server ===")
    print(f"Host: {local_ip}")
    ROLE = os.getenv("ROLE", "random")

    if ROLE.startswith("servant") and ROLE[-1].isdigit():
        SERVANT_ROLE = f"SERVANT{ROLE[-1]}"
        TYPE = os.getenv(SERVANT_ROLE.upper(), "human")
    elif ROLE.startswith("minion") and ROLE[-1].isdigit():
        MINION_ROLE = f"MINION{ROLE[-1]}"
        TYPE = os.getenv(MINION_ROLE.upper(), "human")
    else:
        TYPE = os.getenv(ROLE.upper(), "human")

    if TYPE == "human":
        print(" -> Skipping agent startup for human player")
        exit()
    PORT = int(os.getenv("FASTAPI_PORT", "8000"))
    print(f"Port: {PORT}")
    uvicorn.run(app, host=local_ip, port=PORT)
