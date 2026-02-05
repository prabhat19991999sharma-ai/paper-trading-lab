import os
import time
import json
import logging
import requests
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# Constants
INGEST_URL = "http://127.0.0.1:8000/api/ingest/tick"
WATCHLIST_URL = "http://127.0.0.1:8000/api/watchlist"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("angel_bridge")

# Credentials from Env
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_KEY = os.getenv("ANGEL_TOTP_KEY")

if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_KEY]):
    logger.error("Missing Credentials. Set ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_KEY")
    exit(1)

# Token Map (Simplified for Demo - in prod, download full scrip master)
# You can add more manually here or implement dynamic lookup
TOKEN_MAP = {
    "RELIANCE": {"token": "2885", "exch": "nse_cm"},
    "TCS": {"token": "11536", "exch": "nse_cm"},
    "INFY": {"token": "1594", "exch": "nse_cm"},
    "HDFC": {"token": "1330", "exch": "nse_cm"},
    "HDFCBANK": {"token": "1333", "exch": "nse_cm"},
    "SBIN": {"token": "3045", "exch": "nse_cm"},
    "HINDALCO": {"token": "1363", "exch": "nse_cm"},
    "TITAN": {"token": "3506", "exch": "nse_cm"},
    "AXISBANK": {"token": "5900", "exch": "nse_cm"},
    "ICICIBANK": {"token": "4963", "exch": "nse_cm"},
    "VOLTAS": {"token": "3718", "exch": "nse_cm"},
    "IRCTC": {"token": "13611", "exch": "nse_cm"},
    "ONGC": {"token": "2475", "exch": "nse_cm"},
     # Add others as needed. The bridge will warn if a symbol is missing.
}

def get_watchlist():
    try:
        resp = requests.get(WATCHLIST_URL)
        return resp.json().get("symbols", [])
    except Exception as e:
        logger.error(f"Failed to fetch watchlist: {e}")
        return []

def get_auth_token():
    smartApi = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_KEY).now()
    data = smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
    if not data['status']:
        logger.error(f"Login failed: {data['message']}")
        return None, None
    
    return data['data']['jwtToken'], data['data']['feedToken']

def on_data(wsapp, msg):
    #logger.info(f"Ticks: {msg}")
    # Msg is usually a bytearray or list of dicts if parsed by library? 
    # SmartWebSocketV2 returns python dicts directly in newer versions check docs
    # Actually based on library source, it calls parse_binary_data internal or returns dict
    # We assume 'msg' is the parsed dictionary
    
    if "last_traded_price" in msg and "token" in msg:
        price = float(msg.get("last_traded_price", 0))
        vol = float(msg.get("vol_traded", 0))
        token = msg.get("token").replace('"', '') # sometimes token has quotes
        
        # Reverse lookup symbol
        symbol = None
        for sym, meta in TOKEN_MAP.items():
            if meta["token"] == token:
                symbol = sym
                break
        
        if symbol:
            payload = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "price": price,
                "volume": vol
            }
            try:
                requests.post(INGEST_URL, json=payload, timeout=0.5)
                # print(f"-> {symbol}: {price}")
            except:
                pass

def on_open(wsapp):
    logger.info("Socket Opened")

def on_error(wsapp, error):
    logger.error(f"Socket Error: {error}")

def main():
    jwt, feed_token = get_auth_token()
    if not jwt:
        return

    sws = SmartWebSocketV2(jwt, API_KEY, CLIENT_ID, feed_token)
    
    # 1. Get Symbols we want to watch
    wanted = get_watchlist()
    logger.info(f"Watchlist: {wanted}")
    
    # 2. Build Token List
    token_list = []
    
    for sym in wanted:
        if sym in TOKEN_MAP:
            # Mode: 1=LTP, 2=Quote, 3=SnapQuote
            # For data feed, use Mode 1 (LTP) or Mode 3 (Full)
            token_list.append({
                "exchangeType": 1, # NSE_CM
                "tokens": [TOKEN_MAP[sym]["token"]]
            })
        else:
            logger.warning(f"Symbol {sym} not in local map. defaulting to ignore. (Edit scripts/angel_bridge.py to add it)")

    if not token_list:
        logger.error("No valid tokens found to track.")
        return

    # 3. Subscribe
    # Note: SmartAPI requires distinct correlationID per request
    correlation_id = "stream_1"
    action = 1 # 1=Subscribe, 0=Unsubscribe
    mode = 3 # Mode 3 = Full Quote (Open, High, Low, Close, LTP)
    
    sws.subscribe(correlation_id, mode, token_list)
    
    # Assign callbacks
    sws.on_data = on_data
    sws.on_open = on_open
    sws.on_error = on_error
    
    logger.info("Starting WebSocket connection...")
    sws.connect()

if __name__ == "__main__":
    main()
