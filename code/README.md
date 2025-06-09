# Bayesian Social Deduction with Graph-Informed Language Models

This code contains all necessary submodules and code to start a game of Avalon either with GRAIL, reasoning agents, or human players.

## Setup

Make sure docker is installed:

```
docker --version 
docker compose version
```

Then, navigate to the main directory and run `docker-compose.yml` with the command:

```
docker compose build
```

## Choosing agents for Avalon

Open the file `.env`, and you will see the following: 

```
HUGGING_FACE_HUB_TOKEN=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
```
You will need to provide your own keys.

For SERVANT and MINION, you can choose which agent to play which role, the available options are:\
`recon` &rarr; Recon agent\
`random` &rarr; agent that performs random actions\
`reason_openai` &rarr; reasoning model of OpenAI (`OPENAI_API_KEY` required)\
`reason_bl` &rarr; reasoning model of DeepSeek (`DEEPSEEK_API_KEY` required)\
`human` &rarr; for human players to play the game

For SERVANT, you can also chose variations of the GRAIL agent:\
`ours` &rarr; GRAIL agent\
`ours_graph_only` &rarr; ablation GRAIL agent with only factor graph inference and no prior probabilty \
`ours_llm_only` &rarr; ablation GRAIL agent with only prior probabilty and no factor graph inference

In order to change the underlying model being used for the agents, go to `config.json` (along with `config_minions.json` and `config_servant.json`) change in `"agent":`\
`model` &rarr; underlying model used by `GRAIL` (for instance gpt-4.1)\
`openai_model` &rarr; underlying model used by `reason_openai` (for instance o4-mini)\
`deepseek_model` &rarr; underlying model used by `reason_bl` (for instance deepseek-reasoner)

As an example, good team of GRAIL competing with an OpenAI model should look like this:

```
SERVANT1=ours
SERVANT2=ours
SERVANT3=ours
SERVANT4=ours
MINION1=reason_openai
MINION2=reason_openai
```

## Starting a game

After the setup, start the game with

```
docker compose up
```

To run multiple consecutive games, navigate to the file `run_avalon.sh`, and edit the `NUM_RUNS` parameter to decide how many consecutive runs to make (default 1). When you call `run_avalon.sh` on the terminal, the games will start. To stop the game prematurely, `Ctrl+C` on the terminal to stop the docker.

## Start the web-UI

In your browser, navigate to http://localhost:1234/admin. This will allow you to see the admin view of the game through the spectator mode. 

To play the game, include a human in the `.env` file and navigate to http://localhost:1234/. Here you should register with a username and password. Then you will be able to log in into the game.

After the game is finished, you can check the logs and the history of the game in the `phaser/server/logs` directory. If the game included the GRAIL agent, you can find the logs and data dump of those agents in the `agent/logs` directory.

## Replay games from game logs

To replay games from the game logs, copy the game JSON file you want to replay into the `phaser/server/logs` directory. Then start the server and navigate to admin mode through http://localhost:1234/admin. Enter the 4-letter room ID of the game that you want to view, which is denoted in the JSON file name.

The human experiment games with GRAIL agents are:
EDVZ, QMQQ, YGRE, IDLQ, TEFW, EZNO, GZAP, FDWF, DUEZ, NQYE, ZEHR, ZQBI, SBSS, OONF, PXYY

The human experiment games with reasoning (o4-mini) agents are:
TAOQ, UNBO, SDAZ, NZGB, WBBU, GTKL, JTGN, JULA, GFYU, GYYE, DKXR, TBED, XVRZ, VASH, TWMO

