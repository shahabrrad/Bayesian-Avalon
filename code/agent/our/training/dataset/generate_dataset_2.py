import json
from itertools import combinations
from tqdm import tqdm

# Read the JSON file
FILE = 'Enter the direcotry path to the json file from the ProAvalon dataset here'

def cyclic_perm(a):
    n = len(a)
    b = [[a[i - j] for i in range(n)] for j in range(n)]
    return b

def get_leader_order(data):
    vote_history = data["voteHistory"]
    players = list(vote_history.keys())
    leader_order = []
    num_missions = len(vote_history[players[0]])
    for mission_index in range(num_missions):
        num_proposals = len(vote_history[players[0]][mission_index])
        for proposal_index in range(num_proposals):
            for p in players:
                vote_str = vote_history[p][mission_index][proposal_index]
                if 'VHleader' in vote_str:
                    leader_order.append(p)
                    break
    
    return leader_order


def get_leader_order_one_cycle(data):
    # data = json.loads(json_str)
    vote_history = data["voteHistory"]
    players = list(vote_history.keys())
    n_players = data["numberOfPlayers"]
    player_order = data["playerUsernamesOrderedReversed"]
    if player_order == []:
        player_order = ['a', 'f', 'e', 'd', 'c', 'b']
    
    leader_order = []
    found_leaders = set()  # Keep track of unique leaders we've seen

    num_missions = len(vote_history[players[0]])
    
    for mission_index in range(num_missions):
        num_proposals = len(vote_history[players[0]][mission_index])
        
        for proposal_index in range(num_proposals):
            for p in players:
                vote_str = vote_history[p][mission_index][proposal_index]
                if 'VHleader' in vote_str:
                    # If this is a brand new leader, add to list & set
                    if p not in found_leaders:
                        leader_order.append(p)
                        found_leaders.add(p)
                    if len(found_leaders) == n_players:
                        return leader_order

                    break
    if len(leader_order) < n_players:
        while leader_order[0] != player_order[0]:
            player_order.insert(0, player_order.pop())
        leader_order = player_order
        # print(leader_order)
        # print()
       
    if len(leader_order) != 6:
        print(data)
        print(player_order)
        print(leader_order)
        exit()
    # print(leader_order)
    return leader_order


def vectorize_game(data, player_order):
    """given a game and the ordering of the players, generates the final state vector of that game based on the player ordering"""
    # print(data)
    # game_vecctor = [0,]* 6 + ([0,]*3) * 5  # 6 players, 5 missions, 3 features per mission
    res_players = [p for p, info in data["playerRoles"].items() if info["alliance"] == "Resistance"]
    spy_players = [p for p, info in data["playerRoles"].items() if info["alliance"] == "Spy"]

    # player_order = get_leader_order_one_cycle(data)
    # print(name_2_index)
    name_2_index = {player_order[i]: i for i in range(len(player_order))}
    # print(name_2_index)
    vote_compositions = []
    for L in range(4, 6 + 1):
        for subset in combinations(player_order, L):
            vote_compositions.append(subset)
    
    # turn it to set to make sure we can find things in it
    vote_compositions = [set(vote_comp) for vote_comp in vote_compositions]

    role_vector = [0] * len(player_order)
    for spy in spy_players:
        role_vector[name_2_index[spy]] = 1
    
    num_missions = len(data["voteHistory"][player_order[0]])
    if "Hammer" in data["howTheGameWasWon"]:  # remove the last mission if it was rejected into oblivion
        num_missions = num_missions - 1
    num_players = data["numberOfPlayers"]
    majority_count = (num_players // 2) + 1

    game_vecctor = role_vector
    for mission_index in range(num_missions):
        mission_vector = [0,0,0]  # [team composition, vote composition, success]
        accepted_proposal_index = -1
        leader = None
        picked_players = []
        approving_players = []

        for player in player_order:
            vote_str = data["voteHistory"][player][mission_index][accepted_proposal_index]
            if "VHleader" in vote_str:
                leader = player
            if "VHpicked" in vote_str:
                picked_players.append(player)
            if "VHapprove" in vote_str:
                approving_players.append(player)
        
        mission_result = data['missionHistory'][mission_index]
        party_compositions = list(combinations(player_order, len(picked_players)))
        party_compositions = [set(party_comp) for party_comp in party_compositions]

        team_comp_number = party_compositions.index(set(picked_players))
        vote_comp_number = vote_compositions.index(set(approving_players))
        mission_result_number = 1 if mission_result == "succeeded" else 0
        

        mission_vector[0] = team_comp_number + 1
        mission_vector[1] = vote_comp_number + 1
        mission_vector[2] = mission_result_number + 1

        game_vecctor += mission_vector
    
    # extend the game vector to pad for the unplayed quests
    while len(game_vecctor) != 6 + (5 * 3):
        game_vecctor.append(0)
        # print("Error: Vector length mismatch")
    
    return game_vecctor


def partialize_vector(vector):
    vectors = []
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
    return vectors

def extract_all_data_from_game(game, circular=True, partial=True):
    player_oder = get_leader_order_one_cycle(game)
    if circular:
        orders = cyclic_perm(player_oder)
    else:
        orders = [player_oder]
    all_vectors_from_game = []
    for order in orders:
        # print(order)
        # try:
        game_vector = vectorize_game(game, order)

        all_vectors_from_game.append(game_vector)
        if partial:
            partials = partialize_vector(game_vector)
            all_vectors_from_game += partials
        # print(partials)
    return all_vectors_from_game


def vectorize_train_validation_test_sets(file_path=FILE, train_percentage=0.7):
    # train_percentage = 0.7
    with open(file_path, 'r') as file:
        data = json.load(file)
    six_player_games = sum(1 for game in data if game.get("numberOfPlayers") == 6)
    train_set = []
    validation_set = []
    test_set = []

    index = 0
    for game in tqdm(data):
        # print(game.get("roles"))
        if game.get("numberOfPlayers") == 6:
            if index < int(six_player_games * train_percentage):
                all_data = extract_all_data_from_game(game, circular=True, partial=True)
                train_set += all_data
            elif index < int(six_player_games * train_percentage) + int(six_player_games * (1 - train_percentage) / 2):
                all_data = extract_all_data_from_game(game, circular=False, partial=True)
                validation_set += all_data
            else:
                all_data = extract_all_data_from_game(game, circular=False, partial=True)
                test_set += all_data
            index += 1

    return train_set, validation_set, test_set
    
if __name__ == "__main__":
    with open(FILE, 'r') as file:
        data = json.load(file)
    six_player_games = sum(1 for game in data if game.get("numberOfPlayers") == 6)
    print(six_player_games)