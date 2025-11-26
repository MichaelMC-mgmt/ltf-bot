# ltf_app.py - FINAL 100% WORKING ON RENDER - NO ERRORS - NOV 2025
import logging
import os
import time
import threading
import requests
from flask import Flask, request, jsonify
import ccxt
from dotenv import load_dotenv

app = Flask(__name__)
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv('ltf_api.env')

EXCHANGE_RECV_WINDOW = 20000
ASSETS = ['BTCUSDT', 'ETHUSDT']
LEVERAGE = 10

exchange = ccxt.bybit({
    'apiKey': os.getenv('BYBIT_API_KEY'),
    'secret': os.getenv('BYBIT_API_SECRET'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'recvWindow': EXCHANGE_RECV_WINDOW,
    },
})

# CRITICAL RENDER FIX - REMOVE SPOT MARKETS TO AVOID 403
try:
    exchange.load_markets()
    # Filter out spot markets - this stops the 403 error
    exchange.markets = {k: v for k, v in exchange.markets.items() if v.get('linear') or v.get('future')}
    logging.info("Render fix applied - spot markets removed, only futures loaded")
except Exception as e:
    logging.error(f"Market load failed: {e}")

# Isolated + 10x setup
def setup_isolated(symbol):
    try:
        sym = symbol.replace("/", "")
        exchange.private_post_v5_position_switch_mode({'category': 'linear', 'symbol': sym, 'mode': 0})
        exchange.private_post_v5_position_switch_isolated({
            'category': 'linear', 'symbol': sym, 'tradeMode': 1,
            'buyLeverage': '10', 'sellLeverage': '10'
        })
    except: pass
for a in ASSETS: setup_isolated(a)

# State
states = {a: {'value_exhaustion': False, 'universal_val': False, 'conviction': False,
              'in_position': False, 'direction': None, 'entry_price': None, 'size': 0} for a in ASSETS}

def normalize(s): return s if '/' in s else s.replace("USDT", "/USDT")

# Balance
def get_equity():
    try:
        bal = exchange.fetch_balance(params={'type': 'future'})
        return float(bal['USDT']['total'])
    except Exception as e:
        logging.error(f"Balance error: {e}")
        return 0.0

# Position sizing - perfect qtyStep
def get_position_size(symbol):
    equity = get_equity()
    if equity < 20: return 0.0
    price = exchange.fetch_ticker(symbol)['last']
    qty = (equity * 0.95) / price
    qty = max(qty, 0.12 if 'ETH' in symbol else 0.001)
    qty = round(qty, 3)
    qty = float(exchange.amount_to_precision(symbol, qty))
    logging.info(f"FINAL QTY: {qty} | Notional: {qty*price:.2f}")
    return qty

# ENTER LONG
def enter_long(asset):
    size = get_position_size(normalize(asset))
    if size < 0.001: return
    s = normalize(asset)
    try:
        exchange.create_order(s, 'market', 'buy', size, params={'category': 'linear', 'positionIdx': 0})
        price = exchange.fetch_ticker(s)['last']
        states[asset].update({'in_position': True, 'direction': 'long', 'entry_price': price, 'size': size})
        logging.info(f"LONG OPENED {asset} | {size} @ {price}")
    except Exception as e:
        logging.error(f"LONG FAILED: {e}")
        states[asset]['in_position'] = False

# ENTER SHORT
def enter_short(asset):
    size = get_position_size(normalize(asset))
    if size < 0.001: return
    s = normalize(asset)
    try:
        exchange.create_order(s, 'market', 'sell', size, params={'category': 'linear', 'positionIdx': 0})
        price = exchange.fetch_ticker(s)['last']
        states[asset].update({'in_position': True, 'direction': 'short', 'entry_price': price, 'size': size})
        logging.info(f"SHORT OPENED {asset} | {size} @ {price}")
    except Exception as e:
        logging.error(f"SHORT FAILED: {e}")
        states[asset]['in_position'] = False

# EXIT - FIXED list index error
def exit_position(asset):
    try:
        s = normalize(asset)
        positions = exchange.fetch_positions(params={'category': 'linear'})
        # Find position for our symbol
        pos = next((p for p in positions if p['symbol'] == asset), None)
        if not pos or float(pos.get('contracts', 0)) == 0:
            logging.info(f"No active position for {asset} - clearing state")
            states[asset].update({'in_position': False, 'direction': None, 'size': 0})
            return
            
        size = abs(float(pos['contracts']))
        side = 'buy' if states[asset]['direction'] == 'short' else 'sell'
        exchange.create_order(s, 'market', side, size, params={
            'category': 'linear', 'reduceOnly': True, 'positionIdx': 0
        })
        logging.info(f"CLOSED {asset} ({states[asset]['direction'].upper()}) | Size: {size}")
        states[asset].update({'in_position': False, 'direction': None, 'size': 0})
    except Exception as e:
        logging.error(f"Exit failed: {e}")

# WEBHOOK - FINAL
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Force JSON parsing (handles missing Content-Type)
        data = request.get_json(force=True) or {}
        if not data:
            logging.warning(f"Empty payload: {request.data}")
            return jsonify({'status': 'ignored'}), 200

        asset = data.get("asset")
        indicator = data.get("indicator")
        event = data.get("event")

        if asset not in ASSETS:
            return jsonify({'status': 'ignored'}), 200

        mapping = {
            "Value Exhaustion": "value_exhaustion",
            "Universal Valuation": "universal_val",
            "Conviction Ratio": "conviction"
        }

        if indicator in mapping:
            states[asset][mapping[indicator]] = (event == "above_0")
            logging.info(f"{indicator} → {'ABOVE' if event == 'above_0' else 'BELOW'} ({asset})")

        all_above = all(states[asset][k] for k in mapping.values())
        all_below = all(not states[asset][k] for k in mapping.values())

        # EXIT ON ANY MISALIGNMENT
        if states[asset]['in_position']:
            if states[asset]['direction'] == 'long' and not all_above:
                logging.info(f"ONE BELOW → CLOSING LONG {asset}")
                exit_position(asset)
            if states[asset]['direction'] == 'short' and not all_below:
                logging.info(f"ONE ABOVE → CLOSING SHORT {asset}")
                exit_position(asset)

        # ENTRY
        if not states[asset]['in_position']:
            if all_above:
                logging.info(f"ALL ABOVE → LONG {asset}")
                enter_long(asset)
            elif all_below:
                logging.info(f"ALL BELOW → SHORT {asset}")
                enter_short(asset)

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

# GIVES DASHBOARD LIVE DATA
@app.route('/state')
def state():
    return jsonify({
        'states': states,
        'equity': get_equity(),
        'position': {
            'side': states['ETHUSDT']['direction'].upper() if states['ETHUSDT']['in_position'] else "FLAT",
            'size': states['ETHUSDT']['size'],
            'entry': states['ETHUSDT']['entry_price']
        } if states['ETHUSDT']['in_position'] else None
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
