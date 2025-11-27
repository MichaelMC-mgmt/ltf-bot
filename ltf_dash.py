# app.py - {MC} Terminal – Multi-Page Dashboard (November 2025)
from dash import Dash, html, dcc, page_registry, page_container, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash

# Use a clean external Bootstrap theme + custom CSS for terminal feel
external_stylesheets = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
    dbc.themes.DARKLY,  # Base dark theme
]

app = Dash(
    __name__,
    use_pages=True,                    # Enables multi-page
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

app.title = "{MC} Terminal"

# Custom CSS to match your exact design
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #000000;
                margin: 0;
                padding: 0;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            .terminal-title {
                font-size: 2.8rem;
                font-weight: bold;
                background: linear-gradient(90deg, #00ffff, #0088ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 60px;
                letter-spacing: 4px;
            }
            .nav-button {
                background-color: #0d1117 !important;
                border: 2px solid #30363d !important;
                border-radius: 12px !important;
                color: #58a6ff !important;
                font-size: 1.4rem;
                font-weight: 600;
                padding: 18px 32px !important;
                margin: 12px 0;
                width: 380px;
                text-align: left;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
            }
            .nav-button:hover {
                background-color: #161b22 !important;
                border-color: #58a6ff !important;
                color: white !important;
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(88, 166, 255, 0.3);
            }
            .nav-button.active {
                background: linear-gradient(90deg, #003366, #000000) !important;
                border-color: #00ffff !important;
                color: #00ffff !important;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
            }
            .tab-selected {
                background-color: #1f6feb !important;
                color: white !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Homepage Layout – EXACTLY like your screenshot
home_layout = html.Div([
    html.Div([
        html.H1("{MC} Terminal", className="terminal-title"),
        
        # Top Tabs
        dbc.Tabs([
            dbc.Tab(label="LTF Bots", tab_id="ltf", label_style={"borderRadius": "8px", "margin": "0 8px"}),
            dbc.Tab(label="HTF Bots", tab_id="htf", label_style={"borderRadius": "8px", "margin": "0 8px"}),
        ], id="top-tabs", active_tab="ltf"),

        html.Div(style={'height': '80px'}),  # Spacer

        # Navigation Buttons (Vertical Menu)
        html.Div([
            dbc.Button("CC Engine", id="btn-cc", className="nav-button", n_clicks=0),
            dbc.Button("Market Regime", id="btn-regime", className="nav-button", n_clicks=0),
            dbc.Button("Rotation Strategies", id="btn-rotation", className="nav-button", n_clicks=0),
            dbc.Button("Liquidation Heatmap", id="btn-heatmap", className="nav-button", n_clicks=0),
            dbc.Button("Daily PnL %", id="btn-pnl", className="nav-button", n_clicks=0),
        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})
    ], style={
        'display': 'flex',
        'flexDirection': 'column',
        'alignItems': 'center',
        'justifyContent': 'center',
        'minHeight': '100vh',
        'padding': '40px'
    })
])

# Register the home page
dash.register_page("home", path="/", layout=home_layout, name="Home", order=0)

# ===================================================================
# Navigation Callbacks – Make buttons actually navigate
# ===================================================================
@callback(
    Output("top-tabs", "active_tab"),
    [Input("btn-cc", "n_clicks"),
     Input("btn-regime", "n_clicks"),
     Input("btn-rotation", "n_clicks"),
     Input("btn-heatmap", "n_clicks"),
     Input("btn-pnl", "n_clicks")],
    prevent_initial_call=True
)
def navigate_from_buttons(*args):
    triggered = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    mapping = {
        "btn-cc": "cc-engine",
        "btn-regime": "market-regime",
        "btn-rotation": "rotation",
        "btn-heatmap": "heatmap",
        "btn-pnl": "pnl"
    }
    if triggered in mapping:
        dash.page_registry[mapping[triggered]]["path"]
        # We'll handle actual navigation via client-side callback below
    return dash.no_update

# Client-side navigation (instant & smooth)
app.clientside_callback(
    """
    function(cc, regime, rotation, heatmap, pnl) {
        const triggered = (dash_clientside.callback_context || {}).triggered_id;
        const routes = {
            'btn-cc': '/cc-engine',
            'btn-regime': '/market-regime',
            'btn-rotation': '/rotation-strategies',
            'btn-heatmap': '/liquidation-heatmap',
            'btn-pnl': '/daily-pnl'
        };
        if (triggered && routes[triggered]) {
            window.location.href = routes[triggered];
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("top-tabs", "id"),  # dummy output
    [Input("btn-cc", "n_clicks"),
     Input("btn-regime", "n_clicks"),
     Input("btn-rotation", "n_clicks"),
     Input("btn-heatmap", "n_clicks"),
     Input("btn-pnl", "n_clicks")]
)

# ===================================================================
# App Layout (Multi-page container)
# ===================================================================
app.layout = html.Div([
    dcc.Location(id="url"),
    page_container
])

# ===================================================================
# Run
# ===================================================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print(" {MC} TERMINAL IS LIVE ")
    print(" → http://127.0.0.1:8050")
    print(" → Press CTRL+C to stop")
    print("="*80 + "\n")
    app.run(host="0.0.0.0", port=8050, debug=False)
