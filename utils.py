import os
import re
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html

def get_map_image_url(map_name):
    """
    Generates a URL for a map's background image.
    Assumes images are in 'assets/maps/' and named like 'map_name.png'.
    """
    if not isinstance(map_name, str):
        return "/assets/maps/default.jpg"  # Fallback for non-string input

    # Clean the map name to create a valid filename
    # e.g., "King's Row" -> "kings_row"
    cleaned_name = map_name.lower().replace(" ", "_").replace("'", "")

    for ext in [".jpg", ".png"]:
        image_filename = f"{cleaned_name}{ext}"
        asset_path = f"/assets/maps/{image_filename}"
        local_path = os.path.join("assets", "maps", image_filename)

        if os.path.exists(local_path):
            return asset_path

    return "/assets/maps/default.png"


def get_hero_image_url(hero_name):
    """
    Generates a URL for a hero's portrait with more robust, flexible checking.
    It tries multiple common filename variations and checks for both .png and .jpg.
    """
    if not isinstance(hero_name, str):
        return "/assets/heroes/default_hero.png"

    base_name = hero_name.lower()

    potential_names = []

    # 1. Standard cleaning (e.g., "d.va" -> "dva", "lúcio" -> "lucio")
    cleaned_base = base_name.replace(".", "").replace(":", "").replace("ú", "u")

    # 2. Add variations for spaces (e.g., "soldier 76" -> "soldier_76" AND "soldier76")
    potential_names.append(cleaned_base.replace(" ", "_"))
    potential_names.append(cleaned_base.replace(" ", ""))

    # 3. Add aggressive cleaning as a final fallback (removes all non-letters/numbers)
    potential_names.append(re.sub(r"[^a-z0-9]", "", base_name))

    # Remove any duplicate names that may have been generated
    potential_names = list(set(potential_names))


    for name in potential_names:
        if not name:
            continue  

        for ext in [".png", ".jpg", ".jpeg"]: 
            image_filename = f"{name}{ext}"
            asset_path = f"/assets/heroes/{image_filename}"
            local_path = os.path.join("assets", "heroes", image_filename)

            if os.path.exists(local_path):
                return asset_path

    # Return default if nothing found.
    return "/assets/heroes/default_hero.png"


def create_stat_card(title, image_url, main_text, sub_text):
    """
    Creates a single formatted statistics card.
    """
    return dbc.Col(
        dbc.Card(
            [
                dbc.CardHeader(title),
                dbc.CardBody(
                    html.Div(
                        [
                            html.Img(
                                src=image_url,
                                style={
                                    "width": "60px",
                                    "height": "60px",
                                    "objectFit": "cover",
                                    "borderRadius": "8px",
                                    "marginRight": "15px",
                                },
                            ),
                            html.Div(
                                [
                                    html.H5(main_text, className="mb-0"),
                                    html.Small(sub_text, className="text-muted"),
                                ]
                            ),
                        ],
                        className="d-flex align-items-center",
                    )
                ),
            ],
            className="h-100",
        ),
        md=3,
    )


def filter_data(df, player, season=None, month=None, year=None):
    if df.empty:
        return pd.DataFrame()
    temp = df[df["Win Lose"].isin(["Win", "Lose"])].copy()
    if season:
        temp = temp[temp["Season"] == season]
    else:
        if year is not None:
            temp = temp[pd.to_numeric(temp["Year"], errors="coerce") == int(year)]
        if month is not None:
            temp = temp[temp["Month"] == month]
    role_col, hero_col = f"{player} Role", f"{player} Hero"
    if role_col not in temp.columns or hero_col not in temp.columns:
        return pd.DataFrame()
    temp = temp[temp[role_col].notna() & (temp[role_col] != "not present")]
    if temp.empty:
        return pd.DataFrame()
    temp["Hero"], temp["Role"] = temp[hero_col].str.strip(), temp[role_col].str.strip()
    return temp[temp["Hero"].notna() & (temp["Hero"] != "")]


def calculate_winrate(data, group_col):
    if data.empty or not isinstance(group_col, str) or group_col not in data.columns:
        return pd.DataFrame(columns=[group_col, "Win", "Lose", "Winrate", "Games"])
    data[group_col] = data[group_col].astype(str).str.strip()
    data = data[data[group_col].notna() & (data[group_col] != "")]
    if data.empty:
        return pd.DataFrame(columns=[group_col, "Win", "Lose", "Winrate", "Games"])
    grouped = data.groupby([group_col, "Win Lose"]).size().unstack(fill_value=0)
    if "Win" not in grouped:
        grouped["Win"] = 0
    if "Lose" not in grouped:
        grouped["Lose"] = 0
    grouped["Games"] = grouped["Win"] + grouped["Lose"]
    grouped["Winrate"] = grouped["Win"] / grouped["Games"]
    return grouped.reset_index().sort_values("Winrate", ascending=False)
