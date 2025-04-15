from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Starting positions and scores
game_state = {
    "turn": "Player1",
    "player1": {"position": (0, 0), "treasures": 0},
    "player2": {"position": (9, 9), "treasures": 0},
    "message": "Welcome to Treasure Hunt!"
}

@app.route('/')
def home():
    return render_template(
        'index.html',
        game_state=game_state,
        row_range=range(10),
        col_range=range(10)
    )

@app.route('/search', methods=['POST'])
def search():
    current_player = game_state["turn"]
    position = game_state[current_player]["position"]

    # Example: simple test logic
    if position == (1, 1):
        game_state["message"] = "You found a trap!"
    elif position == (2, 2):
        game_state[current_player]["treasures"] += 1
        game_state["message"] = "You found a treasure!"
    else:
        game_state["message"] = "Nothing here."

    return redirect(url_for('home'))

@app.route('/end_turn', methods=['POST'])
def end_turn():
    if game_state["turn"] == "Player1":
        game_state["turn"] = "Player2"
    else:
        game_state["turn"] = "Player1"

    game_state["message"] = f"{game_state['turn']}'s turn!"
    return redirect(url_for('home'))

@app.route('/move', methods=['POST'])
def move():
    data = request.get_json()
    x, y = data['x'], data['y']
    current_player = game_state["turn"]
    current_x, current_y = game_state[current_player]["position"]

    # Only allow 1-step movement (up/down/left/right)
    if abs(current_x - x) + abs(current_y - y) == 1:
        game_state[current_player]["position"] = (x, y)
        game_state["message"] = f"{current_player} moved to ({x}, {y})"
    else:
        game_state["message"] = "Invalid move. You can only move one tile."

    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
