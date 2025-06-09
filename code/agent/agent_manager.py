# This file contains the agent manager that handles the communication between the game server and the agents.
# The manager handles all agents and mapps API calls to the respective endpoints

from fastapi import FastAPI, Request, HTTPException, status
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
from typing import Optional
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from messages import Message, AvalonGameStateUpdate, Task, Reset, Typing, PrivateData
from agent_acl import ACLAgent
from agent_avalonbench import ABenchAgent
from agent_recon import ReConAgent
from agent_test import TestAgent
from agent_deepseek import DeepSeekAgent
from agent_huggingface import HuggingfaceAgent
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from hashids import Hashids

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
PORT = 23003
GAME_SERVER = "http://server:2567/api"  # Use Docker service name
LLM_SERVER = "http://llmserver:23004/api"  # Use Docker service name
print("=== Starting Agent Manager Service ===")
print(f"Expecting local game server at: {GAME_SERVER}")
print(f"Expecting LLM server at: {LLM_SERVER}")

# Define agent roles with their corresponding environment variable names
AGENT_DEFINITIONS = {}

def load_agent_definitions_from_config():
    global AGENT_DEFINITIONS
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            roles = config.get("game", {}).get("roles", [])
            
            # Create agent definitions with incrementing IDs
            AGENT_DEFINITIONS = {
                role: (role.upper().replace("-", ""), i+1) 
                for i, role in enumerate(roles)
            }
            print(f"Loaded agent definitions from config: {AGENT_DEFINITIONS}")
    except Exception as e:
        print(f"Failed to load agent definitions from config: {e}")
        exit(1)

# Load agent definitions when module is imported
load_agent_definitions_from_config()

class AgentManager:
    # The agent manager manages all agents and connects them to the games as needed
    def __init__(self):
        print("Initializing Agent Manager...")
        self._registered_agents = {
            agent_name: {
                "id": agent_id,
                "role": agent_name,
                "type": os.getenv(env_var),
                "player": "human" if os.getenv(env_var) == "human" else "agent",
                "port": None,
            }
            for agent_name, (env_var, agent_id) in AGENT_DEFINITIONS.items()
            if os.getenv(env_var)  # Only add agents with set environment variables
        }
        self._idgen = Hashids()
        self.room_id = None
        self._game_started = False
        self._valid_agents = {}

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

        if (
            len([a for a in self._registered_agents.values() if a["player"] == "human"])
            == 6
        ):
            print("All agents are human, starting game now...")
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(self.startGame)

    @property
    def registered_agents(self):
        """Getter for registered_agents."""
        return self._registered_agents

    @registered_agents.setter
    def registered_agents(self, value):
        """Setter for registered_agents. Triggers logic when updated."""
        self._registered_agents = value
        print("Registered agents updated:", self._registered_agents)

        # Check if the number of agents with a port is 6
        agents_with_port = {
            role: data
            for role, data in self._registered_agents.items()
            if data.get("port") is not None
        }
        containerized_agents = {
            role: data
            for role, data in self._registered_agents.items()
            if data.get("player") != "human"
        }

        if len(agents_with_port) == len(containerized_agents):
            # Run startGame in a separate thread to avoid blocking
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(self.startGame)

    @property
    def room_id(self):
        """Getter for room_id."""
        return self._room_id

    @room_id.setter
    def room_id(self, value):
        """Setter for room_id. Triggers additional logic when room_id is set."""
        self._room_id = value
        print(f"Room ID set to: {self._room_id}")
        self._on_room_id_set()  # Call the internal method to handle the update

    def _on_room_id_set(self):
        pass

    def registerAgent(self, agent_role: str, port: int):
        if agent_role not in self._registered_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent role '{agent_role}' is not registered. Available: {list(self._registered_agents.keys())}",
            )

        if self._registered_agents[agent_role]["port"] is None:
            # Create a new dictionary to trigger the setter
            new_agents = self._registered_agents.copy()
            new_agents[agent_role] = {
                "id": self._registered_agents[agent_role]["id"],  # Keep the ID
                "role": agent_role,  # Add the role
                "type": self._registered_agents[agent_role]["type"],  # Keep the type
                "player": self._registered_agents[agent_role][
                    "player"
                ],  # Keep the player
                "port": port,  # Add the port
            }
            self.registered_agents = new_agents  # Trigger the setter
            return {
                "success": True,
                "message": f"Agent '{agent_role}' added on port {port}.",
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent role '{agent_role}' is already registered on port {self._registered_agents[agent_role]['port']}.",
            )

    def startGame(self):
        """Start the game if there are 6 registered agents ONLY if UI_DRIVEN is false -- (set in env file)."""
        UI_DRIVEN = os.getenv("UI_DRIVEN", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        print("registered: ", len(self._registered_agents))
        if self._game_started == False and not UI_DRIVEN:
            # For some reason, this occausionally starts multiple times...
            self._game_started = True
            # We need to sleep here for a little to make sure the agents all starte up
            print("Waiting 5 seconds before starting game...")
            time.sleep(5)
            print(" --> Requesting game to start...")

            try:
                payload = {
                    "agent_options": {
                        str(idx): {
                            "id": agent["id"],
                            "role": agent["role"],
                            "type": agent["type"],
                            "player": agent["player"],
                        }
                        for idx, agent in enumerate(self._registered_agents.values())
                    }
                }
                print("Payload successfully created:")
                print(payload)

            except Exception as e:
                print(f"❌ Error while creating payload: {e}")

            response = requests.post(f"{GAME_SERVER}/create-room", json=payload)
            if response.status_code == 200:
                print("Message to start game sent successfully!")
                print(response.json())
                roomData = response.json()
                print("  -> Room ID:", roomData["roomId"])
                self.room_id = roomData["roomId"]  # Use the setter to trigger logic
            else:
                print(
                    f"Failed to send message: {response.status_code}, {response.text}"
                )

    # Function to initialize an agent container
    def startAgent(
        self,
        game_id: str,
        agent_type: str,
        agent_name: str,
        agent_role_preference: str,
    ):
        print(
            "Starting agent container:",
            game_id,
            agent_type,
            agent_name,
            agent_role_preference,
        )
        if agent_type == "human":
            print(" -> Skipping human agent startup for player", agent_name)
            return {
                "success": True,
                "message": "Human agent started",
            }
        # Find the agent with the matching role preference
        matching_agent = None
        for role, agent in self._registered_agents.items():
            if agent["role"] == agent_role_preference.lower():
                matching_agent = agent
                print(f"  -> Found agent {agent_role_preference.lower()}: {agent}")
                break

        if not matching_agent:
            return {
                "success": False,
                "message": f"No agent found with role preference {agent_role_preference}",
            }

        # Make API call to the agent's startup endpoint
        try:
            agent_port = matching_agent["port"]
            agent_type = agent_type or matching_agent["type"]
            agent_url = matching_agent["role"].lower().replace("-", "")
            endpoint = f"http://{agent_url}:{agent_port}/api/startup/"

            print('agent type in manager:', agent_type, game_id, agent_name)
            response = requests.get(
                endpoint,
                params={
                    "game_id": game_id,
                    "agent_type": agent_type,
                    "agent_name": agent_name,
                },
            )
            print(f" -> Agent startup response: {response.json()}")
            # Add the agent ID to the valid agents
            self._valid_agents[response.json()["agent_id"]] = matching_agent

            return response.json()
        except Exception as e:
            print(f"Error calling agent startup endpoint ({endpoint}): {e}")
            return {"success": False, "message": f"Error: {str(e)}"}



    # If there are any agents connected, disconnect them
    def shutdown(self):
        print("Disconnecting all agents...")
        # for agent_id, agent in self._valid_agents.items():
        #     print("  -> Disconnecting agent", agent_id)
        #     res = requests.get(GAME_SERVER, json={"action": "leave_game", "agent_id": agent.getID(), "game_id": agent.getGameID()})
        #     res = json.loads(res.text)
        #     print("  -> Response:", res)
        self._valid_agents = {}

    def generateRandomID(self):
        mtime = time.time()
        keys = [int(v) for v in str(mtime).split(".")]
        return self._idgen.encode(keys[0], keys[1])

    # This is the message endpoint, called whenever a message is sent by any user in the same game as the agent
    def agentMessage(self, agent_id: str, message: Message):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in message request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's message endpoint
        try:
            response = requests.post(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/message/",
                json=message.dict(),
            )
            return response.json()
        except Exception as e:
            print(f"Error calling agent message endpoint: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    # This is the state endpoint. This endpoint is called irregularly, but covers the main game changes.
    # Here, the agent that is updated should keep track of it to make inferences.
    def agentState(self, agent_id: str, state: AvalonGameStateUpdate):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in state request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's state endpoint
        try:
            response = requests.post(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/state/",
                json=state.dict(),
            )
            return response.json()
        except Exception as e:
            print(f"Error calling agent state endpoint: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    # This is the typing endpoint. This endpoint is called whenever a user is typing a message.
    def agentIsTyping(self, agent_id: str, typing: Typing):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in state request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's typing endpoint
        try:
            response = requests.post(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/is_typing/",
                json=typing.dict(),
            )
            return response.json()
        except Exception as e:
            print(f"Error calling agent typing endpoint: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    # This is the reset endpoint. This endpoint is called whenever a turn is over.
    def agentReset(self, agent_id: str, reset: Reset):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in state request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's reset endpoint
        try:
            response = requests.post(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/reset/",
                json=reset.dict(),
            )
            return response.json()
        except Exception as e:
            print(f"Error calling agent reset endpoint: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    # This endpoint is called whenever the agent needs to take an action
    def agentAction(self, agent_id: str, task: Task, state: AvalonGameStateUpdate):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in action request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's action endpoint
        try:
            response = requests.post(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/action/",
                json={"task": task.dict(), "state": state.dict()},
            )
            return response.json()
        except Exception as e:
            print(f"Error calling agent action endpoint: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    # Stop the agents
    def shutdownAgent(self, agent_id: str):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in shutdown request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's shutdown endpoint
        try:
            response = requests.get(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/shutdown/"
            )
            # Remove the agent from valid agents
            del self._valid_agents[agent_id]

            # Schedule program exit in 10 seconds
            if not self._valid_agents:
                self._schedule_exit()

            # self._schedule_exit()

            return response.json()
        except Exception as e:
            print(f"Error calling agent shutdown endpoint: {e}")
            # self._schedule_exit()
            return {"success": False, "message": f"Error: {str(e)}"}

    def _schedule_exit(self):
        """Schedule a task to exit the program after 10 seconds."""
        manager.shutdown()

        def exit_program():
            print(
                "Agent shutdown detected: Shutting down agent manager in 10 seconds..."
            )
            time.sleep(10)
            print("Exiting program now.")
            os._exit(0)  # Force exit the program

        # Run the exit task in a separate thread
        exit_thread = ThreadPoolExecutor(max_workers=1)
        exit_thread.submit(exit_program)

    def agentPrivate(self, agent_id: str, data: PrivateData):
        if agent_id not in self._valid_agents:
            print("Invalid agent ID", agent_id, "in private data request")
            return {"success": False, "message": "Agent ID not valid"}

        # Get the agent data
        agent = self._valid_agents[agent_id]
        agent_port = agent["port"]
        agent_url = agent["role"].lower().replace("-", "")

        # Make API call to the agent's private data endpoint
        try:
            response = requests.post(
                f"http://{agent_url}:{agent_port}/api/agent/{agent_id}/private_data/",
                json=data.dict(),
            )
            return response.json()
        except Exception as e:
            print(f"Error calling agent private data endpoint: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}


# The lifespan of the agent manager
# This is handles the startup and shutdown code of the agent manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global manager
    # During startup, initialize the list of valid agents
    manager = AgentManager()

    # Now wait for shutdown
    yield

    # Disconnect all agents...
    manager.shutdown()


# Globally define the app and agent manager...
app = FastAPI(lifespan=lifespan)
manager = None


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
def startAgent(
    game_id: str, agent_name: str, agent_role_preference: str, agent_type: Optional[str] = None,
):
    return manager.startAgent(game_id, agent_type, agent_name, agent_role_preference)


# This is the message endpoint, called whenever a message is sent by any user in the same game as the agent
@app.post("/api/agent/{agent_id}/message/")
def agentMessage(agent_id: str, message: Message):
    return manager.agentMessage(agent_id, message)


# This is the state endpoint. This endpoint is called irregularly, but covers the main game changes.
@app.post("/api/agent/{agent_id}/state/")
def route_state(agent_id: str, state: AvalonGameStateUpdate):
    return manager.agentState(agent_id, state)


# This is the typing endpoint. This endpoint is called whenever a user is typing a message.
@app.post("/api/agent/{agent_id}/is_typing/")
def route_is_typing(agent_id: str, typing: Typing):
    return manager.agentIsTyping(agent_id, typing)


# This is the reset endpoint. This endpoint is called whenever a turn is over.
@app.post("/api/agent/{agent_id}/reset/")
def route_reset(agent_id: str, reset: Reset):
    return manager.agentReset(agent_id, reset)


# This endpoint is called whenever the agent needs to take an action
@app.post("/api/agent/{agent_id}/action/")
def agentAction(agent_id: str, task: Task, state: AvalonGameStateUpdate):
    return manager.agentAction(agent_id, task, state)


# Stop the agents
@app.get("/api/agent/{agent_id}/shutdown/")
def shutdownAgent(agent_id: str):
    return manager.shutdownAgent(agent_id)


@app.get("/api/shutdown")
def shutdownManager(agent_id: str):
    manager._schedule_exit()


# Provide the agent's private data
@app.post("/api/agent/{agent_id}/private_data/")
def agentPrivate(agent_id: str, data: PrivateData):
    return manager.agentPrivate(agent_id, data)


@app.post("/api/register_agent")
def registerAgent(role: str, port: int):
    return manager.registerAgent(agent_role=role, port=port)


def createAgents():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    agent_json_path = os.path.join(script_dir, "agent.json")
    with open(agent_json_path, "r") as file:
        agent_data = json.load(file)

    ids = [agent["id"] for agent in agent_data]
    random.shuffle(ids)
    for i, agent in enumerate(agent_data):
        agent["id"] = ids[i]

    for agent in agent_data:
        payload = requests.post()


# This is the main function that starts the agent manager
if __name__ == "__main__":
    print("\n=== Starting FastAPI Server ===")
    print(f"Host: {local_ip}")
    print(f"Port: {PORT}")
    uvicorn.run(app, host=local_ip, port=PORT)
