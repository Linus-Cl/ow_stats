from dash import Dash
import dash_bootstrap_components as dbc
from layout import get_layout
from callbacks import register_callbacks
from data import load_data

# --- App Initialization ---
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
)
server = app.server

# --- Data Loading ---
load_data(use_local=True)

# --- Layout ---
app.layout = get_layout()

# --- Callbacks ---
register_callbacks(app)

# --- Main ---
if __name__ == "__main__":
    app.run(debug=False)