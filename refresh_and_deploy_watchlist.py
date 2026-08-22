"""
Auto-refresh: fetches fresh RSI/ATR/S/R/ADV from yfinance and rewrites
_BASE_WATCHLIST + _EXTENDED_WATCHLIST in equity_scanner_ai.py in-place.

Also updates the last_level_update= date in the [ScannerBaseline] log.info().
"""
import yfinance as yf
import pandas as pd
import numpy as np
import re, ast, sys, shutil
from pathlib import Path
from datetime import datetime, timezone

SCANNER = Path("/app/opportunity_engine/equity_scanner_ai.py")
BACKUP  = Path("/app/opportunity_engine/equity_scanner_ai_backup_20260529.py")
TODAY   = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        (low - close.shift(1)).abs(),
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
                print(f"  SKIP {sym}: only {len(close)} days")
                continue
            rsi   = round(float(compute_rsi(close).iloc[-1]), 1)
            atr14 = float(compute_atr(high, low, close).iloc[-1])
            ltp   = round(float(close.iloc[-1]), 2)
            w20 = close.iloc[-20:]
            support    = round(float(w20.min()), 2)
            resistance = round(float(w20.max()), 2)
            proxy_atr  = (resistance - support) * 0.40
            divergence = abs(proxy_atr - atr14) / atr14 if atr14 > 0 else 0
            adj_flag   = ""
            if divergence > 0.40:
                support    = round(ltp - atr14 * 2.5, 2)
                resistance = round(ltp + atr14 * 2.5, 2)
                adj_flag   = "  # ATR_ANCHORED"
            avg_vol    = float(vol.iloc[-20:].mean())
            recent_vol = float(vol.iloc[-3:].mean())
            vol_ratio  = round(min(max(recent_vol / avg_vol if avg_vol > 0 else 1.0, 0.5), 5.0), 1)
            adv_crore  = max(int(round(float((close.iloc[-20:] * vol.iloc[-20:]).mean()) / 1e7, 0)), 1)
            results[sym] = dict(
                ltp=ltp, rsi=rsi, support=support, resistance=resistance,
                vol_ratio=vol_ratio, adv_crore=adv_crore, atr14=round(atr14, 2),
                adj=adj_flag, div=round(divergence * 100, 1),
            )
        except Exception as exc:
            print(f"  ERROR {sym}: {exc}")
    return results


def build_watchlist_str(label, symbols, results):
    lines = [
        f"# ── {label} ─────────────────────────────────────────────────────────",
        f"    # base_ltp refreshed {TODAY} from yfinance live close prices",
        f"    # ATR_ANCHORED = 20d range diverged >40% from ATR(14); levels rebuilt from real ATR",
    ]
    for sym in symbols:
        r = results.get(sym)
        if r is None:
            lines.append(f"    # MISSING: {sym}")
            continue
        lines.append(
            f'    {{"symbol": "{sym:<12}", "base_ltp": {r["ltp"]:>8.2f}, '
            f'"resistance": {r["resistance"]:>8.2f}, "support": {r["support"]:>8.2f}, '
            f'"volume_ratio": {r["vol_ratio"]:.1f}, "rsi": {r["rsi"]:>5.1f}, '
            f'"adv_crore": {r["adv_crore"]:>5d}}},{r["adj"]}'
        )
    return "\n".join(lines)


# ── Regex helpers to replace the watchlist blocks in the source ──────────────

def replace_watchlist_block(src, var_name, new_inner):
    """Replace everything between the opening '[' and closing ']' of var_name's list."""
    # Match: _BASE_WATCHLIST... = [    or   _EXTENDED_WATCHLIST... = [
    pat = re.compile(
        rf"({re.escape(var_name)}[^=]+=\s*\[)"
        r"([\s\S]*?)"
        r"(^\])",
        re.MULTILINE,
    )
    def replacer(m):
        return m.group(1) + "\n" + new_inner + "\n" + m.group(3)
    new_src, count = pat.subn(replacer, src)
    if count == 0:
        raise ValueError(f"Could not find/replace {var_name} block")
    return new_src


# ── Main ─────────────────────────────────────────────────────────────────────

print(f"Fetching data for {len(SYMBOLS_BASE)} base symbols...")
res_base = fetch_and_compute(SYMBOLS_BASE)
print(f"Fetching data for {len(SYMBOLS_EXT)} extended symbols...")
res_ext  = fetch_and_compute(SYMBOLS_EXT)

# Print summary
print("\n=== FRESH DATA SUMMARY ===")
print(f"{'Symbol':<14} {'LTP':>9} {'Resist':>9} {'Support':>9} {'RSI':>6} {'Vol':>5} {'ADV':>5}  Notes")
for sym in SYMBOLS_BASE + SYMBOLS_EXT:
    r = (res_base | res_ext).get(sym)
    if r:
        atag = " ATR_ANCHORED" if r["adj"] else ""
        print(f"  {sym:<12} {r['ltp']:>9.2f} {r['resistance']:>9.2f} {r['support']:>9.2f} "
              f"{r['rsi']:>6.1f} {r['vol_ratio']:>5.1f} {r['adv_crore']:>5d}{atag}")

# Detect level issues (LTP vs S/R)
print("\n=== LEVEL SANITY (crossed levels) ===")
issues = []
for sym in SYMBOLS_BASE + SYMBOLS_EXT:
    r = (res_base | res_ext).get(sym)
    if not r:
        continue
    ltp, res, sup = r["ltp"], r["resistance"], r["support"]
    if ltp > res:
        issues.append(f"  {sym}: LTP {ltp} > resistance {res}  ← price broke out above old resistance")
    if ltp < sup:
        issues.append(f"  {sym}: LTP {ltp} < support {sup}  ← price broke below old support")
if issues:
    for i in issues:
        print(i)
else:
    print("  All levels OK after refresh.")

# ── Backup and rewrite scanner file ─────────────────────────────────────────
shutil.copy2(SCANNER, BACKUP)
print(f"\nBackup saved: {BACKUP}")

src = SCANNER.read_text(encoding="utf-8")

# Build new list bodies (just the content between [ and ])
base_inner = build_watchlist_str("Base watchlist", SYMBOLS_BASE, res_base)
ext_inner  = build_watchlist_str("Extended watchlist", SYMBOLS_EXT, res_ext)

# Replace each block
src = replace_watchlist_block(src, "_BASE_WATCHLIST", base_inner)
src = replace_watchlist_block(src, "_EXTENDED_WATCHLIST", ext_inner)

# Update last_level_update date in log.info
src = re.sub(r"last_level_update=\d{4}-\d{2}-\d{2}", f"last_level_update={TODAY}", src)

SCANNER.write_text(src, encoding="utf-8")
print(f"Wrote updated watchlist to {SCANNER}")
print(f"last_level_update updated to {TODAY}")

# Verify
print("\n=== VERIFICATION (grep of refreshed comment) ===")
for line in src.splitlines():
    if "base_ltp refreshed" in line and "2026" in line:
        print(f"  {line.strip()}")
        break

print("\nDone. Watchlist refreshed and deployed.")
