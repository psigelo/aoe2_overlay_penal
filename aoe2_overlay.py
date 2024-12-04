import requests
import json
import numpy as np
import tkinter as tk
from tkinter import ttk
import traceback
import random
import string

last_match_id = None
id_profile = ""
with open('profile.txt', 'r') as archivo:
    for linea in archivo:
        id_profile = linea.strip()

def puntaje_en_juego(p_1, p_2):
    diff_elo = p_1 - p_2
    elo_f = lambda x: 32 * (0.5 - (1 / (1 + 10 ** (-abs(x / 400)))))
    sing_elo_p1 = -1 if p_1 < p_2 else 1
    p1_wins = round(16 + sing_elo_p1 * elo_f(diff_elo))
    p1_loose = round(32 - p1_wins)

    return p1_wins, p1_loose


def get_player_ratings(id_profile):
    result = {}
    url_rating_1v1 = f"https://data.aoe2companion.com/api/profiles/{id_profile}"
    response_1v1 = requests.get(url_rating_1v1)
    data_1v1 = json.loads(response_1v1.content)

    for lb in data_1v1["leaderboards"]:
        if lb["leaderboardId"] == 'rm_1v1':
            result["rm_1v1"] = lb["rating"]
        if lb["leaderboardId"] == 'rm_team':
            result["rm_team"] = lb["rating"]

    if result.get("rm_1v1") is None:
        result["rm_1v1"] = ""
    if result.get("rm_team") is None:
        result["rm_team"] = ""

    return result


def get_overlay_data(id_profile):
    global last_match_id

    url_current_match = f"https://data.aoe2companion.com/api/matches?profile_ids={id_profile}"
    response = requests.get(url_current_match)
    match_data = json.loads(response.content)

    # try:
    #     if last_match_id == match_data["matches"][0]['matchId']:
    #         return None
    #     else:
    #         last_match_id = match_data["matches"][0]['matchId']
    # except:
    #     return None

    match_title = f"{match_data["matches"][0]['leaderboardName']} on {match_data["matches"][0]['mapName']}"

    all_players = []
    for teams in match_data["matches"][0]["teams"]:
        for player in teams["players"]:
            try:
                player_ratings = get_player_ratings(player["profileId"])
                player_it = {
                    "team": player["team"],
                    "profile": player["profileId"],
                    "name": player["name"],
                    "TG": player_ratings["rm_team"],
                    "RM 1v1": player_ratings["rm_1v1"],
                    "country": player["country"],
                    "civ": player["civ"],
                    "rating": player['rating'],
                    "Name": f"[{player["country"]}]{player["name"]}"
                }
                all_players.append(player_it)
            except:
                player_it = {
                    "team": -1,
                    "profile": -1,
                    "name": "IA",
                    "elo_tg": 0,
                    "RM 1v1": 0,
                    "country": " ",
                    "civ": " ",
                    "rating": 0,
                    "W/L": "",
                    "Name": ""
                }
                all_players.append(player_it)

    players_by_team = {}
    ratings_by_team = {}
    for player in all_players:
        if players_by_team.get(player["team"]) is None:
            players_by_team[player["team"]] = [player]
            ratings_by_team[player["team"]] = [player["rating"]]
        else:
            players_by_team[player["team"]].append(player)
            ratings_by_team[player["team"]].append(player["rating"])

    teams = list(players_by_team.keys())

    for player in players_by_team[teams[0]]:
        if None in [player["rating"]] + ratings_by_team[teams[1]]:
            w, l = "", ""
        else:
            w, l = puntaje_en_juego(player["rating"], np.array(ratings_by_team[teams[1]]).mean())

        for player_it2 in all_players:
            if player_it2["name"] == player["name"]:
                player_it2["W/L"] = f"{w}/{l}"

    for player in players_by_team[teams[1]]:
        if None in [player["rating"]] + ratings_by_team[teams[1]]:
            w, l = "", ""
        else:
            w, l = puntaje_en_juego(player["rating"], np.array(ratings_by_team[teams[0]]).mean())

        for player_it2 in all_players:
            if player_it2["name"] == player["name"]:
                player_it2["W/L"] = f"{w}/{l}"
                # player_it2["loose"] = l

    leaderboard_name = match_data["matches"][0]['leaderboardName']
    return all_players, leaderboard_name, match_title

# Create the overlay
def create_overlay(player_data, title, id_profile):
    # Create the main window
    root = tk.Tk()
    root.title("Player Overlay")

    # Configure the window as an overlay
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.85)

    # Visual style
    bg_color = "#2b2b2b"
    text_color = "#ffffff"
    root.configure(bg=bg_color)

    # Create the top bar for controls
    top_frame = tk.Frame(root, bg=bg_color, height=30)
    top_frame.pack(fill=tk.X)

    # Create the main content frame
    content_frame = tk.Frame(root, bg=bg_color)
    content_frame.pack(fill=tk.BOTH, expand=True)

    # Column headers
    headers = ["Name", "TG", "RM 1v1", "W/L"]
    row_labels = []

    # Title variable
    title_var = tk.StringVar(value=title)

    # Function to update the overlay with new data
    def update_overlay():
        nonlocal id_profile
        nonlocal row_labels
        for row in row_labels:
            for label in row:
                label.destroy()
        row_labels.clear()

        headers = ["Name", "TG", "RM 1v1", "W/L"]
        header_labels = []
        for col, header in enumerate(headers):
            label = ttk.Label(
                content_frame,
                text=header,
                font=("Arial", 12, "bold"),
                background=bg_color,
                foreground=text_color,
            )
            label.grid(row=1, column=col, padx=10, pady=10)
            header_labels.append(label)

        overlay_data = get_overlay_data(id_profile)
        if overlay_data is not None:
            players, _, match_title = overlay_data

            for row, player in enumerate(players, start=2):
                row_data = []
                for col, header in enumerate(headers):
                    value = player.get(header, "")
                    label = ttk.Label(
                        content_frame,
                        text=str(value),
                        font=("Arial", 10),
                        background=bg_color,
                        foreground=text_color,
                    )
                    label.grid(row=row, column=col, padx=10, pady=5)
                    row_data.append(label)
                row_labels.append(row_data)

            # Update the title
            title_var.set(match_title)

        root.after(60000, update_overlay)  # Refresh every 10 seconds

    # Call `update_overlay` to initialize the table
    update_overlay()

    # Minimize functionality
    is_minimized = tk.BooleanVar(value=False)
    original_geometry = None

    def minimize():
        nonlocal original_geometry
        if not is_minimized.get():
            original_geometry = root.geometry()
            content_frame.pack_forget()
            root.geometry("50x30")
            minimize_button.configure(text="+", command=restore)
            is_minimized.set(True)

    def restore():
        if is_minimized.get():
            content_frame.pack(fill=tk.BOTH, expand=True)
            if original_geometry:
                root.geometry(original_geometry)
            minimize_button.configure(text="_", command=minimize)
            is_minimized.set(False)

    # Minimize button
    minimize_button = tk.Button(
        top_frame,
        text="_",
        command=minimize,
        font=("Arial", 10, "bold"),
        bg=bg_color,
        fg=text_color,
        relief=tk.FLAT,
    )
    minimize_button.pack(side=tk.LEFT, padx=5, pady=2)

    # Title
    title_label = tk.Label(
        top_frame,
        textvariable=title_var,
        font=("Arial", 12, "bold"),
        bg=bg_color,
        fg=text_color,
    )
    title_label.pack(side=tk.LEFT, padx=10, pady=2)

    # Close button
    close_button = tk.Button(
        top_frame,
        text="X",
        command=root.destroy,
        font=("Arial", 10, "bold"),
        bg=bg_color,
        fg=text_color,
        relief=tk.FLAT,
    )
    close_button.pack(side=tk.RIGHT, padx=5, pady=2)

    # Drag functionality
    offset_x = 0
    offset_y = 0

    def start_drag(event):
        nonlocal offset_x, offset_y
        offset_x = event.x_root - root.winfo_x()
        offset_y = event.y_root - root.winfo_y()

    def do_drag(event):
        x = event.x_root - offset_x
        y = event.y_root - offset_y
        root.geometry(f"+{x}+{y}")

    root.bind("<Button-1>", start_drag)
    root.bind("<B1-Motion>", do_drag)

    # Context menu
    def show_context_menu(event):
        context_menu = tk.Menu(root, tearoff=0)
        context_menu.add_command(label="Close", command=root.destroy)
        context_menu.post(event.x_root, event.y_root)

    root.bind("<Button-3>", show_context_menu)
    root.mainloop()


if __name__ == "__main__":
    try:
        # Start the overlay
        # player_data, _, title = get_overlay_data(id_profile)
        create_overlay(None, "LOADING", id_profile)
    except Exception as e:
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())
