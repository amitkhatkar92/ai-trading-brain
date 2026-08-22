"""
P2 debug v2: get the actual traceback by monkey-patching _live_history.
"""
import sys
sys.path.insert(0, "/app")

import traceback as tb_mod

from data_feeds import yahoo_feed as yf_mod

_original = yf_mod.YahooFeed._live_history

def _patched_live_history(self, ticker, alias, days, interval):
    try:
        import yfinance as yf
        import math
        period = f"{days}d" if days <= 60 else f"{days // 30}mo"
        df = yf.download(
            ticker, period=period, interval=interval,
            auto_adjust=True, progress=False, threads=False,
        )
        if df.empty:
            return self._sim_history(alias, days)

        df = self._normalize_df_columns(df)

        from data_feeds.base_feed import PriceBar
        from utils.safe_scalar import safe_scalar
        bars = []
        for ts, row in df.iterrows():
            try:
                _open   = safe_scalar(row.get("Open",   row.get("open",   0.0)), 0.0)
                _high   = safe_scalar(row.get("High",   row.get("high",   0.0)), 0.0)
                _low    = safe_scalar(row.get("Low",    row.get("low",    0.0)), 0.0)
                _close  = safe_scalar(row.get("Close",  row.get("close",  0.0)), 0.0)
                _volume = safe_scalar(row.get("Volume", row.get("volume", 0.0)), 0.0)
            except Exception as row_exc:
                print(f"[ROW ERROR] {ticker} ts={ts}: {row_exc}")
                tb_mod.print_exc()
                continue
            bars.append(PriceBar(
                symbol=alias, timestamp=ts.to_pydatetime(),
                open=_open, high=_high, low=_low, close=_close,
                volume=_volume, interval=interval,
            ))
        return bars
    except Exception as exc:
        print(f"[OUTER ERROR] {ticker}: {exc}")
        tb_mod.print_exc()
        return self._sim_history(alias, days)

yf_mod.YahooFeed._live_history = _patched_live_history

# Now test
from data_feeds.yahoo_feed import YahooFeed
feed = YahooFeed()
bars = feed.get_history("COALINDIA.NS", 30, "1d")
print(f"COALINDIA bars: {len(bars)}, first close: {bars[0].close if bars else 'N/A'}")
