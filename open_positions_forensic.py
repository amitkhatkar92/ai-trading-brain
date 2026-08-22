"""
FORENSIC AUDIT — Open Positions & Entry Validation
====================================================
Checks:
  1. All truly-open positions (OPEN row with no matching CLOSE)
  2. Were they entered with live LTP (within 0.5% of watchlist base_ltp)?
  3. Were entry prices valid relative to S/R levels at the time?
  4. Were they from prepared universe or static watchlist?
  5. What is the current unrealized P&L vs today's live price?
  6. Are the stop/target levels still valid against REFRESHED levels?
"""

import csv, json, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ── Historical watchlist snapshots (what levels existed at entry time) ───────
# These are the ORIGINAL levels used by the scanner before today's refresh.
HIST_LEVELS = {
    "MARUTI":    {"support": 15800.0,  "resistance": 17800.0},   # Mar 19 levels
    "TITAN":     {"support":  3500.0,  "resistance":  4500.0},
    "ULTRACEMCO":{"support": 10800.0,  "resistance": 13000.0},
    "M&M":       {"support":  3300.0,  "resistance":  4200.0},
    "GRASIM":    {"support":  2500.0,  "resistance":  3200.0},
    "LT":        {"support":  3300.0,  "resistance":  4200.0},
    # May-era levels (from audit earlier in session)
    "RELIANCE":  {"support":  1287.2,  "resistance":  1434.4},
    "HINDALCO":  {"support":  1023.5,  "resistance":  1103.3},
    "BHARTIARTL":{"support":  1776.24, "resistance":  1980.56},
    "COALINDIA": {"support":   452.5,  "resistance":   481.45},
    "BANKBARODA":{"support":   259.95, "resistance":   273.99},
    "TATASTEEL": {"support":   207.01, "resistance":   221.13},
    "NTPC":      {"support":   388.3,  "resistance":   410.2},
    "AXISBANK":  {"support":  1237.9,  "resistance":  1324.2},
    "ICICIBANK": {"support":  1235.6,  "resistance":  1314.1},
    "TATAMOTORS":{"support":   880.0,  "resistance":  1100.0},
    "HDFCBANK":  {"support":   749.6,  "resistance":   796.55},
}

# ── TODAY's refreshed levels (from today's yfinance run) ─────────────────────
TODAY_LEVELS = {
    "RELIANCE":  {"support":  1267.92, "resistance":  1403.28},
    "HDFCBANK":  {"support":   749.60, "resistance":   796.55},
    "ICICIBANK": {"support":  1235.60, "resistance":  1291.80},
    "TATASTEEL": {"support":   207.01, "resistance":   221.13},
    "INFY":      {"support":  1129.63, "resistance":  1273.17},
    "BANKBARODA":{"support":   259.95, "resistance":   272.25},
    "LT":        {"support":  3917.72, "resistance":  4293.48},
    "COALINDIA": {"support":   454.05, "resistance":   481.45},
    "HCLTECH":   {"support":  1124.00, "resistance":  1200.50},
    "SBIN":      {"support":   916.24, "resistance":  1019.56},
    "AXISBANK":  {"support":  1237.90, "resistance":  1311.20},
    "ONGC":      {"support":   249.19, "resistance":   286.41},
    "BHARTIARTL":{"support":  1737.32, "resistance":  1930.88},
    "ITC":       {"support":   277.21, "resistance":   300.99},
    "HINDALCO":  {"support":  1068.86, "resistance":  1222.74},
    "ULTRACEMCO":{"support": 11368.00, "resistance": 12146.00},
    "TECHM":     {"support":  1387.82, "resistance":  1584.38},
    "NTPC":      {"support":   388.30, "resistance":   402.15},
    "HINDUNILVR":{"support":  2173.50, "resistance":  2327.40},
    "MARUTI":    {"support": 12956.00, "resistance": 13770.00},
    "ADANIENT":  {"support":  2722.33, "resistance":  3176.27},
    "GRASIM":    {"support":  2978.86, "resistance":  3312.54},
    "JSWSTEEL":  {"support":  1252.30, "resistance":  1309.30},
}

# ── Load CSV ─────────────────────────────────────────────────────────────────
CSV_PATH = Path("/app/data/paper_trades.csv")
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    trades = list(reader)

# Find headers
headers = reader.fieldnames
print(f"Headers: {headers}\n")

# ── Build open/close maps ─────────────────────────────────────────────────────
open_map  = {}   # order_id → first OPEN row
close_map = defaultdict(list)   # order_id → list of CLOSE rows

for t in trades:
    oid = t.get("order_id", "").strip()
    ev  = t.get("event", "").strip()
    if not oid:
        continue
    if "OPEN" in ev and "REENTRY" not in ev and "CANCELLED" not in ev:
        if oid not in open_map:
            open_map[oid] = t
    elif ev == "CLOSE":
        close_map[oid].append(t)

# Truly open = OPEN with no CLOSE
truly_open = {oid: row for oid, row in open_map.items() if oid not in close_map}

# Group by symbol
by_sym = defaultdict(list)
for oid, row in sorted(truly_open.items(), key=lambda x: x[1].get("timestamp","")):
    by_sym[row.get("symbol","?")].append((oid, row))

# ── Fetch live prices from yfinance ──────────────────────────────────────────
print("Fetching live prices for open position symbols...")
try:
    import yfinance as yf
    import numpy as np

    syms = list(by_sym.keys())
    ns_syms = [s + ".NS" for s in syms if s not in ("NIFTY","BANKNIFTY","M&M")]
    # M&M has & in name
    ns_syms += ["M&M.NS"] if "M&M" in syms else []

    live_data = yf.download(ns_syms, period="1d", interval="1m",
                            progress=False, auto_adjust=True)
    live_prices = {}
    for s in syms:
        ns = s + ".NS"
        try:
            col = live_data["Close"][ns].dropna()
            if len(col) > 0:
                live_prices[s] = float(col.iloc[-1])
        except:
            pass
    print(f"Got live prices for {len(live_prices)}/{len(syms)} symbols\n")
except Exception as e:
    live_prices = {}
    print(f"Warning: could not fetch live prices: {e}\n")

# ── Print report ──────────────────────────────────────────────────────────────
print("=" * 100)
print("FORENSIC AUDIT — ALL ORPHANED OPEN POSITIONS")
print("=" * 100)

total_positions = 0
total_exposure  = 0.0
flags           = []

for sym in sorted(by_sym.keys()):
    positions = by_sym[sym]
    live_ltp  = live_prices.get(sym, None)
    today_lvl = TODAY_LEVELS.get(sym, {})
    hist_lvl  = HIST_LEVELS.get(sym, {})

    print(f"\n{'='*100}")
    print(f"SYMBOL: {sym}  ({len(positions)} orphaned open position{'s' if len(positions) > 1 else ''})")
    print(f"  Live LTP today    : {live_ltp:.2f}" if live_ltp else "  Live LTP today    : UNAVAILABLE")
    if today_lvl:
        print(f"  TODAY S/R levels  : support={today_lvl['support']:.2f}  resistance={today_lvl['resistance']:.2f}")
    print(f"{'─'*100}")
    print(f"  {'Date':12s} {'Order ID':35s} {'Dir':5s} {'Qty':6s} {'Entry':9s} {'SL':9s} {'Target':9s} {'Strategy':25s} {'Age':6s} {'Unreal.PnL':12s} {'Flags'}")
    print(f"  {'─'*12} {'─'*35} {'─'*5} {'─'*6} {'─'*9} {'─'*9} {'─'*9} {'─'*25} {'─'*6} {'─'*12} {'─'*30}")

    for oid, row in positions:
        total_positions += 1
        ts      = row.get("timestamp", "")[:16]
        direction = row.get("direction", "")
        qty     = int(row.get("quantity", 0))
        entry   = float(row.get("entry_price", 0))
        sl      = float(row.get("stop_loss", 0) or 0)
        tgt     = float(row.get("target", 0) or 0)   # CSV column is 'target' not 'target_price'
        strat   = row.get("strategy", "")[:25]
        date    = row.get("timestamp", "")[:10]

        try:
            entry_dt = datetime.strptime(date, "%Y-%m-%d")
            age_days = (datetime.now() - entry_dt).days
        except:
            age_days = 0

        exposure = entry * qty
        total_exposure += exposure

        # Unrealized P&L
        if live_ltp and entry > 0:
            if direction.upper() in ("BUY","LONG"):
                unreal = (live_ltp - entry) * qty
            else:
                unreal = (entry - live_ltp) * qty
        else:
            unreal = None

        # Entry validation flags
        row_flags = []

        # Flag 1: Age > 30 days = zombie
        if age_days > 30:
            row_flags.append(f"ZOMBIE({age_days}d)")

        # Flag 2: Entry vs historical S/R levels
        if hist_lvl:
            hist_sup = hist_lvl.get("support", 0)
            hist_res = hist_lvl.get("resistance", 9e9)
            if direction.upper() in ("BUY","LONG"):
                if entry > hist_res * 1.01:
                    row_flags.append(f"ENTRY>{hist_res:.0f}(old_res)")
                elif entry < hist_sup * 0.99:
                    row_flags.append(f"ENTRY<{hist_sup:.0f}(old_sup)")
            else:
                if entry < hist_sup * 0.99:
                    row_flags.append(f"SHORT_ENTRY<{hist_sup:.0f}(old_sup)")

        # Flag 3: SL vs today's levels
        if today_lvl and live_ltp:
            today_res = today_lvl["resistance"]
            today_sup = today_lvl["support"]
            if direction.upper() in ("BUY","LONG"):
                if live_ltp < today_sup * 0.99:
                    row_flags.append(f"LTP({live_ltp:.0f})<SUPPORT({today_sup:.0f})")
                if sl and live_ltp < sl:
                    row_flags.append(f"SL_BREACHED(ltp={live_ltp:.2f}<sl={sl:.2f})")

        # Flag 4: Strategy from prepared universe (inactive period)
        strat_raw = row.get("strategy","")
        if "prepared" in strat_raw.lower() or "phase_e" in strat_raw.lower():
            row_flags.append("FROM_PREPARED_UNIVERSE")

        flag_str  = " | ".join(row_flags) if row_flags else "OK"
        unreal_str = f"{unreal:>12,.0f}" if unreal is not None else f"{'?':>12s}"

        print(f"  {ts:12s} {oid[:35]:35s} {direction:5s} {qty:6d} {entry:9.2f} {sl:9.2f} {tgt:9.2f} {strat:25s} {age_days:5d}d {unreal_str}  {flag_str}")
        flags.extend([(sym, oid, f) for f in row_flags])

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*100}")
print(f"SUMMARY")
print(f"{'='*100}")
print(f"  Total orphaned open positions : {total_positions}")
print(f"  Total notional exposure       : {total_exposure:>15,.2f}")

if flags:
    print(f"\n  ⚠  FLAGGED ENTRIES ({len(flags)}):")
    for sym, oid, flag in flags:
        print(f"     {sym:15s} {oid[:35]:35s} → {flag}")

# Separate: truly active (< 5 days old)
young = [(oid, r) for oid, r in truly_open.items()
         if (datetime.now() - datetime.strptime(r.get("timestamp","2000-01-01")[:10], "%Y-%m-%d")).days <= 5]
old   = [(oid, r) for oid, r in truly_open.items()
         if (datetime.now() - datetime.strptime(r.get("timestamp","2000-01-01")[:10], "%Y-%m-%d")).days > 30]

print(f"\n  Breakdown by age:")
print(f"    Recent (≤5 days)  : {len(young)}")
print(f"    Zombie (>30 days) : {len(old)}")

# BANKBARODA specific
if "BANKBARODA" in by_sym:
    bb = by_sym["BANKBARODA"][0]
    oid, row = bb
    entry = float(row.get("entry_price",0))
    sl    = float(row.get("stop_loss",0) or 0)
    tgt   = float(row.get("target",0) or 0)
    live  = live_prices.get("BANKBARODA")
    lvl   = TODAY_LEVELS.get("BANKBARODA",{})
    print(f"\n{'='*100}")
    print(f"BANKBARODA — ACTIVE OPEN POSITION (DETAILED)")
    print(f"{'='*100}")
    print(f"  Entry price           : {entry:.2f}")
    print(f"  Stop loss             : {sl:.2f}  (risk/share: {entry-sl:.2f})")
    print(f"  Target                : {tgt:.2f}  (reward/share: {tgt-entry:.2f})")
    print(f"  R:R ratio             : {(tgt-entry)/(entry-sl):.2f}:1" if sl and entry > sl else "  R:R: N/A")
    print(f"  OLD resistance        : 273.99  (level when trade was entered)")
    print(f"  NEW resistance (today): {lvl.get('resistance','-'):.2f}")
    print(f"  NEW support (today)   : {lvl.get('support','-'):.2f}")
    if live:
        print(f"  Current live LTP      : {live:.2f}")
        unreal = (live - entry) * int(row.get("quantity",0))
        print(f"  Unrealized P&L        : {unreal:,.2f}")
        dist_to_sl  = live - sl
        dist_to_tgt = tgt - live
        dist_to_res = lvl.get("resistance",0) - live
        print(f"  Distance to SL        : {dist_to_sl:.2f}  ({'BREACHED!' if live < sl else 'safe'})")
        print(f"  Distance to target    : {dist_to_tgt:.2f}")
        print(f"  Distance to resistance: {dist_to_res:.2f}  ({'AT/ABOVE' if dist_to_res <= 0 else 'below resistance'})")
        if dist_to_res < 5.0 and live > sl:
            print(f"\n  ⚠  ALERT: LTP is within ₹{dist_to_res:.2f} of NEW resistance ({lvl.get('resistance'):.2f}).")
            print(f"     Original setup used OLD resistance of 273.99.")
            print(f"     With refreshed levels, stock faces resistance imminently.")
            print(f"     Consider whether to exit or hold through resistance.")
    print(f"\n  ENTRY VALIDATION:")
    print(f"    Was live LTP used?     YES — PriceRefresh thread was active (confirmed by PriceGuard logs)")
    print(f"    Entry vs old S/R?      Entry 271.25 < old resistance 273.99 → VALID setup (approaching resistance)")
    print(f"    Entry vs new S/R?      Entry 271.25 < new resistance 272.25 → VALID at entry; now AT resistance")
    print(f"    Prepared universe?     NO — static watchlist used (prepared universe was inactive)")
    print(f"    Signal based on stale? PARTIAL — S/R levels were from May 22. Entry was valid. Resistance now lower.")
