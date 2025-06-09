import json
import glob
import pandas as pd
import os
from collections import defaultdict

def analyze_logs():
    # Find all log files
    log_files = glob.glob("evaluation/logs/*.json")
    print(log_files)
    # Dictionary to store game results
    # Format: {(good_agent_type, evil_agent_type): [good_wins, total_games]}
    results = defaultdict(lambda: [0, 0])
    
    # Set to track all agent types found in logs
    all_agent_types = set()
    
    # Process each log file
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
            
            # Extract logs
            logs = log_data.get('logs', [])
            
            # Find agent types and roles
            agents_info = {}  # {pid: {'type': agent_type, 'role': role}}
            good_agent_types = set()
            evil_agent_types = set()
            
            # Extract agent information
            for entry in logs:
                if isinstance(entry, dict) and 'type' in entry and 'role' in entry and 'pid' in entry:
                    pid = entry['pid']
                    agent_type = entry['type']
                    role = entry['role']
                    
                    agents_info[pid] = {
                        'type': agent_type,
                        'role': role
                    }
                    
                    all_agent_types.add(agent_type)
                    
                    # Categorize agent types by team
                    if role.startswith('Servant'):
                        good_agent_types.add(agent_type)
                    elif role.startswith('Minion'):
                        evil_agent_types.add(agent_type)
            
            # Determine if there was a clear winner
            good_won = False
            for entry in logs:
                if isinstance(entry, dict) and 'full' in entry and 'messages' in entry['full']:
                    messages = entry['full']['messages']
                    if not messages:
                        continue
                    
                    for msg in messages:
                        if not msg:
                            continue
                        
                        if msg.get('player') == 'system' and 'wins' in msg.get('msg', ''):
                            if 'Good wins' in msg['msg']:
                                good_won = True
                            elif 'Evil wins' in msg['msg']:
                                good_won = False
            
            # If we have both good and evil agent types and a clear outcome
            if good_agent_types and evil_agent_types:
                # If all agents of same team are the same type
                if len(good_agent_types) == 1 and len(evil_agent_types) == 1:
                    good_type = list(good_agent_types)[0]
                    evil_type = list(evil_agent_types)[0]
                    
                    # Update results
                    results[(good_type, evil_type)][1] += 1  # Increment total games
                    if good_won:
                        results[(good_type, evil_type)][0] += 1  # Increment good wins
        
        except Exception as e:
            print(f"Error processing {log_file}: {e}")
    
    # Create DataFrame
    df = pd.DataFrame(index=sorted(all_agent_types), columns=sorted(all_agent_types))
    
    # Fill DataFrame with win percentages
    for (good_type, evil_type), (wins, total) in results.items():
        if total > 0:
            win_percentage = (wins / total) * 100
            df.loc[good_type, evil_type] = f"{win_percentage:.1f}% ({wins}/{total})"
        else:
            df.loc[good_type, evil_type] = "N/A"
    
    # Replace NaN with empty string
    df = df.fillna("N/A")
    
    # Add row and column labels
    df.index.name = "Good Agent Types"
    df.columns.name = "Evil Agent Types"
    
    return df

if __name__ == "__main__":
    results_df = analyze_logs()
    print("\nGood Team Win Percentages:")
    print("(Rows: Agent type playing good roles, Columns: Agent type playing evil roles)\n")
    
    # Get the agent types (column names)
    agent_types = results_df.columns.tolist()
    # print(agent_types)
    
    # Calculate column widths for better alignment
    agent_type_width = 20  # Width for the first column
    value_width = 15       # Width for each value column
    
    # Create the header rows
    header1 = f"{'':<{agent_type_width}} | {'Evil Agent Types':<{value_width * len(agent_types) + (len(agent_types) - 1) * 3}}"
    header2 = f"{'Good Agent Types':<{agent_type_width}} | {' | '.join(f'{agent:<{value_width}}' for agent in agent_types)}"
    
    # Calculate the total width of the table
    total_width = len(header2)
    
    # Create a horizontal line that's guaranteed to be long enough
    horizontal_line = '-' * total_width
    
    # Print the headers
    print(horizontal_line)
    print(header1)
    print(header2)
    print(horizontal_line)
    
    # Print each row with vertical separators and proper alignment
    for idx, row in results_df.iterrows():
        row_values = [f"{val:<{value_width}}" for val in row.values]
        formatted_row = f"{idx:<{agent_type_width}} | {' | '.join(row_values)}"
        print(formatted_row)
        print(horizontal_line)
    
    # Save to CSV
    results_df.to_csv("evaluation/agent_win_rates.csv")
    print("\nResults saved to evaluation/agent_win_rates.csv")
