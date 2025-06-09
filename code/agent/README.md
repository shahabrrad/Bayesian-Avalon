# Avalon Agent Development

## Running the Agents
Running the agent manager works as follows:
```
python agent/agent_manager_v2.py
```

We also need the LLM backend (Note: This will need memory as it's loading Starling-7B)
```
python agent/llm_backend.py
```

To create agents, you will need to call the agent manager's API with a game ID
```
 curl -d game_id=nel5aK -d agent_type=test -G http://192.168.1.13:23003/api/startup/
```
For example, here we instruct the agent manager to create an agent for game _nel5aK_. Just keep calling that for however many agents you want to create.

There are currently three agents possible:
- _test_: which is a basic agent that does random things to "just run the game"
- _ab_: the AvalonBench base agent
- _acl_: our main agent

## Agent Loop
The game server is implemented as the master and will be updating the agent with various messages throughout the game (e.g., game states and player messages). However, agents will not be able to act on their own. The game server will ask agents to perform an action from a list of allowable actions whenever it is the agent's turn. For this purpose, the agent will sent an API request to the agent and the agent is expected to utilize the latest state information they got in a previous update in order to make a decision. There are three conditions for ending an agent's turn:
- The agent chooses the _end_turn_ action, at which point the game server will move on to the next player/action
- The agent's turn time runs out and the agent's chosen action will not be applied. The game server will move on to the next player prior to an agent's response. You will not be able to detect this (but you can track this on your own through the state)
- The API call from the game server to the agent times out, at which point the game server will end the agent's turn and move on.

### Establishing a Connection
Establishing a connection works as follows:
- User initiates an agent by issuing an /api/startup request (see above) with a game ID
- The agent manager will reach out to the game server to check the game ID and inform the game server about the general API endpoint
- If the game ID exists, the game server will internally add the agent to the requested game and assign a unique ID to the agent
- From now on, the game server will behave as described in the Agent Loop section as above


## Some backup commands
Setup Environment
```
conda deactivate && conda activate emnlp
```

## Quick Summary
Use base emnlp conda env
Run the following: 
streamlit run web_ui.py
Then run agent manager
and also simulate game