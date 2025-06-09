# This file contains message definitions for the agent API.

from pydantic import BaseModel, Field
from typing import Union, Optional, List

# This message "Message" defines a chat message sent by a user
# Parameters:
#   quest: The quest number
#   turn: The turn number
#   room: The room ID (typically the game ID)
#   player: The name of the player sending the message
#   msg: The message itself
#   strategy: The strategy label the player can assign to the message
#   pid: The player ID. This is the player id in the game [1, .., 6]
#   mid: The random message ID
class Message(BaseModel):
    quest: int
    turn: int
    room: str
    player: str
    msg: str
    strategy: list
    pid: Union[int, None] = None
    mid: str

# This message "Typing" defines a typing indicator for the current player
# Parameters:
#   player: The name of the player typing a message
#   room: The room ID (typically the game ID)
#   quest: The quest number
#   turn: The turn number
class Typing(BaseModel):
    player: str
    room: str
    quest: int
    turn: int

# This message "Reset" defines a reset message that is sent after each turn. This is mainly used for the web-clients in case they got disconnected
# For the agent, this message is not really needed
# Parameters:
#   room: The room ID (typically the game ID)
#   quest: The quest number
#   turn: The turn number
class Reset(BaseModel):
    room: str
    quest: int
    turn: int

# This message "Task" defines the task that the agent needs to perform
# You can choose any of the actions defined in task
# The server will keep asking you to take an action until either your turn time ends, or you send the "end_turn" action
# Note that end_turn is not a part of the valid actions listed in task (but maybe should be as it's not always a valid action)
# Parameters:
#   task: A list of possible actions that the agent can take
#       Possible tasks:
#       - "vote_quest": Vote on the quest
#       - "vote_party": Vote on the party
#       - "vote_assassin": Vote on who merlin is
#       - "start_party_vote": Start a vote on the party
#       - "propose_party": Propose a party
#       - "message": Send a message
#   target_party_size: The number of players that agent can propose
#   sequence: The number of actions that the agent has taken so far in this turn
class Task(BaseModel):
    task: list
    target_party_size: int
    sequence: int

# Message for the game simulator mimicking an actual game
class SimulationAPI(BaseModel):
    action: str
    game_id: Optional[str] = None
    agent_api: Optional[str] = None
    agent_type: Optional[str] = None
    agent_role_preference: Optional[str] = None

# Class representing the private ata
class PrivateData(BaseModel):
    name: str
    role: str
    pid: int
    knowledge: dict
    named_knowledge: dict
    all_players: dict
    order_to_name: dict

## Updated state to match Colyseus state:

class AvalonStateMessage(BaseModel):
    quest: int = None
    turn: int = None
    room: str = None
    player: str = None
    msg: str = None
    strategy: List[str] = None
    pid: int = None
    mid: str = None

class AvalonGameState(BaseModel):
    players: Optional[List[Optional[str]]] = None
    all_joined: Optional[bool] = None
    player_order: Optional[List[int]] = None
    messages: Optional[List[Optional[AvalonStateMessage]]] = None
    winner: Optional[str] = None
    leader_pid: Optional[int] = None
    turn_pid: Optional[int] = None
    quest: Optional[int] = None
    turn: Optional[int] = None
    can_propose_party: Optional[bool] = None
    target_party_size: Optional[int] = None
    turn_timer: Optional[float] = None
    proposed_party: Optional[List[Optional[int]]] = None
    vote_party: Optional[bool] = None
    vote_quest: Optional[bool] = None
    failed_party_votes: Optional[int] = None
    quest_results: Optional[List[Optional[str]]] = None
    party: Optional[List[str]] = None
    vote_assassin: Optional[bool] = None
    all_roles: Optional[List[str]] = None
    room: Optional[str] = None

class AvalonGameStateUpdate(BaseModel):
    timestamp: str
    changes: Optional[AvalonGameState] = None
    full: Optional[AvalonGameState] = None