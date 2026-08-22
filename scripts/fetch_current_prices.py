"""
Fetch current NSE prices for all _BASE_WATCHLIST symbols from yfinance.
Output: a ready-to-paste Python dict of {symbol: round(close, 2)}.
"""
import yfinance as yf
from datetime import datetime, timedelta

# All symbols from equity_scanner_ai._BASE_WATCHLIST
SYMBOLS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "HINDUNILVR",
    "LT", "SBIN", "BAJFINANCE", "KOTAKBANK", "BHARTIARTL", "AXISBANK",
    "ASIANPAINT", "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "WIPRO",
    "NESTLEIND", "TECHM", "HCLTECH", "BAJAJFINSV", "M&M", "ONGC",
    "NTPC", "POWERGRID", "TATAMOTORS", "TATASTEEL", "JSWSTEEL", "COALINDIA",
    "HINDALCO", "GRASIM", "DRREDDY", "DIVISLAB", "ADANIENT", "ADANIPORTS",
    "TATACONSUM", "ITC", "BANKBARODA", "HAVELLS", "PIDILITIND", "BRITANNIA",
]

ns_syms = [s + ".NS" for s in SYMBOLS]

try:
    df = yf.download(ns_syms, period="2d", interval="1d", progress=False)
    closes = df["Close"].iloc[-1]  # most recent close
    print("PRICES = {")
    for sym in SYMBOLS:
        ns = sym + ".NS"
        val = closes.get(ns)
        if val and val > 0:
            print(f'    "{sym}": {round(float(val), 2)},')
        else:
            print(f'    # "{sym}": NO_DATA,')
    print("}")
except Exception as e:
    print(f"Error: {e}")
    # Try individually on failure
    for sym in SYMBOLS:
        try:
            t = yf.Ticker(sym + ".NS")
            p = t.fast_info.get("last_price") or t.fast_info.get("regularMarketPrice")
            if p:
                print(f'    "{sym}": {round(float(p), 2)},')
            else:
                print(f'    # "{sym}": NO_DATA')
        except Exception as e2:
            print(f'    # "{sym}": ERROR {e2}')
