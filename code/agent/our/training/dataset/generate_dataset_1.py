from itertools import combinations
import os
import json
from itertools import permutations
import torch
import csv
from tqdm import tqdm


AVALONLOGS_6P_FOLDER = "6_player"
def cyclic_perm(a):
    n = len(a)
    b = [[a[i - j] for i in range(n)] for j in range(n)]
    return b



def vectorize_game_history(json_data, circular=True, partial=False, extra=1):
    """
    This function takes a game history in json format and returns a vectorized version of it.
    The vectorized version is for 6p_pomegranate file
    The circular flag determines if we want to augment the data with all permutations of the player orders
    the partial flag determines if we want to creates vectors for when the game is not over yet
    the extra flag determines if the game state will have an extra category to determine incompleteness of the game
    """

    player_names = [player['name'] for player in json_data['players']]

    #This for loop augments data with all permutations of the player orders
    vectors = []

    if circular:
        player_permutations = cyclic_perm(player_names)
    else:
        player_permutations = [player_names]
    
    for player_names in player_permutations:
        vector = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        # vector = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]


        player_roles = {player['name']: 0 for player in json_data['players']}

        vote_compositions = []
        for L in range(4, 6 + 1):
            for subset in combinations(player_names, L):
                vote_compositions.append(subset)
        
        # turn it to set to make sure we can find things in it
        vote_compositions = [set(vote_comp) for vote_comp in vote_compositions]

        # this sets the player roles as either 0 or 1
        for role in json_data['outcome']['roles']:
            if role['role'] not in ['LOYAL FOLLOWER', 'MERLIN', 'PERCIVAL', 'SERVANT']:
                player_roles[role['name']] = 1
        
        # fill the vector with roles
        for i, name in enumerate(player_names):
            vector[i] = player_roles[name]

        for i in range(len(json_data['missions'])):
            mission = json_data['missions'][i]
            if mission['state'] == 'PENDING':
                break
            team_size = mission['teamSize']
            # print(mission)
            team = mission['proposals'][-1]['team']
            final_proposals = mission['proposals'][-1]
            # proposer = final_proposals['proposer']
            # proposer = player_names.index(proposer)

            party_compositions = list(combinations(player_names, team_size))
            party_compositions = [set(party_comp) for party_comp in party_compositions]

            team_comp_number = party_compositions.index(set(team))
            vote_comp_number = vote_compositions.index(set(final_proposals['votes']))

            vector[6 + (i*3)] = team_comp_number + extra
            vector[6 + (i*3) + 1] = vote_comp_number + extra
            if mission['state'] == 'SUCCESS':
                vector[6 + (i*3) + 2] = 1   + extra
            else:
                vector[6 + (i*3) + 2] = 0   + extra
            # vector[6 + (i*4) + 2] = proposer + extra

        # this is because we are doing all permutations:
        vectors.append(vector) # TODO I am commenting this so that we never train on full games.

        
        if partial:
            if vector[-3] != 0:
                new_vector = vector[:-3] + [0, 0, 0]
                vectors.append(new_vector)
            if vector[-6] != 0:
                new_vector = vector[:-6] + [0, 0, 0, 0, 0, 0]
                vectors.append(new_vector)
            if vector[-9] != 0:
                new_vector = vector[:-9] + [0, 0, 0, 0, 0, 0, 0, 0, 0]
                vectors.append(new_vector)
            if vector[-12] != 0:
                new_vector = vector[:-12] + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                vectors.append(new_vector)
        # new_vector = vector[:-12] + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        # vectors.append(new_vector)
        
        # vector = vector + llm_guess
    # print(*vectors)
    # exit()

    # return vector
    return vectors



def read_and_vectorize_game_history(file_path, circular=True, partial=False):
    with open(file_path, 'r') as file:
        json_data = json.load(file)
    return vectorize_game_history(json_data, circular=circular, partial=partial)

def vectorize_all_games_in_folder(folder_path="6_player"):
    vectors = []
    for file_name in tqdm(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            # vectors.append(read_and_vectorize_game_history(file_path))
            # this is because I am doing all permutations thing
            vectors += read_and_vectorize_game_history(file_path)
    return vectors

def get_game_results_from_file(file_path):
    with open(file_path, 'r') as file:
        json_data = json.load(file)
    return get_game_result(json_data)

def get_game_result(json_data):
    player_names = [player['name'] for player in json_data['players']]
    outcome = json_data["outcome"]
    assassinated = outcome["assassinated"]
    if not (outcome["assassinated"] is None):
        assassinated = player_names.index(outcome["assassinated"])
    game_length = len([mission for mission in json_data['missions'] if mission['state'] != 'PENDING'])
    return {"length":game_length, "outcome": outcome["state"], "message": outcome["message"], "assassinated": assassinated}



def vectorize_train_validation_test_sets(folder_path=AVALONLOGS_6P_FOLDER, train_percentage=0.7):
    train_percentage = 0.7
    train_vectors = []
    files_list = os.listdir(folder_path)
    number_of_files = len(files_list)
    train_files = files_list[:int(number_of_files * train_percentage)]
    validation_files = files_list[int(number_of_files * train_percentage) : int(number_of_files * train_percentage) + int(number_of_files * (1 - train_percentage) / 2)]
    test_files = files_list[int(number_of_files * train_percentage) + int(number_of_files * (1 - train_percentage) / 2):]  
    for file_name in train_files:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            train_vectors += read_and_vectorize_game_history(file_path, circular=True, partial=True)
            # train_vectors += read_and_vectorize_game_history(file_path, circular=True, partial=False)  #TODO turn this back
    validation_vectors = []
    validation_states = []
    for file_name in validation_files:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            # validation_vectors += read_and_vectorize_game_history(file_path, circular=True, partial=False)
            validation_vectors += read_and_vectorize_game_history(file_path, circular=False, partial=True)
            game_result = get_game_results_from_file(file_path)
            game_result["game_id"] = file_name
            validation_states.append(game_result)

    test_vectors = []
    for file_name in test_files:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            # test_vectors += read_and_vectorize_game_history(file_path, circular=True, partial=False)
            test_vectors += read_and_vectorize_game_history(file_path, circular=False, partial=True)
            game_result = get_game_results_from_file(file_path)
            game_result["game_id"] = file_name
            # validation_states.append(game_result)
    return train_vectors, validation_vectors, test_vectors