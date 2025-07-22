import dash_bootstrap_components as dbc
from dash import dcc, html
import constants
import re
from utils import get_map_image_url, get_hero_image_url
import pandas as pd

def generate_history_layout_simple(games_df):
    if games_df.empty:
        return [dbc.Alert("No match history available.", color="info")]

    history_items = []
    last_season = None

    for idx, game in games_df.iterrows():
        if pd.isna(game.get("Map")):
            continue

        current_season = game.get("Season")
        if pd.notna(current_season) and current_season != last_season:
            match = re.search(r"\d+", str(current_season))
            season_text = f"Season {match.group(0)}" if match else str(current_season)
            history_items.append(
                dbc.Alert(
                    season_text, color="secondary", className="my-4 text-center fw-bold"
                )
            )
            last_season = current_season

        map_name = game.get("Map", "Unknown Map")
        gamemode = game.get("Gamemode", "")
        att_def = game.get("Attack Def")
        map_image_url = get_map_image_url(map_name)
        date_str = (
            game["Date"].strftime("%d.%m.%Y")
            if pd.notna(game.get("Date"))
            else "Invalid Date"
        )
        result_color, result_text = (
            ("success", "VICTORY")
            if game.get("Win Lose") == "Win"
            else ("danger", "DEFEAT")
        )
        if att_def == "Attack Attack":
            att_def_string =  f"{gamemode} • {date_str}"
        else:
            att_def_string =  f"{gamemode} • {date_str} • {att_def}"
       
        # --- REVISED PLAYER LIST SECTION ---
        player_list_items = []
        for p in constants.players:
            hero = game.get(f"{p} Hero")
            if pd.notna(hero) and hero != "not present":
                role = game.get(f"{p} Role", "N/A")
                hero_image_url = get_hero_image_url(hero)

                player_list_items.append(
                    dbc.ListGroupItem(
                        # Use flexbox to align the avatar and the text content
                        html.Div(
                            [
                                # 1. The Hero Portrait (Avatar)
                                html.Img(
                                    src=hero_image_url,
                                    style={
                                        "width": "40px",
                                        "height": "40px",
                                        "borderRadius": "50%",
                                        "objectFit": "cover",
                                        "marginRight": "15px",
                                    },
                                ),
                                # 2. A div to hold the player info and hero name
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Span(p, className="fw-bold"),
                                                html.Span(
                                                    f" ({role})",
                                                    className="text-muted",
                                                    style={"fontSize": "0.9em"},
                                                ),
                                            ]
                                        ),
                                        html.Div(hero),
                                    ],
                                    # This inner flexbox pushes the player name and hero name apart
                                    className="d-flex justify-content-between align-items-center w-100",
                                ),
                            ],
                            # This outer flexbox aligns the image with the text block
                            className="d-flex align-items-center",
                        )
                    )
                )

        card = dbc.Card(
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            src=map_image_url,
                            className="img-fluid rounded-start h-100",
                            style={"objectFit": "cover"},
                        ),
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.CardHeader(
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H5(
                                                    f"{map_name}", className="mb-0"
                                                ),
                                                html.Small(
                                                    att_def_string,
                                                    className="text-muted",
                                                ),
                                            ]
                                        ),
                                        dbc.Badge(
                                            result_text,
                                            color=result_color,
                                            className="ms-auto",
                                            style={"height": "fit-content"},
                                        ),
                                    ],
                                    className="d-flex justify-content-between align-items-center",
                                )
                            ),
                            dbc.CardBody(
                                dbc.ListGroup(player_list_items, flush=True),
                                className="p-0",
                            ),
                        ],
                        md=9,
                    ),
                ],
                className="g-0",
            ),
            className="mb-3",
        )
        history_items.append(card)

    return history_items


def get_layout():
    return dbc.Container(
    [
        dcc.Store(id="history-display-count-store", data={"count": 10}),
        dbc.Row(
            [
                dbc.Col(
                    html.Img(
                        src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Overwatch_circle_logo.svg/1024px-Overwatch_circle_logo.svg.png",
                        height="50px",
                    ),
                    width="auto",
                ),
                dbc.Col(html.H1("Overwatch Statistics", className="my-4"), width=True),
                dbc.Col(
                    dbc.Button(
                        "Update Data from Cloud",
                        id="update-data-button",
                        color="primary",
                        className="mt-4",
                    ),
                    width="auto",
                ),
            ],
            align="center",
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Filter", className="bg-primary text-white"
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Label("Select Player:"),
                                        dcc.Dropdown(
                                            id="player-dropdown",
                                            options=[
                                                {"label": p, "value": p}
                                                for p in constants.players
                                            ],
                                            value=constants.players[0],
                                            clearable=False,
                                            className="mb-3",
                                        ),
                                        dbc.Label(
                                            "Select Season (overwrites Year/Month):"
                                        ),
                                        dcc.Dropdown(
                                            id="season-dropdown",
                                            placeholder="(not selected)",
                                            className="mb-3",
                                            clearable=True,
                                        ),
                                        dbc.Label("Select Year:"),
                                        dcc.Dropdown(
                                            id="year-dropdown",
                                            placeholder="(not selected)",
                                            className="mb-3",
                                            clearable=True,
                                        ),
                                        dbc.Label("Select Month:"),
                                        dcc.Dropdown(
                                            id="month-dropdown",
                                            placeholder="(not selected)",
                                            className="mb-3",
                                            clearable=True,
                                        ),
                                        dbc.Label("Minimum number of games:"),
                                        dcc.Slider(
                                            id="min-games-slider",
                                            min=1,
                                            max=100,
                                            step=None,
                                            value=5,
                                            marks={
                                                1: "1",
                                                5: "5",
                                                10: "10",
                                                25: "25",
                                                50: "50",
                                                75: "75",
                                                100: "100",
                                            },
                                            included=False,
                                            className="mb-1",
                                        ),
                                        html.Div(
                                            id="slider-hint",
                                            className="text-muted",
                                            style={"fontSize": "0.85em"},
                                        ),
                                        html.Hr(),
                                        html.Div(
                                            id="compare-switches-container",
                                            className="mt-3",
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Tabs(
                            [
                                dbc.Tab(
                                    label="Map & Mode Statistics",
                                    tab_id="tab-map",
                                    children=[
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="map-stat-type",
                                                        value="winrate",
                                                        clearable=False,
                                                        style={
                                                            "width": "100%",
                                                            "margin-bottom": "20px",
                                                        },
                                                        options=[
                                                            {
                                                                "label": "Winrate by Map",
                                                                "value": "winrate",
                                                            },
                                                            {
                                                                "label": "Games per Map",
                                                                "value": "plays",
                                                            },
                                                            {
                                                                "label": "Gamemode Statistics",
                                                                "value": "gamemode",
                                                            },
                                                            {
                                                                "label": "Attack/Defense Statistics",
                                                                "value": "attackdef",
                                                            },
                                                        ],
                                                    ),
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    html.Div(
                                                        dbc.Switch(
                                                            id="map-view-type",
                                                            label="Detailed",
                                                            value=False,
                                                            className="mt-1",
                                                        ),
                                                        id="map-view-type-container",
                                                        style={"margin-bottom": "20px"},
                                                    ),
                                                    width=4,
                                                    className="d-flex align-items-center",
                                                ),
                                            ]
                                        ),
                                        html.Div(id="map-stat-container"),
                                    ],
                                ),
                                dbc.Tab(
                                    label="Hero Statistics",
                                    tab_id="tab-hero",
                                    children=[
                                        dcc.Dropdown(
                                            id="hero-stat-type",
                                            value="winrate",
                                            clearable=False,
                                            style={
                                                "width": "300px",
                                                "margin-bottom": "20px",
                                            },
                                            options=[
                                                {
                                                    "label": "Winrate by Hero",
                                                    "value": "winrate",
                                                },
                                                {
                                                    "label": "Games per Hero",
                                                    "value": "plays",
                                                },
                                            ],
                                        ),
                                        dcc.Graph(id="hero-stat-graph"),
                                    ],
                                ),
                                dbc.Tab(
                                    label="Role Statistics",
                                    tab_id="tab-role",
                                    children=[
                                        dcc.Dropdown(
                                            id="role-stat-type",
                                            value="winrate",
                                            clearable=False,
                                            style={
                                                "width": "300px",
                                                "margin-bottom": "20px",
                                            },
                                            options=[
                                                {
                                                    "label": "Winrate by Role",
                                                    "value": "winrate",
                                                },
                                                {
                                                    "label": "Games per Role",
                                                    "value": "plays",
                                                },
                                            ],
                                        ),
                                        dcc.Graph(id="role-stat-graph"),
                                    ],
                                ),
                                dbc.Tab(
                                    dcc.Graph(id="performance-heatmap"),
                                    label="Performance Heatmap",
                                    tab_id="tab-heatmap",
                                ),
                                dbc.Tab(
                                    label="Winrate History",
                                    tab_id="tab-trend",
                                    children=[
                                        dbc.Label("Filter Hero (optional):"),
                                        dcc.Dropdown(
                                            id="hero-filter-dropdown",
                                            placeholder="No hero selected",
                                            className="mb-3",
                                        ),
                                        dcc.Graph(id="winrate-over-time"),
                                    ],
                                ),
                                dbc.Tab(
                                    label="Match History",
                                    tab_id="tab-history",
                                    children=[
                                        dbc.Card(
                                            dbc.CardBody([
                                                dbc.Row([
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Filter Player:"),
                                                            dcc.Dropdown(
                                                                id='player-dropdown-match-history',
                                                                options=[{'label': 'All Players', 'value': 'ALL'}] + [{'label': player, 'value': player} for player in constants.players],
                                                                value='ALL',
                                                                clearable=False,
                                                            ),
                                                        ],
                                                        width=6
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Filter Hero:"),
                                                            dcc.Dropdown(
                                                                id='hero-filter-dropdown-match',
                                                                placeholder="All Heroes",
                                                                clearable=True,
                                                            ),
                                                        ],
                                                        width=6
                                                    )
                                                ])
                                            ]),
                                            className="mb-3"
                                        ),
                                        html.Div(
                                            id="history-list-container",
                                            style={
                                                "maxHeight": "1000px",
                                                "overflowY": "auto",
                                            },
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="history-load-amount-dropdown",
                                                        options=[
                                                            {"label": "Load 10 more", "value": 10},
                                                            {"label": "Load 25 more", "value": 25},
                                                            {"label": "Load 50 more", "value": 50},
                                                        ],
                                                        value=10,
                                                        clearable=False,
                                                    ),
                                                    width={"size": 3, "offset": 3},
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        "Load More",
                                                        id="load-more-history-button",
                                                        color="secondary",
                                                        className="w-100",
                                                    ),
                                                    width=3,
                                                ),
                                            ],
                                            className="my-3 align-items-center",
                                            justify="center"
                                        ),
                                    ],
                                ),
                            ],
                            id="tabs",
                            active_tab="tab-map",
                        )
                    ],
                    width=9,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    id="stats-header", className="bg-primary text-white"
                                ),
                                dbc.CardBody([html.Div(id="stats-container")]),
                            ]
                        )
                    ],
                    width=12,
                )
            ],
            className="mt-4",
        ),
        html.Div(id="dummy-output", style={"display": "none"}),
    ],
    fluid=True,
)
