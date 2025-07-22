import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, ctx, State, ALL, html, dcc
import dash_bootstrap_components as dbc
import constants
from utils import (
    get_map_image_url,
    get_hero_image_url,
    create_stat_card,
    filter_data,
    calculate_winrate,
)
from layout import generate_history_layout_simple
from data import load_data, get_data


def register_callbacks(app):
    @app.callback(
        Output("dummy-output", "children"),
        Input("update-data-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def update_data_callback(n_clicks):
        if n_clicks > 0:
            load_data(use_local=False)
        return f"Data updated at {pd.Timestamp.now()}"

    @app.callback(
        Output("season-dropdown", "options"),
        Output("month-dropdown", "options"),
        Output("year-dropdown", "options"),
        Input("dummy-output", "children"),
    )
    def update_filter_options(_):
        df = get_data()
        if df.empty:
            return [], [], []
        season_options = [
            {"label": s, "value": s}
            for s in sorted(df["Season"].dropna().unique(), reverse=True)
        ]
        month_options = [
            {"label": m, "value": m} for m in sorted(df["Monat"].dropna().unique())
        ]
        year_options = [
            {"label": str(int(y)), "value": int(y)}
            for y in sorted(df["Jahr"].dropna().unique())
        ]
        return season_options, month_options, year_options

    @app.callback(
        Output("compare-switches-container", "children"),
        Input("player-dropdown", "value"),
    )
    def generate_comparison_switches(selected_player):
        other_players = [p for p in constants.players if p != selected_player]
        if not other_players:
            return None
        switches = [html.Label("Vergleiche mit:", className="fw-bold")]
        for player in other_players:
            switches.append(
                dbc.Switch(
                    id={"type": "compare-switch", "player": player},
                    label=player,
                    value=False,
                    className="mt-1",
                )
            )
        return switches

    @app.callback(
        Output({"type": "compare-switch", "player": ALL}, "value"),
        Input("player-dropdown", "value"),
        State({"type": "compare-switch", "player": ALL}, "value"),
        prevent_initial_call=True,
    )
    def reset_compare_switches(selected_player, switch_values):
        return [False] * len(switch_values)

    @app.callback(
        Output("map-view-type-container", "style"), Input("map-stat-type", "value")
    )
    def toggle_view_type_visibility(map_stat_type):
        if map_stat_type in ["winrate", "plays"]:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("min-games-slider", "disabled"),
        Output("slider-hint", "children"),
        Input("tabs", "active_tab"),
        Input("hero-stat-type", "value"),
        Input("role-stat-type", "value"),
        Input("map-stat-type", "value"),
    )
    def toggle_slider(tab, hero_stat, role_stat, map_stat):
        if (
            (tab == "tab-hero" and hero_stat == "winrate")
            or (tab == "tab-role" and role_stat == "winrate")
            or (tab == "tab-map" and map_stat in ["winrate", "gamemode", "attackdef"])
        ):
            return False, ""
        return True, "Nur relevant für Winrate-Statistiken"

    @app.callback(
        Output("history-list-container", "children"),
        Output("history-display-count-store", "data"),
        Input("load-more-history-button", "n_clicks"),
        Input("player-dropdown-match-verlauf", "value"),
        Input("hero-filter-dropdown-match", "value"),
        Input("dummy-output", "children"),
        State("history-display-count-store", "data"),
        State("history-load-amount-dropdown", "value"),
    )
    def update_history_display(
        n_clicks, player_name, hero_name, _, current_store, load_amount
    ):
        df = get_data()
        if df.empty:
            return [
                dbc.Alert("Keine Match History verfügbar.", color="danger")
            ], {"count": 10}

        triggered_id = ctx.triggered_id if ctx.triggered_id else "dummy-output"

        # Reset count if filters change, otherwise increment
        if triggered_id in [
            "player-dropdown-match-verlauf",
            "hero-filter-dropdown-match",
            "dummy-output",
        ]:
            new_count = 10
        else:  # triggered by "load-more-history-button"
            new_count = current_store.get("count", 10) + load_amount

        filtered_df = df.copy()

        # Filter by player
        if player_name and player_name != "ALL":
            player_hero_col = f"{player_name} Hero"
            if player_hero_col in filtered_df.columns:
                # Filter for games the player participated in
                filtered_df = filtered_df[
                    filtered_df[player_hero_col].notna()
                    & (filtered_df[player_hero_col] != "nicht dabei")
                ]

                # Filter by hero for that specific player
                if hero_name:
                    filtered_df = filtered_df[filtered_df[player_hero_col] == hero_name]

        # If a hero is selected but no specific player, filter for any player playing that hero
        elif hero_name and (not player_name or player_name == "ALL"):
            # Check all player hero columns
            hero_cols = [
                f"{p} Hero"
                for p in constants.players
                if f"{p} Hero" in filtered_df.columns
            ]
            # Create a boolean mask. True if any of the hero columns for a row equals the hero_name
            mask = filtered_df[hero_cols].eq(hero_name).any(axis=1)
            filtered_df = filtered_df[mask]

        games_to_show = filtered_df.head(new_count)
        history_layout = generate_history_layout_simple(games_to_show)

        if games_to_show.empty:
            history_layout = [
                dbc.Alert(
                    "Für diese Filterkombination wurden keine Spiele gefunden.",
                    color="info",
                )
            ]

        return history_layout, {"count": new_count}

    @app.callback(
        Output("hero-filter-dropdown-match", "options"),
        Output("hero-filter-dropdown-match", "value"),
        Input("player-dropdown-match-verlauf", "value"),
        Input("dummy-output", "children"),
        State("hero-filter-dropdown-match", "value"),
    )
    def update_match_history_hero_options(selected_player, _, current_hero):
        df = get_data()
        if df.empty:
            return [], None

        if not selected_player or selected_player == "ALL":
            # Show all heroes from all players if no player is selected
            all_heroes = set()
            for p in constants.players:
                hero_col = f"{p} Hero"
                if hero_col in df.columns:
                    all_heroes.update(
                        df[
                            df[hero_col].notna() & (df[hero_col] != "nicht dabei")
                        ][hero_col].unique()
                    )
            heroes = sorted(list(all_heroes))
        else:
            # Show heroes for the selected player
            player_hero_col = f"{selected_player} Hero"
            if player_hero_col in df.columns:
                heroes = sorted(
                    df[
                        df[player_hero_col].notna()
                        & (df[player_hero_col] != "nicht dabei")
                    ][player_hero_col].unique()
                )
            else:
                heroes = []

        hero_options = []
        for hero in heroes:
            hero_options.append(
                {
                    "label": html.Div(
                        [
                            html.Img(
                                src=get_hero_image_url(hero),
                                style={
                                    "height": "25px",
                                    "marginRight": "10px",
                                    "borderRadius": "50%",
                                },
                            ),
                            html.Span(hero),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                    "value": hero,
                }
            )

        # Check if the current hero is still valid
        if current_hero and current_hero in heroes:
            return hero_options, current_hero

        return hero_options, None

    @app.callback(
        Output("map-stat-container", "children"),
        Output("hero-stat-graph", "figure"),
        Output("role-stat-graph", "figure"),
        Output("performance-heatmap", "figure"),
        Output("stats-header", "children"),
        Output("stats-container", "children"),
        Output("winrate-over-time", "figure"),
        Output("hero-filter-dropdown", "options"),
        Input("player-dropdown", "value"),
        Input("min-games-slider", "value"),
        Input("season-dropdown", "value"),
        Input("month-dropdown", "value"),
        Input("year-dropdown", "value"),
        Input("hero-filter-dropdown", "value"),
        Input("hero-stat-type", "value"),
        Input("role-stat-type", "value"),
        Input("map-stat-type", "value"),
        Input("map-view-type", "value"),
        Input({"type": "compare-switch", "player": ALL}, "value"),
        State({"type": "compare-switch", "player": ALL}, "id"),
        Input("dummy-output", "children"),
    )
    def update_all_graphs(
        player,
        min_games,
        season,
        month,
        year,
        hero_filter,
        hero_stat_type,
        role_stat_type,
        map_stat_type,
        map_view_type,
        compare_values,
        compare_ids,
        _,
    ):
        df = get_data()
        dataframes = {player: filter_data(df, player, season, month, year)}
        active_compare_players = []
        if compare_ids:
            for i, is_on in enumerate(compare_values):
                if is_on:
                    p_name = compare_ids[i]["player"]
                    active_compare_players.append(p_name)
                    dataframes[p_name] = filter_data(df, p_name, season, month, year)
        main_df = dataframes[player]
        title_suffix = f"({player}{' vs ' + ', '.join(active_compare_players) if active_compare_players else ''})"
        empty_fig = go.Figure(
            layout={"title": "Keine Daten für die Auswahl verfügbar"}
        )
        stats_header = f"Gesamtstatistiken ({player})"

        stats_container = html.Div("Keine Daten für die Auswahl verfügbar.")
        if not main_df.empty:
            total, wins = len(main_df), len(main_df[main_df["Win Lose"] == "Win"])
            losses, winrate = total - wins, wins / total if total > 0 else 0

            # --- REVISED: Primary Stats Row ---
            primary_stats_row = dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Gesamtspiele"),
                                dbc.CardBody(html.H4(f"{total}")),
                            ],
                            className="text-center h-100",
                        )
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Gewonnen"),
                                dbc.CardBody(
                                    html.H4(f"{wins}", className="text-success")
                                ),
                            ],
                            className="text-center h-100",
                        )
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Verloren"),
                                dbc.CardBody(
                                    html.H4(f"{losses}", className="text-danger")
                                ),
                            ],
                            className="text-center h-100",
                        )
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Winrate"),
                                dbc.CardBody(
                                    html.H4(f"{winrate:.0%}", className="text-primary")
                                ),
                            ],
                            className="text-center h-100",
                        )
                    ),
                ],
                className="mb-4", 
            )

            # --- Row 2: "Best Of" Stats ---
            secondary_stat_cards = []
            try:
                most_played_hero = main_df["Hero"].mode()[0]
                hero_plays = main_df["Hero"].value_counts()[most_played_hero]
                card = create_stat_card(
                    "Meistgespielter Held",
                    get_hero_image_url(most_played_hero),
                    most_played_hero,
                    f"{hero_plays} Spiele",
                )
            except (KeyError, IndexError):
                card = create_stat_card(
                    "Meistgespielter Held",
                    get_hero_image_url(None),
                    "N/A",
                    "Keine Daten",
                )
            secondary_stat_cards.append(card)
            try:
                hero_wr = calculate_winrate(main_df, "Hero")
                hero_wr_filtered = hero_wr[hero_wr["Spiele"] >= min_games]
                best_hero = hero_wr_filtered.loc[hero_wr_filtered["Winrate"].idxmax()]
                card = create_stat_card(
                    "Beste Winrate (Held)",
                    get_hero_image_url(best_hero["Hero"]),
                    best_hero["Hero"],
                    f"{best_hero['Winrate']:.0%} ({best_hero['Spiele']} Spiele)",
                )
            except (KeyError, IndexError, ValueError):
                card = create_stat_card(
                    "Beste Winrate (Held)",
                    get_hero_image_url(None),
                    "N/A",
                    f"Min. {min_games} Spiele",
                )
            secondary_stat_cards.append(card)
            try:
                most_played_map = main_df["Map"].mode()[0]
                map_plays = main_df["Map"].value_counts()[most_played_map]
                card = create_stat_card(
                    "Meistgespielte Map",
                    get_map_image_url(most_played_map),
                    most_played_map,
                    f"{map_plays} Spiele",
                )
            except (KeyError, IndexError):
                card = create_stat_card(
                    "Meistgespielte Map", get_map_image_url(None), "N/A", "Keine Daten"
                )
            secondary_stat_cards.append(card)
            try:
                map_wr = calculate_winrate(main_df, "Map")
                map_wr_filtered = map_wr[map_wr["Spiele"] >= min_games]
                best_map = map_wr_filtered.loc[map_wr_filtered["Winrate"].idxmax()]
                card = create_stat_card(
                    "Beste Winrate (Map)",
                    get_map_image_url(best_map["Map"]),
                    best_map["Map"],
                    f"{best_map['Winrate']:.0%} ({best_map['Spiele']} Spiele)",
                )
            except (KeyError, IndexError, ValueError):
                card = create_stat_card(
                    "Beste Winrate (Map)",
                    get_map_image_url(None),
                    "N/A",
                    f"Min. {min_games} Spiele",
                )
            secondary_stat_cards.append(card)

            stats_container = html.Div(
                [primary_stats_row, dbc.Row(secondary_stat_cards)]
            )

        map_stat_output = None
        attack_def_modes = ["Attack", "Defense", "Attack Attack"]
        bar_fig = go.Figure()
        if (
            map_view_type
            and not active_compare_players
            and map_stat_type in ["winrate", "plays"]
        ):
            if map_stat_type == "winrate":
                map_data = calculate_winrate(main_df, "Map")
                map_data = map_data[map_data["Spiele"] >= min_games]
                if not map_data.empty:
                    plot_df = main_df[
                        main_df["Attack Def"].isin(attack_def_modes)
                    ].copy()
                    plot_df["Mode"] = plot_df["Attack Def"].replace(
                        {"Attack Attack": "Gesamt"}
                    )
                    grouped = (
                        plot_df.groupby(["Map", "Mode", "Win Lose"])
                        .size()
                        .unstack(fill_value=0)
                    )
                    if "Win" not in grouped:
                        grouped["Win"] = 0
                    if "Lose" not in grouped:
                        grouped["Lose"] = 0
                    grouped["Spiele"] = grouped["Win"] + grouped["Lose"]
                    grouped["Winrate"] = grouped["Win"] / grouped["Spiele"]
                    plot_data = grouped.reset_index()
                    plot_data = plot_data[plot_data["Map"].isin(map_data["Map"])]
                    if not plot_data.empty:
                        bar_fig = px.bar(
                            plot_data,
                            x="Map",
                            y="Winrate",
                            color="Mode",
                            barmode="group",
                            title=f"Map Winrates (Detailliert) - {player}",
                            category_orders={
                                "Map": map_data["Map"].tolist(),
                                "Mode": ["Gesamt", "Attack", "Defense"],
                            },
                            custom_data=["Spiele"],
                            color_discrete_map={
                                "Gesamt": "lightslategrey",
                                "Attack": "#EF553B",
                                "Defense": "#636EFA",
                            },
                        )
                        bar_fig.update_traces(
                            hovertemplate="Winrate: %{y:.1%}<br>Spiele: %{customdata[0]}<extra></extra>"
                        )
                        bar_fig.update_layout(yaxis_tickformat=".0%")
                    else:
                        bar_fig = empty_fig
                else:
                    bar_fig = empty_fig
            elif map_stat_type == "plays":
                if not main_df.empty:
                    plot_df = main_df.copy()
                    plot_df["Seite"] = plot_df["Attack Def"].apply(
                        lambda x: x if x in attack_def_modes else "Andere Modi"
                    )
                    plays_by_side = (
                        plot_df.groupby(["Map", "Seite"])
                        .size()
                        .reset_index(name="Spiele")
                    )
                    total_plays_map = (
                        main_df.groupby("Map")
                        .size()
                        .reset_index(name="TotalSpiele")
                        .sort_values("TotalSpiele", ascending=False)
                    )
                    bar_fig = px.bar(
                        plays_by_side,
                        x="Map",
                        y="Spiele",
                        color="Seite",
                        barmode="stack",
                        title=f"Spiele pro Map (Detailliert) - {player}",
                        labels={"Spiele": "Anzahl Spiele", "Seite": "Seite"},
                        category_orders={"Map": list(total_plays_map["Map"])},
                        color_discrete_map={
                            "Attack": "#EF553B",
                            "Defense": "#00CC96",
                            "Attack Attack": "#636EFA",
                        },
                    )
                    bar_fig.update_traces(
                        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y}<extra></extra>"
                    )
                else:
                    bar_fig = empty_fig
        else:
            group_col = {
                "winrate": "Map",
                "plays": "Map",
                "gamemode": "Gamemode",
                "attackdef": "Attack Def",
            }.get(map_stat_type)
            y_col = (
                "Winrate"
                if map_stat_type in ["winrate", "gamemode", "attackdef"]
                else "Spiele"
            )
            for name, df_to_plot in dataframes.items():
                if (
                    not df_to_plot.empty
                    and group_col
                    and group_col in df_to_plot.columns
                ):
                    if y_col == "Winrate":
                        stats = calculate_winrate(df_to_plot, group_col)
                        stats = stats[stats["Spiele"] >= min_games]
                        if not stats.empty:
                            bar_fig.add_trace(
                                go.Bar(
                                    x=stats[group_col],
                                    y=stats[y_col],
                                    name=name,
                                    customdata=stats[["Spiele"]],
                                    hovertemplate="<b>%{x}</b><br>Winrate: %{y:.1%}<br>Spiele: %{customdata[0]}<extra></extra>",
                                )
                            )
                    else:
                        stats = (
                            df_to_plot.groupby(group_col)
                            .size()
                            .reset_index(name="Spiele")
                            .sort_values("Spiele", ascending=False)
                        )
                        if not stats.empty:
                            bar_fig.add_trace(
                                go.Bar(
                                    x=stats[group_col],
                                    y=stats[y_col],
                                    name=name,
                                    hovertemplate="<b>%{x}</b><br>Spiele: %{y}<extra></extra>",
                                )
                            )
            bar_fig.update_layout(
                title=f"{map_stat_type.title().replace('def', 'Def')} nach {group_col} {title_suffix}",
                barmode="group",
                yaxis_title=y_col,
                legend_title="Spieler",
            )
            if y_col == "Winrate":
                bar_fig.update_layout(yaxis_tickformat=".0%")
            if not bar_fig.data:
                bar_fig = empty_fig
        if map_stat_type == "winrate":
            map_stat_output = dbc.Row(dbc.Col(dcc.Graph(figure=bar_fig), width=12))
        else:
            pie_fig = go.Figure()
            pie_data_col = None
            if map_stat_type == "gamemode":
                pie_data_col = "Gamemode"
            elif map_stat_type == "attackdef":
                pie_data_col = "Attack Def"
            if pie_data_col:
                pie_data = main_df.copy()
                if pie_data_col == "Attack Def":
                    pie_data = pie_data[pie_data["Attack Def"].isin(attack_def_modes)]
                pie_data = (
                    pie_data.groupby(pie_data_col).size().reset_index(name="Spiele")
                )
                if not pie_data.empty:
                    pie_fig = px.pie(
                        pie_data,
                        names=pie_data_col,
                        values="Spiele",
                        title=f"Verteilung {pie_data_col}",
                    )
                    pie_fig.update_traces(
                        hovertemplate="<b>%{label}</b><br>Spiele: %{value}<br>Anteil: %{percent}<extra></extra>"
                    )
                else:
                    pie_fig = empty_fig
            if map_stat_type == "plays":
                map_stat_output = dbc.Row(
                    [dbc.Col(dcc.Graph(figure=bar_fig), width=12)]
                )
            else:
                map_stat_output = dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=bar_fig), width=7),
                        dbc.Col(dcc.Graph(figure=pie_fig), width=5),
                    ]
                )

        def create_comparison_fig(stat_type, group_col):
            fig = go.Figure()
            y_col = "Winrate" if stat_type == "winrate" else "Spiele"
            for name, df_to_plot in dataframes.items():
                if not df_to_plot.empty:
                    if y_col == "Winrate":
                        stats = calculate_winrate(df_to_plot, group_col)
                        stats = stats[stats["Spiele"] >= min_games]
                        if not stats.empty:
                            fig.add_trace(
                                go.Bar(
                                    x=stats[group_col],
                                    y=stats[y_col],
                                    name=name,
                                    customdata=stats[["Spiele"]],
                                    hovertemplate="<b>%{x}</b><br>Winrate: %{y:.1%}<br>Spiele: %{customdata[0]}<extra></extra>",
                                )
                            )
                    else:
                        stats = (
                            df_to_plot.groupby(group_col)
                            .size()
                            .reset_index(name="Spiele")
                            .sort_values("Spiele", ascending=False)
                        )
                        if not stats.empty:
                            fig.add_trace(
                                go.Bar(
                                    x=stats[group_col],
                                    y=stats[y_col],
                                    name=name,
                                    hovertemplate="<b>%{x}</b><br>Spiele: %{y}<extra></extra>",
                                )
                            )
            fig.update_layout(
                title=f"{stat_type.title()} nach {group_col} {title_suffix}",
                barmode="group",
                yaxis_title=y_col,
                legend_title="Spieler",
            )
            if y_col == "Winrate":
                fig.update_layout(yaxis_tickformat=".0%")
            return fig if fig.data else empty_fig

        hero_fig = create_comparison_fig(hero_stat_type, "Hero")
        role_fig = create_comparison_fig(role_stat_type, "Rolle")
        heatmap_fig = empty_fig
        if not main_df.empty:
            try:
                pivot = main_df.pivot_table(
                    index="Rolle",
                    columns="Map",
                    values="Win Lose",
                    aggfunc=lambda x: (x == "Win").sum() / len(x)
                    if len(x) > 0
                    else 0,
                )
                if not pivot.empty:
                    heatmap_fig = px.imshow(
                        pivot,
                        text_auto=".0%",
                        color_continuous_scale="RdYlGn",
                        zmin=0,
                        zmax=1,
                        aspect="auto",
                        title=f"Winrate Heatmap – {player}",
                    )
                    heatmap_fig.update_traces(
                        hovertemplate="<b>Map: %{x}</b><br><b>Rolle: %{y}</b><br><b>Winrate: %{z: .1%}</b><extra></extra>"
                    )
            except Exception:
                pass
        winrate_fig = go.Figure()
        for name, df_to_plot in dataframes.items():
            if not df_to_plot.empty and "Datum" in df_to_plot.columns:
                time_data = df_to_plot.dropna(subset=["Datum"]).copy()
                time_data.sort_values("Datum", inplace=True, ascending=True)
                if hero_filter:
                    time_data = time_data[time_data["Hero"] == hero_filter]
                if not time_data.empty:
                    time_data["Win"] = (time_data["Win Lose"] == "Win").astype(int)
                    time_data["GameNum"] = range(1, len(time_data) + 1)
                    time_data["CumulativeWinrate"] = (
                        time_data["Win"].cumsum() / time_data["GameNum"]
                    )
                    winrate_fig.add_trace(
                        go.Scatter(
                            x=time_data["GameNum"],
                            y=time_data["CumulativeWinrate"],
                            mode="lines",
                            name=name,
                        )
                    )
        winrate_fig.update_layout(
            title=f"Winrate-Verlauf {title_suffix}",
            yaxis_tickformat=".0%",
            yaxis_title="Winrate",
            xaxis_title="Spielnummer",
            legend_title="Spieler",
        )
        winrate_fig.update_traces(
            hovertemplate="<b>Spielnummer: %{x}</b><br><b>Winrate: %{y: .1%}</b><extra></extra>"
        )
        if not winrate_fig.data:
            winrate_fig = empty_fig

        hero_options = []
        if not main_df.empty:
            heroes = sorted(main_df["Hero"].dropna().unique())
            for hero in heroes:
                hero_options.append(
                    {
                        "label": html.Div(
                            [
                                html.Img(
                                    src=get_hero_image_url(hero),
                                    style={
                                        "height": "25px",
                                        "marginRight": "10px",
                                        "borderRadius": "50%",
                                    },
                                ),
                                html.Span(hero),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        "value": hero,
                    }
                )

        return (
            map_stat_output,
            hero_fig,
            role_fig,
            heatmap_fig,
            stats_header,
            stats_container,
            winrate_fig,
            hero_options,
        )
