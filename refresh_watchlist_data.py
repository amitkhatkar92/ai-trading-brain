"""
Phase 0 — Emergency Watchlist Data Refresh
Fetches current RSI(14), ATR(14), support/resistance, volume_ratio, adv_crore
for all watchlist symbols from yfinance. Run once, paste output into equity_scanner_ai.py.
"""
import yfinance as yf
import pandas as pd
import numpy as np


SYMBOLS_BASE = [
    "RELIANCE","HDFCBANK","ICICIBANK","TATASTEEL","INFY","BANKBARODA",
    "LT","COALINDIA","HCLTECH","SBIN","AXISBANK","ONGC","KOTAKBANK",
    "BHARTIARTL","ITC","BAJAJFINSV","HINDALCO","ULTRACEMCO","TECHM","NTPC",
]
SYMBOLS_EXT = [
    "HINDUNILVR","ASIANPAINT","BAJFINANCE","MARUTI","SUNPHARMA","WIPRO",
    "POWERGRID","DIVISLAB","TITAN","DRREDDY","ADANIENT","TATACONSUM",
    "NESTLEIND","HAVELLS","PIDILITIND","GRASIM","JSWSTEEL","ADANIPORTS",
]


def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def fetch_and_compute(symbols):
    tickers = [s + ".NS" for s in symbols]
    data = yf.download(tickers, period="35d", interval="1d",
                       progress=False, auto_adjust=True)
    results = {}
    for sym in symbols:
        ns = sym + ".NS"
        try:
            close = data["Close"][ns].dropna()
            high  = data["High"][ns].dropna()
            low   = data["Low"][ns].dropna()
            vol   = data["Volume"][ns].dropna()

            if len(close) < 15:
                print(f"  SKIP {sym}: only {len(close)} days of data")
                continue

            rsi   = round(float(compute_rsi(close).iloc[-1]), 1)
            atr14 = float(compute_atr(high, low, close).iloc[-1])
            ltp   = round(float(close.iloc[-1]), 2)

            # 20-day range for support / resistance
            w20 = close.iloc[-20:]
            support    = round(float(w20.min()), 2)
            resistance = round(float(w20.max()), 2)

            # ATR proxy vs real ATR divergence check
            proxy_atr  = (resistance - support) * 0.40
            divergence = abs(proxy_atr - atr14) / atr14 if atr14 > 0 else 0
            adj_flag   = ""
            if divergence > 0.40:
                # Anchor levels to real ATR so _estimate_atr() stays accurate
                support    = round(ltp - atr14 * 2.5, 2)
                resistance = round(ltp + atr14 * 2.5, 2)
                adj_flag   = "  # ATR_ANCHORED"

            # Volume ratio: 3-day avg vs 20-day avg (smoothed)
            avg_vol   = float(vol.iloc[-20:].mean())
            recent_vol = float(vol.iloc[-3:].mean())
            vol_ratio = round(
                min(max(recent_vol / avg_vol if avg_vol > 0 else 1.0, 0.5), 5.0), 1
            )

            # ADV in crore: avg(close * volume) / 10_000_000
            adv_crore = int(round(
                float((close.iloc[-20:] * vol.iloc[-20:]).mean()) / 1e7, 0
            ))
            adv_crore = max(adv_crore, 1)  # floor at 1

            results[sym] = dict(
                ltp=ltp, rsi=rsi, support=support, resistance=resistance,
                vol_ratio=vol_ratio, adv_crore=adv_crore,
                atr14=round(atr14, 2), adj=adj_flag,
                divergence_pct=round(divergence * 100, 1),
            )
        except Exception as exc:
            print(f"  ERROR {sym}: {exc}")
    return results


def print_watchlist_dict(label, symbols, results):
    print(f"\n# ── {label} ─────────────────────────────────────────────────────────")
    print(f"# base_ltp refreshed {pd.Timestamp.now().strftime('%Y-%m-%d')} from yfinance live close prices")
    for sym in symbols:
        r = results.get(sym)
        if r is None:
            print(f"  # MISSING: {sym}")
            continue
        print(
            f'    {{"symbol": "{sym:12s}", "base_ltp": {r["ltp"]:8.2f}, '
            f'"resistance": {r["resistance"]:8.2f}, "support": {r["support"]:8.2f}, '
            f'"volume_ratio": {r["vol_ratio"]:.1f}, "rsi": {r["rsi"]:5.1f}, '
            f'"adv_crore": {r["adv_crore"]:5d}}},{r["adj"]}'
        )


def print_summary(symbols, results):
    print("\n# ── ATR divergence report ──────────────────────────────────────────")
    for sym in symbols:
        r = results.get(sym)
        if r:
            flag = " *** ANCHORED" if r["adj"] else ""
            print(
                f"  {sym:15s}  ltp={r['ltp']:8.2f}  rsi={r['rsi']:5.1f}"
                f"  atr14={r['atr14']:6.2f}  vol={r['vol_ratio']:.1f}x"
                f"  adv={r['adv_crore']:5d}cr  div={r['divergence_pct']:5.1f}%{flag}"
            )


if __name__ == "__main__":
    print("Fetching base watchlist symbols...")
    res_base = fetch_and_compute(SYMBOLS_BASE)
    print("Fetching extended watchlist symbols...")
    res_ext  = fetch_and_compute(SYMBOLS_EXT)
    all_results = {**res_base, **res_ext}

    print_summary(SYMBOLS_BASE + SYMBOLS_EXT, all_results)
    print_watchlist_dict("Base watchlist", SYMBOLS_BASE, res_base)
    print_watchlist_dict("Extended watchlist", SYMBOLS_EXT, res_ext)
    print("\nDone. Paste the above dicts into equity_scanner_ai.py to replace the hardcoded levels.")
