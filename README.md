# Bayesian Avalon
This repository contains the code and data for the "Bayesian Social Deduction with Graph-Informed Language Models".

[Project Page](https://camp-lab-purdue.github.io/bayesian-social-deduction/) | [Arxiv](https://arxiv.org/abs/2506.17788) | [Dataset](https://huggingface.co/datasets/shahabrahimirad/bayesian-social-deduction) 

# TLDR;
We developed GRAIL, an agent that uses ptobabilistic graph models to reason about beliefs in the social deduction game of Avalon. The GRAIL agent is able to match the performance of the biggest LRMs with smaller models. 

## Code

The `code/` directory contains the game engine and agent implementations.

The subdirectory includes: core game logic for social deduction mechanics, pre-trained GRAIL agents and baseline reasoning agents, and scripts to simulate games or run human-agent interactions.

See `code/README.md` for full documentation on code structure, agent training, and game configuration [here](code/README.md).

## Human Experiment Data

The `data/` directory contains logs from human-vs-agent experiments. These are the same games from the [human experiment dataset](https://huggingface.co/datasets/shahabrahimirad/bayesian-social-deduction/tree/main/human_experiments), but they have been specifically formatted to be replayable within the Avalon Game Client.

There are 15 experiment folders `02` to `16`, each containing two JSON files &mdash; one GRAIL game and one Reasoning game &mdash; that can be used to re-run the human experiments.

The `data/results/` directory contains two CSV files, one for GRAIL (ours) and one for the Reasoning agent, each providing human evaluation results for the games. Analyses of these results are presented in the main paper and the appendix.

To re-run experiments or map logs to specific agent types, refer to `code/README.md` [here](code/README.md).

## Citation

```bibtex
@misc{rahimirad2025bayesiansocialdeductiongraphinformed,
          title={Bayesian Social Deduction with Graph-Informed Language Models}, 
          author={Shahab Rahimirad and Guven Gergerli and Lucia Romero and Angela Qian and Matthew Lyle Olson and Simon Stepputtis and Joseph Campbell},
          year={2025},
          eprint={2506.17788},
          archivePrefix={arXiv},
          primaryClass={cs.AI},
          url={https://arxiv.org/abs/2506.17788}, 
}
```

## License

MIT License - Open for research and commercial use.