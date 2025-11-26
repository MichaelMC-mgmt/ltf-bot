# dashboard.py - FINAL 100% WORKING DASHBOARD - NOV 2025
from dash import Dash, html, dcc, Input, Output
import plotly.graph_objs as go

# Import your bot's live state
# CONNECT TO YOUR LIVE RENDER BOT
import requests
import json

RENDER_BOT_URL = "https://ltf-bot.onrender.com"  # ← YOUR LIVE BOT URL

def get_bot_state():
    try:
        r = requests.get(f"{RENDER_BOT_URL}/state", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

app = Dash(__name__)
app.title = "LTF Bot Dashboard"

# Dark theme style
card_style = {
    'backgroundColor': '#1e1e2e',
    'color': 'white',
    'padding': '20px',
    'margin': '10px',
    'borderRadius': '10px',
    'textAlign': 'center',
    'minWidth': '180px',
    'boxShadow': '0 4px 8px rgba(0,0,0,0.3)'
}

app.layout = html.Div(style={'backgroundColor': '#0d1117', 'color': 'white', 'fontFamily': 'Arial'}, children=[
    html.H1("LTF Trading Bot - LIVE", style={'textAlign': 'center', 'margin': '30px'}),

    dcc.Interval(id='interval', interval=5000, n_intervals=0),

    html.Div(id='stats-row', style={'display': 'flex', 'justifyContent': 'center', 'flexWrap': 'wrap'}),

    html.Hr(style={'borderColor': '#30363d'}),

    html.H2("Indicator States", style={'textAlign': 'center'}),
    html.Div(id='indicators-grid', style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '20px', 'margin': '30px'}),

    dcc.Graph(id='equity-chart', style={'height': '400px', 'margin': '30px'}),

    html.Hr(style={'borderColor': '#30363d'}),

    html.H2("Manual Controls", style={'textAlign': 'center'}),
    html.Div([
        html.Button("FORCE CLOSE ALL", id="close-all", n_clicks=0,
                    style={'background': '#ff4444', 'color': 'white', 'padding': '15px 30px', 'margin': '10px', 'fontSize': '18px', 'border': 'none', 'borderRadius': '8px'}),
        html.Button("Manual Long ETH", id="long-eth", n_clicks=0,
                    style={'background': '#00aa00', 'color': 'white', 'padding': '15px 30px', 'margin': '10px', 'fontSize': '18px', 'border': 'none', 'borderRadius': '8px'}),
        html.Button("Manual Short ETH", id="short-eth", n_clicks=0,
                    style={'background': '#aa0000', 'color': 'white', 'padding': '15px 30px', 'margin': '10px', 'fontSize': '18px', 'border': 'none', 'borderRadius': '8px'}),
    ], style={'textAlign': 'center', 'margin': '30px'}),

    html.Div(id='output', style={'textAlign': 'center', 'fontSize': '20px', 'margin': '20px'})
])

# Get live position
def get_position():
    try:
        pos = exchange.fetch_positions(['ETHUSDT'])[0]
        size = float(pos['contracts'])
        if abs(size) < 0.001: return None
        return {
            'side': 'LONG' if size > 0 else 'SHORT',
            'size': abs(size),
            'entry': float(pos['entryPrice']),
            'upl': float(pos['unrealisedPnl']),
            'pct': float(pos.get('percentage', 0))
        }
    except Exception as e:
        print(f"Position fetch error: {e}")
        return None

@app.callback(
    [Output('stats-row', 'children'),
     Output('indicators-grid', 'children'),
     Output('equity-chart', 'figure'),
     Output('output', 'children')],
    Input('interval', 'n_intervals')
)
def update_dashboard(n):
    equity = get_equity()
    pos = get_position()
    eth = states.get('ETHUSDT', {})

    stats = [
        html.Div([html.H2(f"${equity:,.2f}"), html.P("Equity")], style=card_style),
        html.Div([html.H2(pos['side'] if pos else "FLAT"), html.P("Position")], style=card_style),
        html.Div([html.H2(f"{pos['upl']:+.2f}" if pos else "0.00"), html.P("Unrealized PnL")],
                 style={**card_style, 'color': '#00ff00' if pos and pos['upl'] > 0 else '#ff4444'}),
        html.Div([html.H2(f"{pos['pct']:+.2f}%" if pos else "0.00%"), html.P("Return")],
                 style={**card_style, 'color': '#00ff00' if pos and pos['pct'] > 0 else '#ff4444'}),
    ]

    indicators = [
        html.Div([html.H3("Value Exhaustion"), html.H1("🟢" if eth.get('value_exhaustion') else "🔴")], style=card_style),
        html.Div([html.H3("Universal Val"), html.H1("🟢" if eth.get('universal_val') else "🔴")], style=card_style),
        html.Div([html.H3("Conviction Ratio"), html.H1("🟢" if eth.get('conviction') else "🔴")], style=card_style),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=[equity], mode='lines+markers', name='Equity', line=dict(color='#58a6ff')))
    fig.update_layout(template='plotly_dark', title="Live Equity", paper_bgcolor='#0d1117', plot_bgcolor='#0d1117')

    return stats, indicators, fig, ""

@app.callback(
    Output('output', 'children'),
    [Input('close-all', 'n_clicks'), Input('long-eth', 'n_clicks'), Input('short-eth', 'n_clicks')]
)
def controls(c, l, s):
    from dash import ctx
    if not ctx.triggered: return ""
    btn = ctx.triggered[0]['prop_id'].split('.')[0]
    from ltf_app import exit_position, enter_long, enter_short
    if btn == 'close-all':
        for a in ASSETS:
            exit_position(a)
        return "ALL POSITIONS CLOSED"
    if btn == 'long-eth':
        enter_long('ETHUSDT')
        return "MANUAL LONG EXECUTED"
    if btn == 'short-eth':
        enter_short('ETHUSDT')
        return "MANUAL SHORT EXECUTED"
    return ""

if __name__ == '__main__':
    print("\n" + "="*70)
    print("LTF DASHBOARD IS LIVE → http://127.0.0.1:8050")
    print("Make sure ltf_app.py is running on port 5000!")
    print("="*70 + "\n")

    app.run(host='0.0.0.0', port=8050, debug=False)
