import os
import json
import sys


def get_player_roles(logs):
    player_roles = {"good": [], "evil": []}

    for entry in logs:
        if "name" in entry and "player" in entry:
        # if "timestamp" not in entry and "name" in entry and "player" in entry:

            if "Servant" in entry["role"]:
                player_roles["good"].append(entry["name"])
                player_roles[entry["name"]] = False
            else:
                player_roles["evil"].append(entry["name"])
                player_roles[entry["name"]] = True

        # changes = entry.get("changes", {})

        # if changes.get("all_joined", False) == True:
        #     for player in changes.get("all_players", []):
        #         if player is None:
        #             continue
                
        #         if "Servant" in player["role"]:
        #             player_roles["good"].append(player["name"])
        #             player_roles[player["name"]] = False
        #         else:
        #             player_roles["evil"].append(player["name"])
        #             player_roles[player["name"]] = True

    return player_roles


def get_llm_vibe_stats(player_roles, agent_dir, game_log_filename):
    key_string = "###  LLM vibes: "

    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0

    for filename in os.listdir(agent_dir):
        for name in player_roles["good"]:
            if filename == "LOG_(" + name + ")_" + game_log_filename[:-5] + ".log":
                filepath = os.path.join(agent_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    line = file.readline()
                    while line:
                        idx = line.find(key_string)
                        if idx != -1:
                            vibes = line[idx + len(key_string) + 1 : -2]
                            for player_vibe_pair in vibes.split(", "):
                                player, vibe = player_vibe_pair.split(": ")
                                player = player[1:-1].capitalize()
                                vibe = vibe[1:-1]

                                if vibe == "increase":
                                    if player in player_roles["evil"]:
                                        true_positive += 1
                                    else:
                                        false_positive += 1
                                elif vibe == "decrease":
                                    if player in player_roles["good"]:
                                        true_negative += 1
                                    else:
                                        false_negative += 1
                        
                        line = file.readline()

    return true_positive, false_positive, true_negative, false_negative



def get_successful_quests_with_evil(player_roles, logs):
    quests_succeeded_with_evil = 0
    # quests_succeeded_with_two_evil = 0

    for i in range(1, len(logs)):
        entry = logs[i]
        changes = entry.get("full", {})

        last_message = changes.get("messages", [])[-1] if changes.get("messages", []) else None
        if last_message:
            # print(last_message["msg"])
            if last_message["msg"] == "Voting for the quest has started...":
                # Check two things: what was the party
                # look at the next entry in log to see if the qyest was successful
                proposed_party = changes.get("proposed_party", [])
                evil_players_in_party = 0
                all_players = changes.get("all_players", [])
                player_id_to_role = {player["id"]: player["role"] for player in all_players}

                for player_id in proposed_party:
                    role = player_id_to_role.get(player_id, "")
                    if "Minion" in role:
                        evil_players_in_party += 1
                if evil_players_in_party > 0:
                    next_message = logs[i + 2].get("full", {}).get("messages", [])[-1] if logs[i + 2].get("full", {}).get("messages", []) else None
                    # print(logs[i+2].get("full", {}))
                    
                    if next_message:
                        # print(next_message["msg"])
                        if next_message["msg"] == "The quest has succeeded!":
                            quests_succeeded_with_evil += evil_players_in_party
                            # quests_succeeded_with_two_evil = 0
                        # print(changes)
                        # elif next_message["msg"].startswith("These were the game's"):
                        #     print(logs[i + 1].get("full", {}).get("messages", []))
                        #     exit()

    return quests_succeeded_with_evil


def get_graph_stats(player_roles, agent_dir, game_log_filename):
    key_string = "***  BELIEFS: "

    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0

    for filename in os.listdir(agent_dir):
        for name in player_roles["good"]:
            if filename == "LOG_(" + name + ")_" + game_log_filename[:-5] + ".log":
                filepath = os.path.join(agent_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    line = file.readline()
                    while line:
                        idx = line.find(key_string)
                        if idx != -1:
                            vibes = line[idx + len(key_string): ]
                            vibes = vibes.replace("'", '"')
                            vibes = json.loads(vibes)

                            for player in vibes:
                                vibe = vibes[player]
                                player = player.capitalize()

                                if vibe["evil"] > 0.5:
                                    if player in player_roles["evil"]:
                                        true_positive += 1
                                    else:
                                        false_positive += 1
                                elif vibe["evil"] < 0.5:
                                    if player in player_roles["good"]:
                                        true_negative += 1
                                    else:
                                        false_negative += 1
                        
                        line = file.readline()

    return true_positive, false_positive, true_negative, false_negative



def get_graph_with_vibes_stats(player_roles, agent_dir, game_log_filename):
    key_string = "***  BELIEFS with Vibes: "

    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0

    for filename in os.listdir(agent_dir):
        for name in player_roles["good"]:
            if filename == "LOG_(" + name + ")_" + game_log_filename[:-5] + ".log":
                filepath = os.path.join(agent_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    line = file.readline()
                    while line:
                        idx = line.find(key_string)
                        if idx != -1:
                            vibes = line[idx + len(key_string): ]
                            vibes = vibes.replace("'", '"')
                            vibes = json.loads(vibes)

                            for player in vibes:
                                vibe = vibes[player]
                                player = player.capitalize()

                                if vibe["evil"] > 0.5:
                                    if player in player_roles["evil"]:
                                        true_positive += 1
                                    else:
                                        false_positive += 1
                                elif vibe["evil"] < 0.5:
                                    if player in player_roles["good"]:
                                        true_negative += 1
                                    else:
                                        false_negative += 1
                        
                        line = file.readline()

    return true_positive, false_positive, true_negative, false_negative

def get_winner_and_duration(logs):
    good_win = 0
    bad_win = 0
    good_duration = []
    bad_duration = []

    last_entry = logs[-1]
    # changes = last_entry
    # print(last_entry)
    # changes = last_entry.get("changes", {})
    changes = last_entry.get("full", {})

    # winner = changes.get("winner", None)
    winner = changes.get("winner", None)

    
    # Extract "quest" value
    quest_durations = [msg.get("quest") for msg in changes.get("messages", []) if isinstance(msg, dict) and "quest" in msg]
    last_quest = quest_durations[-1] if quest_durations else None
    
    if winner == "good":
        good_win += 1
        if last_quest is not None:
            good_duration.append(last_quest)
    elif winner == "evil":
        bad_win += 1
        if last_quest is not None:
            bad_duration.append(last_quest)

    return good_win, bad_win, good_duration, bad_duration


def get_player_one_alignment(logs):
    last_entry = logs[-1]
    changes = last_entry.get("full", {})
    all_players = changes.get("all_players", [])
    
    for player in all_players:
        if player["id"] == 1:
            if "Minion" in player["role"]:
                return "evil"
            else:
                return "good"
    
    return None


def get_party_vote_stats(logs, player_roles):
    party_votes_by_quest = {}


    logs = [logs[-1]]
    for entry in logs:
        # changes = entry.get("changes", {})
        changes = entry.get("full", {})

        # final_messages = changes.get("messages", [])
        # # print(final_messages)
        # if len(final_messages) > 0:
        #     final_messages = [final_messages[-1]]
        # print(final_messages)
        
        # for msg in final_messages:
        for msg in changes.get("messages", []):
            if isinstance(msg, dict):
                if msg.get("msg", "")[:20] == "Party vote summary: ":
                    # print(msg)
                    # Party vote occurred
                    quest_number = msg.get("quest", None)

                    if quest_number not in party_votes_by_quest:
                        party_votes_by_quest[quest_number] = {}
                        party_votes_by_quest[quest_number]["total_votes"] = 0
                        party_votes_by_quest[quest_number]["no_votes_evil"] = 0
                        party_votes_by_quest[quest_number]["no_votes_good"] = 0

                    party_votes_by_quest[quest_number]["total_votes"] += 1

                    votes = msg.get("msg", "")[20:]


                    for name_vote_pair in votes.split(", "):
                        name, vote = name_vote_pair.split(": ")
                        # print(player_roles, vote)
                        if name in player_roles:
                            if player_roles[name] and vote == "no":
                                party_votes_by_quest[quest_number]["no_votes_evil"] += 1
                            elif not player_roles[name] and vote == "no":
                                party_votes_by_quest[quest_number]["no_votes_good"] += 1
                    # exit()

    avg_party_votes = 0.0
    num_final_party_votes = 0
    avg_no_party_votes_evil = 0.0
    avg_no_party_votes_good = 0.0

    num_quests = 0
    for quest in party_votes_by_quest.values():
        num_quests += 1
        # print(quest["total_votes"])
        # exit()
        avg_party_votes += quest["total_votes"]
        avg_no_party_votes_evil += quest["no_votes_evil"]
        avg_no_party_votes_good += quest["no_votes_good"]

        if quest["total_votes"] == 5:
            num_final_party_votes += 1
    if num_quests == 0:
        num_quests = 1
    return avg_party_votes / num_quests, avg_no_party_votes_evil / num_quests, avg_no_party_votes_good / num_quests, num_final_party_votes

def parse_logs(directory, agent_dir):
    good_wins = 0
    bad_wins = 0
    good_durations = []
    bad_durations = []

    avg_votes = []
    avg_no_votes_evil = []
    avg_no_votes_good = []
    num_final_party_votes = []
    
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0

    graph_true_positives = 0
    graph_false_positives = 0
    graph_true_negatives = 0
    graph_false_negatives = 0

    graph_and_llm_true_positives = 0
    graph_and_llm_false_positives = 0
    graph_and_llm_true_negatives = 0
    graph_and_llm_false_negatives = 0

    evil_votes_to_succeed = 0

    good_win_with_first_player_evil = 0
    evil_win_with_first_player_evil = 0

    good_win_with_first_player_good = 0
    evil_win_with_first_player_good = 0

    
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            # print("Parsing game log: ", filename)
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                    logs = data.get("logs", [])
                    
                    if logs:
                        player_roles = get_player_roles(logs)
                        # print(player_roles)

                        evil_votes_to_succeed += get_successful_quests_with_evil(player_roles, logs)


                        temp_avg_votes, temp_avg_no_votes_evil, temp_avg_no_votes_good, temp_num_final_party_votes = get_party_vote_stats(logs, player_roles)
                        avg_votes.append(temp_avg_votes)
                        avg_no_votes_evil.append(temp_avg_no_votes_evil)
                        avg_no_votes_good.append(temp_avg_no_votes_good)
                        num_final_party_votes.append(temp_num_final_party_votes)

                        graph_true_positive, graph_false_positive, graph_true_negative, graph_false_negative = get_graph_stats(player_roles, agent_dir, filename)
                        true_positive, false_positive, true_negative, false_negative = get_llm_vibe_stats(player_roles, agent_dir, filename)
                        graph_and_llm_true_positive, graph_and_llm_false_positive, graph_and_llm_true_negative, graph_and_llm_false_negative = get_graph_with_vibes_stats(player_roles, agent_dir, filename)
                        true_positives += true_positive
                        false_positives += false_positive
                        true_negatives += true_negative
                        false_negatives += false_negative
                        graph_true_positives += graph_true_positive
                        graph_false_positives += graph_false_positive
                        graph_true_negatives += graph_true_negative
                        graph_false_negatives += graph_false_negative
                        graph_and_llm_true_positives += graph_and_llm_true_positive
                        graph_and_llm_false_positives += graph_and_llm_false_positive
                        graph_and_llm_true_negatives += graph_and_llm_true_negative
                        graph_and_llm_false_negatives += graph_and_llm_false_negative

                        good_win, bad_win, good_dur, bad_dur = get_winner_and_duration(logs)
                        good_wins += good_win
                        bad_wins += bad_win
                        good_durations.extend(good_dur)
                        bad_durations.extend(bad_dur)
                        was_first_Evil = get_player_one_alignment(logs)
                        # print(filename, was_first_Evil)
                        if was_first_Evil == "evil":
                            if good_win:
                                good_win_with_first_player_evil += 1
                            else:
                                evil_win_with_first_player_evil += 1
                        else:
                            if good_win:
                                good_win_with_first_player_good += 1
                            else:
                                evil_win_with_first_player_good += 1


                except json.JSONDecodeError:
                    print(f"Error decoding JSON in file: {filename}")
    
    print(f"Good won: {good_wins} times")
    print(f"Bad won: {bad_wins} times")

    print(f"Good won with first player evil: {good_win_with_first_player_evil} times")
    print(f"Good won with first player good: {good_win_with_first_player_good} times")
    print(f"Bad won with first player evil: {evil_win_with_first_player_evil} times")
    print(f"Bad won with first player good: {evil_win_with_first_player_good} times")

    print(f"All game durations: {good_durations + bad_durations}")
    print(f"Average duration when good won: {sum(good_durations) / len(good_durations) if good_durations else 0}")
    print(f"Average duration when bad won: {sum(bad_durations) / len(bad_durations) if bad_durations else 0}")
    print(f"Average number of party votes per quest: {sum(avg_votes) / len(avg_votes) if avg_votes else 0}")
    print(f"Average number of final party votes per game: {sum(num_final_party_votes) / len(num_final_party_votes) if num_final_party_votes else 0}")
    print(f"Average number of 'no' party votes by evil players per quest: {sum(avg_no_votes_evil) / len(avg_no_votes_evil) if avg_no_votes_evil else 0}")
    print(f"Average number of 'no' party votes by good players per quest: {sum(avg_no_votes_good) / len(avg_no_votes_good) if avg_no_votes_good else 0}")

    print(f"Total number of times an evil player has voted to succeed a quest: {evil_votes_to_succeed}")

    print(f"LLM vibe true positives: {true_positives}")
    print(f"LLM vibe false positives: {false_positives}")
    print(f"LLM vibe true negatives: {true_negatives}")
    print(f"LLM vibe false negatives: {false_negatives}")

    print(f"Graph true positives: {graph_true_positives}")
    print(f"Graph false positives: {graph_false_positives}")
    print(f"Graph true negatives: {graph_true_negatives}")
    print(f"Graph false negatives: {graph_false_negatives}")

    print(f"Graph and LLM true positives: {graph_and_llm_true_positives}")
    print(f"Graph and LLM false positives: {graph_and_llm_false_positives}")
    print(f"Graph and LLM true negatives: {graph_and_llm_true_negatives}")
    print(f"Graph and LLM false negatives: {graph_and_llm_false_negatives}")

    if true_positives == 0:
        print(f"LLM vibe f1 score: {0}")
    else:
        f1_score = 2 * true_positives / (2 * true_positives + false_positives + false_negatives)
        print(f"LLM vibe f1 score: {f1_score}")

    graph_f1_score = 2 * graph_true_positives / (2 * graph_true_positives + graph_false_positives + graph_false_negatives)
    print(f"Graph f1 score: {graph_f1_score}")

    graph_and_llm_f1_score = 2 * graph_and_llm_true_positives / (2 * graph_and_llm_true_positives + graph_and_llm_false_positives + graph_and_llm_false_negatives)
    print(f"Graph + LLM f1 score: {graph_and_llm_f1_score}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <server_log_path> <agent_log_path")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    agent_path = sys.argv[2]
    parse_logs(directory_path, agent_path)