"""
P2 debug: reproduce the float(Series) error in _live_history.
Run inside the container to get a proper traceback.
"""
import traceback
import logging
logging.basicConfig(level=logging.DEBUG)

import sys
sys.path.insert(0, "/app")

from data_feeds.yahoo_feed import YahooFeed

feed = YahooFeed()

# Override the log handler to capture the full exception
import data_feeds.yahoo_feed as yf_mod
orig_live_history = feed._live_history

def patched_live_history(ticker, alias, days, interval):
    try:
        import yfinance as yf
        period = f"{days}d" if days <= 60 else f"{days // 30}mo"
        df = yf.download(
            ticker, period=period, interval=interval,
            auto_adjust=True, progress=False, threads=False,
        )
        print(f"[DEBUG] {ticker}: df.shape={df.shape}, df.columns={list(df.columns)[:5]}")
        print(f"[DEBUG] column type: {type(df.columns)}")
        if not df.empty:
            row = df.iloc[-1]
            print(f"[DEBUG] row type: {type(row)}, row.index type: {type(row.index)}")
            # Try safe_scalar
            from utils.safe_scalar import safe_scalar
            close = row.get("Close", row.get("close", 0.0))
            print(f"[DEBUG] close type: {type(close)}, value: {close}")
            print(f"[DEBUG] safe_scalar(close): {safe_scalar(close, 0.0)}")
    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        traceback.print_exc()

try:
    patched_live_history("COALINDIA.NS", "COALINDIA", 30, "1d")
    patched_live_history("WIPRO.NS", "WIPRO", 30, "1d")
except Exception as e:
    print(f"Top-level error: {e}")
    traceback.print_exc()
