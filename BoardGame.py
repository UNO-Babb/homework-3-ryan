from flask import Flask, render_template, request, redirect, url_for, jsonify
import random, json, os

app = Flask(__name__)

# ───────────────────────────────────────────────────────── helpers ──────────
def save_event(msg: str) -> None:
    with open("events.txt", "a") as f:
        f.write(msg + "\n")

def dump_state() -> None:
    """Write game_state and item_map to game_state.json (tuple keys → str)."""
    gs = dict(game_state)
    gs["revealed"] = {str(k): v for k, v in game_state["revealed"].items()}
    im = {str(k): v for k, v in item_map.items()}
    with open("game_state.json", "w") as f:
        json.dump({"game_state": gs, "item_map": im}, f)

def load_state() -> bool:
    if not os.path.exists("game_state.json"):
        return False
    with open("game_state.json") as f:
        payload = json.load(f)

    loaded = payload["game_state"]
    for p in ("player1", "player2"):
        loaded[p]["position"] = tuple(loaded[p]["position"])
    loaded["revealed"] = {
        tuple(map(int, k.strip("()").split(","))): v
        for k, v in loaded["revealed"].items()
    }
    game_state.clear()
    game_state.update(loaded)

    item_map.clear()
    for k, v in payload["item_map"].items():
        x, y = k.strip("()").split(",")
        item_map[(int(x), int(y))] = v
    return True
# ────────────────────────────────────────────────────────────────────────────

# default fresh state
game_state = {
    "turn": "Player1",
    "player1": {"position": (0, 0), "treasures": 0},
    "player2": {"position": (9, 9), "treasures": 0},
    "message": "Welcome to Treasure Hunt!",
    "has_moved": False,
    "revealed": {},
    "winner": None,
    "skip_turns": {"player1": False, "player2": False},
}
item_map = {}

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
    grass = [(r, c) for r in range(10) for c in range(10) if tile_map[r][c] == '.']
    picks = random.sample(grass, 6 + 6 + 3)
    item_map = {p: 'Treasure' for p in picks[:6]}
    item_map.update({p: 'Trap' for p in picks[6:12]})
    item_map.update({p: 'Monster' for p in picks[12:]})

# ───────────────────────────────────────────────────────── routes ───────────
@app.route('/')
def home():
    return render_template("index.html", game_state=game_state,
                           tile_map=tile_map, row_range=range(10), col_range=range(10))

@app.route('/start')
def start():
    restart_state()
    save_event("Game started!")
    dump_state()
    return redirect(url_for('home'))

@app.route('/restart')
def restart():
    restart_state()
    save_event("Game restarted!")
    dump_state()
    return redirect(url_for('home'))

@app.route('/load')
def load():
    if load_state():
        game_state["message"] = "Saved game loaded!"
    else:
        game_state["message"] = "No saved game found."
    return redirect(url_for('home'))

# ───────────────────────────── game actions ────────────────────────────────
@app.route('/move', methods=['POST'])
def move():
    if game_state.get("winner"):
        return jsonify(success=False)
    x, y = request.get_json().values()
    pk = game_state["turn"].lower()
    if game_state["has_moved"]:
        return jsonify(success=False)
    cx, cy = game_state[pk]["position"]
    if abs(cx - x) + abs(cy - y) != 1 or tile_map[x][y] in ('~', '^'):
        return jsonify(success=False)
    game_state[pk]["position"] = (x, y)
    game_state["has_moved"] = True
    game_state["message"] = f"{game_state['turn']} moved to {(x, y)}"
    save_event(game_state["message"])
    dump_state()
    return jsonify(success=True)

@app.route('/search', methods=['POST'])
def search():
    if game_state.get("winner"):
        return redirect(url_for('home'))
    cur = game_state["turn"]; pk = cur.lower(); pos = game_state[pk]["position"]
    if pos in game_state["revealed"]:
        return redirect(url_for('home'))
    game_state["revealed"][pos] = True
    item = item_map.get(pos)
    if item == 'Treasure':
        game_state[pk]["treasures"] += 1
        msg = f"{cur} found Treasure at {pos}"
        if game_state[pk]["treasures"] >= 3:
            game_state["winner"] = cur
            msg = f"🎉 {cur} wins with 3 treasures!"
    elif item == 'Trap':
        game_state["skip_turns"][pk] = True            # flag self
        msg = f"{cur} triggered Trap and will lose next turn!"
    elif item == 'Monster':
        game_state[pk]["position"] = (0, 0) if cur == "Player1" else (9, 9)
        msg = f"{cur} encountered Monster at {pos}"
    else:
        msg = f"{cur} found nothing at {pos}"
    game_state["message"] = msg
    save_event(msg)
    dump_state()
    return redirect(url_for('home'))

@app.route('/end_turn', methods=['POST'])
def end_turn():
    if game_state.get("winner"):
        return redirect(url_for('home'))

    # advance to next player
    game_state["turn"] = "Player2" if game_state["turn"] == "Player1" else "Player1"
    game_state["has_moved"] = False
    pk = game_state["turn"].lower()

    # check skip flag for the player whose turn is about to start
    if game_state["skip_turns"][pk]:
        game_state["skip_turns"][pk] = False
        save_event(f"{game_state['turn']}'s turn skipped (trap).")
        game_state["message"] = f"{game_state['turn']}'s turn was skipped due to a trap!"
        # give turn to the other player
        game_state["turn"] = "Player2" if game_state["turn"] == "Player1" else "Player1"
        pk = game_state["turn"].lower()

    game_state["message"] = f"{game_state['turn']}'s turn."
    dump_state()
    return redirect(url_for('home'))
# ────────────────────────────────────────────────────────────────────────────
def restart_state():
    game_state.update({
        "turn": "Player1",
        "player1": {"position": (0, 0), "treasures": 0},
        "player2": {"position": (9, 9), "treasures": 0},
        "message": "Game reset – Player1 starts.",
        "has_moved": False,
        "revealed": {},
        "winner": None,
        "skip_turns": {"player1": False, "player2": False}
    })
    generate_items()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
