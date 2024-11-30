import requests
from bs4 import BeautifulSoup
import requests
import json
import PySimpleGUI as sg
import traceback
import time
import numpy as np

last_match_id = None

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

    if last_match_id == match_data["matches"][0]['matchId']:
        return None
    else:
        last_match_id = match_data["matches"][0]['matchId']

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
                    "elo_tg": player_ratings["rm_team"],
                    "elo_1v1": player_ratings["rm_1v1"],
                    "country": player["country"],
                    "civ": player["civ"],
                    "rating": player['rating']
                }
                all_players.append(player_it)
            except:
                player_it = {
                    "team": -1,
                    "profile": -1,
                    "name": "IA",
                    "elo_tg": 0,
                    "elo_1v1": 0,
                    "country": " ",
                    "civ": " ",
                    "rating": 0
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
                player_it2["win"] = w
                player_it2["loose"] = l

    for player in players_by_team[teams[1]]:
        if None in [player["rating"]] + ratings_by_team[teams[1]]:
            w, l = "", ""
        else:
            w, l = puntaje_en_juego(player["rating"], np.array(ratings_by_team[teams[0]]).mean())

        for player_it2 in all_players:
            if player_it2["name"] == player["name"]:
                player_it2["win"] = w
                player_it2["loose"] = l




    leaderboardName = match_data["matches"][0]['leaderboardName']
    return all_players, leaderboardName, match_title


def create_overlay(id_profile):
    # Initial data fetch
    overlay_data = get_overlay_data(id_profile)
    players, _, match_title = overlay_data
    # Table headers
    headers = ["Name", "TG", "RM 1v1", "Country", "Civ", "Win", "Loose"]

    # Layout for the window
    layout = [
        [sg.Text(match_title, justification='center', font=("Arial", 16), size=(50, 1), text_color="white", background_color="#333333", key="-TITLE-")],
        [sg.Table(
            values=[[player["name"], player["elo_tg"],player["elo_1v1"], player["country"], player["civ"], player["win"], player["loose"]] for player in players],
            headings=headers,
            auto_size_columns=True,
            justification="center",
            num_rows=min(8, len(players)),  # Show up to 8 rows
            font=("Arial", 12),
            row_height=25,
            text_color="white",
            background_color="#333333",
            alternating_row_color="#444444",
            header_text_color="white",
            header_background_color="#222222",
            key="-TABLE-",
            expand_x=True
        )]
    ]
    menu = ["", ["Close"]]
    # Window configuration
    window = sg.Window(
        "Overlay",
        layout,
        no_titlebar=True,
        keep_on_top=True,
        transparent_color="#333333",  # Make the background transparent
        finalize=True,
        element_justification="center",
        grab_anywhere=True,
        background_color="#333333",
        right_click_menu=menu,
        location=sg.user_settings_get_entry('-location-', (None, None))
    )

    # Adjust transparency
    window.TKroot.attributes("-alpha", 0.8)  # Transparency level (0.0 to 1.0)

    # Event loop
    while True:
        event, values = window.read(timeout=100)  # Poll every 100 ms

        if event in (sg.WINDOW_CLOSED, "Exit", "Close"):  # Close on button or window close
            sg.user_settings_set_entry('-location-', window.current_location())
            break

        # Refresh overlay data every minute
        if int(time.time()) % 60 == 0:  # Check if the current second is 0
            overlay_data = get_overlay_data(id_profile)

            if overlay_data is None:
                continue

            players, _, match_title = overlay_data
            window["-TITLE-"].update(match_title)
            table_data = [[player["name"], player["elo_tg"], player["elo_1v1"], player["country"], player["civ"], player["win"], player["loose"]] for player in players]
            window["-TABLE-"].update(values=table_data)
            window["-TITLE-"].update(match_title)

    window.close()


if __name__ == "__main__":
    id_profile = ""
    with open('profile.txt', 'r') as archivo:
        for linea in archivo:
            id_profile = linea.strip()
    # print(id_profile)
    try:
        create_overlay(id_profile)
    except Exception as e:
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())

