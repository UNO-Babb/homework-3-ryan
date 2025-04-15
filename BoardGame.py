from flask import Flask, render_template, request, redirect, url_for, jsonify
import random

app = Flask(__name__)

# Game state
game_state = {
    "turn": "Player1",
    "player1": {"position": (0, 0), "treasures": 0},
    "player2": {"position": (9, 9), "treasures": 0},
    "message": "Welcome to Treasure Hunt!",
    "has_moved": False,
    "revealed": {},
    "winner": None,
    "skip_turns": {"player1": False, "player2": False}
}

# Item map populated at game start
item_map = {}

# 10x10 terrain map
tile_map = [
    ['.', '.', '.', '.', '.', '.', '~', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '=', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '~', '~', '.', '.', '.'],
    ['.', '^', '^', '.', '~', '~', '.', '.', '.', '.'],
    ['.', '^', '^', '.', '~', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '=', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '~', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '~', '~', '.', '.', '^', '^', '.'],
    ['.', '.', '.', '=', '.', '.', '.', '^', '^', '.'],
    ['.', '.', '.', '~', '.', '.', '.', '.', '.', '.'],
]

def generate_items():
    global item_map
    item_map = {}
    grass_tiles = [(r, c) for r in range(10) for c in range(10) if tile_map[r][c] == '.']
    item_positions = random.sample(grass_tiles, 6 + 6 + 3)
    treasures = item_positions[:6]
    traps = item_positions[6:12]
    monsters = item_positions[12:]

    for pos in treasures:
        item_map[pos] = 'Treasure'
    for pos in traps:
        item_map[pos] = 'Trap'
    for pos in monsters:
        item_map[pos] = 'Monster'

# Save events to events.txt
def save_event(event):
    with open('events.txt', 'a') as file:
        file.write(f"{event}\n")

@app.route('/')
def home():
    return render_template(
        'index.html',
        game_state=game_state,
        tile_map=tile_map,
        row_range=range(10),
        col_range=range(10)
    )

@app.route('/start')
def start():
    game_state["turn"] = "Player1"
    game_state["player1"] = {"position": (0, 0), "treasures": 0}
    game_state["player2"] = {"position": (9, 9), "treasures": 0}
    game_state["message"] = "Game has started! Player1 goes first."
    game_state["has_moved"] = False
    game_state["revealed"] = {}
    game_state["winner"] = None
    game_state["skip_turns"] = {"player1": False, "player2": False}
    generate_items()

    # Log game start
    save_event("Game started!")

    return redirect(url_for('home'))

@app.route('/search', methods=['POST'])
def search():
    if game_state.get("winner"):
        game_state["message"] = f"{game_state['winner']} already won the game!"
        return redirect(url_for('home'))

    current_player = game_state["turn"]
    player_key = current_player.lower()
    position = game_state[player_key]["position"]

    if position in game_state["revealed"]:
        game_state["message"] = f"{current_player} already searched this tile."
        return redirect(url_for('home'))

    game_state["revealed"][position] = True
    item = item_map.get(position)

    if item == 'Treasure':
        game_state[player_key]["treasures"] += 1
        event = f"{current_player} found a Treasure at {position}."
        save_event(event)
        if game_state[player_key]["treasures"] >= 3:
            game_state["winner"] = current_player
            game_state["message"] = f"🎉 {current_player} wins the game with 3 treasures!"
        else:
            game_state["message"] = f"{current_player} found a Treasure!"
    elif item == 'Trap':
        game_state["skip_turns"][player_key] = True
        event = f"{current_player} triggered a Trap at {position}."
        save_event(event)
        game_state["message"] = f"{current_player} triggered a Trap! They'll lose their next turn!"
    elif item == 'Monster':
        game_state[player_key]["position"] = (0, 0) if current_player == "Player1" else (9, 9)
        event = f"{current_player} encountered a Monster at {position}."
        save_event(event)
        game_state["message"] = f"{current_player} encountered a Monster and fled to start!"
    else:
        event = f"{current_player} found nothing at {position}."
        save_event(event)
        game_state["message"] = f"{current_player} found nothing."

    return redirect(url_for('home'))

@app.route('/end_turn', methods=['POST'])
def end_turn():
    if game_state.get("winner"):
        game_state["message"] = f"{game_state['winner']} already won the game!"
        return redirect(url_for('home'))

    next_turn = "Player2" if game_state["turn"] == "Player1" else "Player1"
    next_key = next_turn.lower()

    if game_state["skip_turns"][next_key]:
        game_state["skip_turns"][next_key] = False
        game_state["message"] = f"{next_turn}'s turn was skipped due to a trap!"
        print(f"[DEBUG] Skipped {next_turn}'s turn due to trap.")  # dev output
        game_state["turn"] = "Player1" if next_turn == "Player2" else "Player2"
        game_state["has_moved"] = False
        return redirect(url_for('home'))  # Skip their turn and go to the next player

    game_state["turn"] = next_turn
    game_state["has_moved"] = False
    game_state["message"] = f"{game_state['turn']}'s turn!"
    return redirect(url_for('home'))

@app.route('/move', methods=['POST'])
def move():
    if game_state.get("winner"):
        game_state["message"] = f"{game_state['winner']} already won the game!"
        return jsonify(success=False)

    data = request.get_json()
    x, y = data['x'], data['y']
    current_player = game_state.get("turn")
    player_key = current_player.lower()

    if player_key not in game_state:
        game_state["message"] = "Game not started. Please click Start Game."
        return jsonify(success=False)

    if game_state.get("has_moved"):
        game_state["message"] = f"{current_player} has already moved this turn!"
        return jsonify(success=False)

    current_x, current_y = game_state[player_key]["position"]

    if abs(current_x - x) + abs(current_y - y) != 1:
        game_state["message"] = "Invalid move. You can only move one tile."
        return jsonify(success=False)

    terrain = tile_map[x][y]
    if terrain in ['~', '^']:
        game_state["message"] = f"{current_player} cannot move to that terrain!"
        return jsonify(success=False)

    game_state[player_key]["position"] = (x, y)
    game_state["has_moved"] = True
    game_state["message"] = f"{current_player} moved to ({x}, {y})"
    return jsonify(success=True)

@app.route('/restart')
def restart():
    # Reset the game state
    game_state["turn"] = "Player1"
    game_state["player1"] = {"position": (0, 0), "treasures": 0}
    game_state["player2"] = {"position": (9, 9), "treasures": 0}
    game_state["message"] = "Game has been restarted! Player1 goes first."
    game_state["has_moved"] = False
    game_state["revealed"] = {}
    game_state["winner"] = None
    game_state["skip_turns"] = {"player1": False, "player2": False}
    
    generate_items()  # Reset the item map (treasures, traps, monsters)
    
    # Log game restart
    save_event("Game restarted!")

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
