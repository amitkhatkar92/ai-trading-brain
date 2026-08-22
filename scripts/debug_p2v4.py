"""
P2 debug v4: reproduce with concurrent yf.download calls (simulating RSI refresh + price refresh overlap).
"""
import sys, threading, traceback
sys.path.insert(0, "/app")

errors = []

def download_history(symbol):
    """Simulates _live_history."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period="22d", interval="1d",
                         auto_adjust=True, progress=False, threads=False)
        if df.empty:
            return

        from data_feeds.yahoo_feed import YahooFeed
        df = YahooFeed._normalize_df_columns(df)

        from utils.safe_scalar import safe_scalar
        from data_feeds.base_feed import PriceBar
        bars = []
        for ts, row in df.iterrows():
            bars.append(PriceBar(
                symbol=symbol.replace(".NS",""),
                timestamp=ts.to_pydatetime(),
                open=safe_scalar(row.get("Open", row.get("open", 0.0)), 0.0),
                high=safe_scalar(row.get("High", row.get("high", 0.0)), 0.0),
                low=safe_scalar(row.get("Low", row.get("low", 0.0)), 0.0),
                close=safe_scalar(row.get("Close", row.get("close", 0.0)), 0.0),
                volume=safe_scalar(row.get("Volume", row.get("volume", 0.0)), 0.0),
                interval="1d",
            ))
        if bars:
            closes = [float(b.close) for b in bars
                      if hasattr(b, 'close') and b.close and b.close > 0
                      and isinstance(b.close, (int, float))]
            print(f"OK {symbol}: {len(bars)} bars, {len(closes)} closes")
    except Exception as e:
        print(f"ERROR {symbol}: {e}")
        traceback.print_exc()
        errors.append((symbol, str(e)))

# Sequential test
print("=== Sequential test ===")
for sym in ["COALINDIA.NS", "WIPRO.NS", "HDFCBANK.NS"]:
    download_history(sym)

# Concurrent test (3 threads)
print("\n=== Concurrent test (3 threads) ===")
threads = []
for sym in ["AMBUJACEM.NS", "BAJAJ-AUTO.NS", "ASTRAL.NS"]:
    t = threading.Thread(target=download_history, args=(sym,), daemon=True)
    threads.append(t)
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=30)

print(f"\nTotal errors: {len(errors)}")
for sym, err in errors:
    print(f"  {sym}: {err}")
