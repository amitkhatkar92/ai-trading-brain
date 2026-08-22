"""
P2 debug v5: intercept the exception with full traceback at the source.
Monkey-patch _live_history to get the actual stack.
"""
import sys, traceback as tb
sys.path.insert(0, "/app")

# Patch before import
import data_feeds.yahoo_feed

original = data_feeds.yahoo_feed.YahooFeed._live_history

def patched(self, ticker, alias, days, interval):
    try:
        import yfinance as yf
        period = f"{days}d" if days <= 60 else f"{days // 30}mo"
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False, threads=False)
        if df.empty:
            return self._sim_history(alias, days)
        df = self._normalize_df_columns(df)
        from data_feeds.base_feed import PriceBar
        from utils.safe_scalar import safe_scalar
        bars = []
        for ts, row in df.iterrows():
            bars.append(PriceBar(
                symbol=alias, timestamp=ts.to_pydatetime(),
                open=safe_scalar(row.get("Open", row.get("open", 0.0)), 0.0),
                high=safe_scalar(row.get("High", row.get("high", 0.0)), 0.0),
                low=safe_scalar(row.get("Low", row.get("low", 0.0)), 0.0),
                close=safe_scalar(row.get("Close", row.get("close", 0.0)), 0.0),
                volume=safe_scalar(row.get("Volume", row.get("volume", 0.0)), 0.0),
                interval=interval,
            ))
        try:
            from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit
            _gdit().record_refresh_success(alias.replace(".NS", ""))
        except Exception:
            pass
        return bars
    except Exception as exc:
        # FULL TRACEBACK
        print(f"\n=== FULL TRACEBACK for {ticker} ===")
        tb.print_exc()
        print("===\n")
        try:
            from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit
            _gdit().record_corruption(
                symbol=alias.replace(".NS", ""), indicator="ohlcv_history",
                corruption_type=f"{type(exc).__name__}:{str(exc)[:80]}",
                fallback_used=True,
            )
        except Exception:
            pass
        import logging
        logging.getLogger("data_feeds.yahoo_feed").debug(
            "[YahooFeed] history %s failed: %s — using sim", ticker, exc)
        return self._sim_history(alias, days)
    finally:
        self._yf_close_caches()

data_feeds.yahoo_feed.YahooFeed._live_history = patched

# Now run the actual scan to trigger the RSI refresh
from opportunity_engine.equity_scanner_ai import get_live_watchlist
import time
print("Triggering scan...")
result = get_live_watchlist()
print(f"Scan done: {len(result)} candidates")
time.sleep(5)
print("Done")
