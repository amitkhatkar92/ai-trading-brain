"""Today's trading activity, learning, and EOD findings - May 29, 2026."""
import csv, sys, json, os
sys.path.insert(0, "/app")
from datetime import date

TODAY = "2026-05-29"

# ── 1. Today's trades ─────────────────────────────────────────────────────
print("=" * 60)
print("TODAY'S TRADES (May 29, 2026)")
print("=" * 60)
try:
    rows = list(csv.DictReader(open("/app/data/paper_trades.csv")))
    today_rows = [r for r in rows if r.get("timestamp", "").startswith(TODAY)]
    opens  = [r for r in today_rows if r.get("event", "").upper() in ("OPEN", "ENTRY")]
    closes = [r for r in today_rows if r.get("event", "").upper() in ("CLOSE", "EXIT", "VOID")]
    print(f"Total today rows: {len(today_rows)}  opens={len(opens)}  closes={len(closes)}")
    if today_rows:
        for r in today_rows:
            pnl = r.get("pnl", "")
            print(f"  {r['timestamp'][:16]}  {r.get('event','?'):6}  {r.get('symbol','?'):14}"
                  f"  {r.get('direction','?'):5}  entry={r.get('entry_price','?'):8}"
                  f"  pnl={pnl if pnl else 'N/A':>12}  {r.get('reason','')[:55]}")
    else:
        print("  No trades today.")
except Exception as e:
    print(f"  Error reading CSV: {e}")

# ── 2. Total today P&L ────────────────────────────────────────────────────
print()
print("TODAY'S P&L")
print("-" * 40)
try:
    today_pnl = 0.0
    closed_today = [r for r in today_rows if r.get("event", "").upper() in ("CLOSE", "EXIT")]
    for r in closed_today:
        try:
            today_pnl += float(r.get("pnl", 0) or 0)
        except:
            pass
    print(f"  Closed today:  {len(closed_today)} trades")
    print(f"  Today P&L:     ₹{today_pnl:,.2f}")
except Exception as e:
    print(f"  Error: {e}")

# ── 3. Strategy performance tracker ──────────────────────────────────────
print()
print("STRATEGY PERFORMANCE (from tracker)")
print("-" * 40)
try:
    from learning_system.strategy_performance_tracker import get_performance_tracker
    tracker = get_performance_tracker()
    if hasattr(tracker, "get_summary"):
        summary = tracker.get_summary()
        for k, v in (summary.items() if isinstance(summary, dict) else []):
            print(f"  {k}: {v}")
    elif hasattr(tracker, "_data"):
        for strat, data in list(tracker._data.items())[:10]:
            print(f"  {strat[:35]:36} wins={data.get('wins',0):3}  total={data.get('total',0):3}"
                  f"  wr={data.get('win_rate',0):.0%}  enabled={data.get('enabled','?')}")
    else:
        print(f"  Tracker type: {type(tracker)}")
        print(f"  Methods: {[m for m in dir(tracker) if not m.startswith('_')][:10]}")
except Exception as e:
    print(f"  Not available: {e}")

# ── 4. Learning engine log ────────────────────────────────────────────────
print()
print("LEARNING ENGINE LOG (today)")
print("-" * 40)
try:
    log_path = "/app/logs/trading.log"
    if os.path.exists(log_path):
        with open(log_path) as f:
            lines = f.readlines()
        learn_lines = [l.strip() for l in lines
                       if TODAY in l and any(w in l for w in
                       ("LearningEngine", "EOD", "StrategyHealth", "WinRate", "disabled", "promoted",
                        "learning", "Learning", "performance", "Performance"))]
        if learn_lines:
            for l in learn_lines[-15:]:
                print(f"  {l[:110]}")
        else:
            print("  No learning events logged today.")
    else:
        print(f"  Log not found at {log_path}")
except Exception as e:
    print(f"  Error: {e}")

# ── 5. Daily candidates freshness ────────────────────────────────────────
print()
print("SCANNER STATE")
print("-" * 40)
try:
    cand_path = "/app/data/daily_candidates.json"
    if os.path.exists(cand_path):
        import datetime
        mtime = os.path.getmtime(cand_path)
        age_hours = (datetime.datetime.now().timestamp() - mtime) / 3600
        with open(cand_path) as f:
            cands = json.load(f)
        count = len(cands) if isinstance(cands, list) else len(cands.get("candidates", cands))
        mdate = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  daily_candidates.json: {count} candidates  last_updated={mdate}  age={age_hours:.1f}h")
    else:
        print("  daily_candidates.json not found")
except Exception as e:
    print(f"  Error: {e}")

print()
print("DONE")
