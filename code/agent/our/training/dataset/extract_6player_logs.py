import json
import os

# This file moves the logs with 6 players to a new folder

def main():
    player_sizes = []
    file_names = []
    avalon_logs_folder = "avalonlogs/logs"
    json_file_paths = [os.path.join(avalon_logs_folder, file) for file in os.listdir(avalon_logs_folder)]
    print(len(json_file_paths))
    for file_name in json_file_paths:
        # print(file_name)
        with open(file_name, 'r') as file:
            data = json.load(file)
            player_size = len([player['name'] for player in data['players']])
            player_sizes.append(player_size)
            # plyer_names = [player['name'] for player in data['players']]
            if player_size == 6:
                file_names.append(file_name)
    
    
    new_folder = "6_player"
    os.makedirs(new_folder, exist_ok=True)

    for file_name in file_names:
        new_path = os.path.join(new_folder, os.path.basename(file_name))
        os.rename(file_name, new_path)
    
    six_player_files_count = len(os.listdir(new_folder))
    print(f"Number of files in {new_folder} folder: {six_player_files_count}")

    print("6 player games moved to the new folder" , player_sizes.count(6))


if __name__ == "__main__":
    main()