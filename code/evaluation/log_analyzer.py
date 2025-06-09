import json
import sys
from typing import Dict, List, Any, Tuple

def load_game_log(log_path: str) -> Dict[str, Any]:
    """Load and parse the game log file."""
    with open(log_path, 'r') as f:
        return json.load(f)["logs"]

def get_last_game_message(messages: List) -> Dict[str, Any]:
    """Find the last message with msgtype 'game'."""
    for msg in reversed(messages):
        if msg['msgtype'] == 'game':
            return msg
    raise ValueError("No game message found in log")

def get_player_name(players: List[Dict[str, Any]], pid: int) -> str:
    """Get player name from their ID."""
    for player in players:
        if player['id'] == pid:
            return player['name']
    return f"Unknown Player {pid}"

def get_player_id(players: List[Dict[str, Any]], name: str) -> int:
    """Get player ID from their name."""
    for player in players:
        if player['name'] == name:
            return player['id']
    raise ValueError(f"Unknown player name: {name}")

def parse_party_from_message(msg: str, players: List[Dict[str, Any]]) -> List[int]:
    """Parse party members from a message like 'Luca proposed a party: Luca, Paul'."""
    # Extract the part after the colon
    party_str = msg.split(":")[1].strip()
    # Split by comma and strip whitespace
    party_names = [name.strip() for name in party_str.split(",")]
    # Convert names to player IDs
    return [get_player_id(players, name) for name in party_names]

def get_next_leader(current_leader: str, players: List[Dict[str, Any]]) -> str:
    """Get the next leader in the rotation."""
    player_names = [p['name'] for p in players]
    current_index = player_names.index(current_leader)
    next_index = (current_index + 1) % len(player_names)
    return player_names[next_index]

def validate_quest_flow(quest_messages: List[Dict[str, Any]], players: List[Dict[str, Any]]) -> List[str]:
    """Validate that the quest follows the expected flow pattern."""
    errors = []
    current_turn = None
    party_proposed = False
    discussion_started = False
    all_players_spoke = set()  # Track all players who spoke in the entire discussion phase
    vote_started = False
    current_leader = None
    expected_next_leader = None
    active_party = None
    
    # Get the initial leader from the first party proposal
    initial_proposal = next((m for m in quest_messages if 'proposed a party' in m.get('msg', '')), None)
    if initial_proposal:
        current_leader = initial_proposal['msg'].split(" proposed a party:")[0]
        party_proposed = True
        active_party = parse_party_from_message(initial_proposal['msg'], players)
    
    for msg in quest_messages:
        if msg['turn'] != current_turn:
            current_turn = msg['turn']
            # Only reset discussion flags for new turn
            discussion_started = False
            
        if msg['player'] != 'system':
            if not party_proposed:
                errors.append(f"Turn {current_turn}: Player spoke before party was proposed")
            elif not discussion_started:
                discussion_started = True
            all_players_spoke.add(msg['player'])
        else:
            if 'proposed a party' in msg['msg']:
                proposer = msg['msg'].split(" proposed a party:")[0]
                if expected_next_leader and proposer != expected_next_leader:
                    errors.append(f"Turn {current_turn}: {proposer} proposed party, but expected {expected_next_leader}")
                current_leader = proposer
                expected_next_leader = None
                party_proposed = True
                active_party = parse_party_from_message(msg['msg'], players)
            elif 'initiated a party vote' in msg['msg']:
                if not party_proposed:
                    errors.append(f"Turn {current_turn}: Vote started without party proposal")
                vote_started = True
            elif 'The party has been rejected' in msg['msg']:
                expected_next_leader = get_next_leader(current_leader, players)
                # Reset for new discussion round
                party_proposed = False
                discussion_started = False
                all_players_spoke = set()  # Reset only when party is rejected
                vote_started = False
    
    # Check if all players spoke in the final discussion round
    if vote_started and len(all_players_spoke) != len(players):
        errors.append(f"Turn {current_turn}: Not all players spoke in discussion. Expected {len(players)} players, but only {len(all_players_spoke)} spoke.")
    
    return errors

def analyze_game_log(log_path: str) -> None:
    """Analyze the game log and print a hierarchical summary of the game flow."""
    log_data = load_game_log(log_path)
    game_msg = get_last_game_message(log_data)
    game_data = game_msg['full']
    
    players = game_data['all_players']
    messages = game_data['messages']
    
    current_quest = None
    current_turn = None
    turn_actions = []
    quest_messages = []
    
    print(f"Game Summary for {log_path}")
    print("=" * 50)
    
    for msg in messages:
        # Skip system messages that aren't relevant to the flow
        if msg['player'] == 'system' and not any(x in msg['msg'] for x in [
            'proposed a party', 'initiated a party vote', 'Party vote summary',
            'The party has been', 'Voting for the quest', 'The quest has'
        ]):
            continue
            
        # Start new quest section
        if msg['quest'] != current_quest:
            if current_quest is not None:
                if turn_actions:
                    print_turn_actions(turn_actions)
                # Validate previous quest's flow
                errors = validate_quest_flow(quest_messages, players)
                if errors:
                    print("\nFlow Validation Errors for Quest", current_quest)
                    for error in errors:
                        print(f"  - {error}")
            current_quest = msg['quest']
            print(f"\nQuest {current_quest}:")
            current_turn = None
            turn_actions = []
            quest_messages = []
            
        # Start new turn section
        if msg['turn'] != current_turn:
            if current_turn is not None and turn_actions:
                print_turn_actions(turn_actions)
            current_turn = msg['turn']
            print(f"  Turn {current_turn}:")
            turn_actions = []
            
        # Add message to quest messages for validation
        quest_messages.append(msg)
            
        # Process different types of messages
        if msg['player'] != 'system':
            turn_actions.append(f"- {msg['player']} sent a message")
        else:
            if 'proposed a party' in msg['msg']:
                proposer_name = msg['msg'].split(" proposed a party:")[0]
                party_proposal = parse_party_from_message(msg['msg'], players)
                turn_actions.append(f"- {proposer_name} proposed party: {', '.join(get_player_name(players, pid) for pid in party_proposal)}")
            elif 'initiated a party vote' in msg['msg']:
                turn_actions.append(f"- {get_player_name(players, msg['pid'])} started party vote")
            elif 'Party vote summary' in msg['msg']:
                turn_actions.append(f"- {msg['msg']}")
            elif 'The party has been' in msg['msg']:
                turn_actions.append(f"- {msg['msg']}")
            elif 'Voting for the quest' in msg['msg']:
                turn_actions.append(f"- {msg['msg']}")
            elif 'The quest has' in msg['msg']:
                turn_actions.append(f"- {msg['msg']}")
    
    # Print any remaining turn actions
    if turn_actions:
        print_turn_actions(turn_actions)
    
    # Validate final quest's flow
    if quest_messages:
        errors = validate_quest_flow(quest_messages, players)
        if errors:
            print("\nFlow Validation Errors for Quest", current_quest)
            for error in errors:
                print(f"  - {error}")
    
    # Print final game result
    print("\nFinal Result:")
    print(f"- Winner: {game_data['winner']}")
    print("- Player Roles:")
    for player in players:
        print(f"  - {player['name']}: {player['role']}")

def print_turn_actions(actions: List[str]) -> None:
    """Print the actions that occurred in a turn."""
    for action in actions:
        print(f"    {action}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python log_analyzer.py <log_file_path>")
        sys.exit(1)
        
    log_path = sys.argv[1]
    analyze_game_log(log_path)
