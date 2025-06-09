For training the model, you need to first download the datasets used for the trianing.

Clone the avalonlogs github [https://github.com/WhoaWhoa/avalonlogs] here then extract 6 player games by running the `dataset/extract_6player_logs.py` file. The directory of the logs from the avalonlogs dataset will be used in the `generate_dataset_1` script.

Request the game data from the ProAvalon website [https://proavalon.com/statistics]. The json file will be used in the `generate_dataset_2` script