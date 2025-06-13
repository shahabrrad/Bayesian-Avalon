# Bayesian Avalon
This repository contains the code and data for the "Bayesian Social Deduction with Graph-Informed Language Models"

## Code

The `code/` directory contains the game engine and agent implementations.

The subdirectory includes: core game logic for social deduction mechanics, pre-trained GRAIL agents and baseline reasoning agents, and scripts to simulate games or run human-agent interactions.

See `code/README.md` for full documentation on code structure, agent training, and game configuration

## Human Experiment Data

The `data/` directory contains logs from human-vs-agent experiments.

There are 15 experiment folders `02` to `16`, each containing two JSON files &mdash; one GRAIL game and one Reasoning game &mdash; that can be used to re-run the human experiments.

The `data/results/` directory contains two CSV files, one for GRAIL (ours) and one for the Reasoning agent, each providing human evaluation results for the games. Analyses of these results are presented in the main paper and the appendix.

To re-run experiments or map logs to specific agent types, refer to `code/README.md`.