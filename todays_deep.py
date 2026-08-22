"""Detailed strategy performance stats and today's analysis."""
import sys, json
sys.path.insert(0, "/app")
import logging; logging.disable(logging.INFO)

# ── Strategy performance table ────────────────────────────────────────────
print("STRATEGY PERFORMANCE TABLE")
print("=" * 80)
try:
    from learning_system.strategy_performance_tracker import get_performance_tracker
    tracker = get_performance_tracker()
    
    if hasattr(tracker, "get_table"):
        tbl = tracker.get_table()
        if isinstance(tbl, str):
            print(tbl)
        elif isinstance(tbl, list):
            for row in tbl:
                print(f"  {row}")
    
    if hasattr(tracker, "get_all_stats"):
        stats = tracker.get_all_stats()
        if isinstance(stats, dict):
            for strat, d in stats.items():
                enabled = d.get("enabled", True)
                wins    = d.get("wins", d.get("win_count", 0))
                total   = d.get("total", d.get("trade_count", 0))
                pnl     = d.get("total_pnl", d.get("pnl", 0))
                wr      = wins/total if total > 0 else 0
                flag    = "✓" if enabled else "✗ DISABLED"
                print(f"  [{flag}] {strat[:40]:42} trades={total:3}  wins={wins:3}  wr={wr:.0%}  pnl=₹{pnl:>12,.0f}")
        else:
            print(f"  Stats type: {type(stats)}: {str(stats)[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# ── Today's candidate quality ─────────────────────────────────────────────
print()
print("TODAY'S SCANNER CANDIDATES (top 10)")
print("=" * 80)
try:
    with open("/app/data/daily_candidates.json") as f:
        cands = json.load(f)
    if isinstance(cands, dict):
        items = cands.get("candidates", list(cands.values()))
    else:
        items = cands
    
    # Sort by confidence if available
    if items and isinstance(items[0], dict):
        items_sorted = sorted(items, key=lambda x: float(x.get("confidence", x.get("score", 0))), reverse=True)
        for c in items_sorted[:10]:
            sym    = c.get("symbol", c.get("ticker", "?"))
            conf   = c.get("confidence", c.get("score", "?"))
            direct = c.get("direction", c.get("bias", "?"))
            entry  = c.get("entry_price", c.get("entry", "?"))
            rr     = c.get("rr", c.get("risk_reward", "?"))
            strat  = c.get("strategy", "?")
            print(f"  {sym:14}  dir={str(direct):5}  conf={str(conf)[:5]:6}  rr={str(rr)[:4]:5}"
                  f"  entry={str(entry)[:8]:9}  strategy={str(strat)[:25]}")
    else:
        print(f"  {len(items)} candidates (non-dict format)")
        print(f"  Sample: {str(items[0])[:200] if items else 'empty'}")
except Exception as e:
    print(f"  Error: {e}")

# ── Learning: what did the system learn today? ────────────────────────────
print()
print("LEARNING EVENTS (from SQLite telemetry if available)")
print("=" * 80)
try:
    import sqlite3, os
    db_paths = ["/app/data/trading_brain.db", "/app/data/telemetry.db", "/app/data/learning.db"]
    for dbp in db_paths:
        if os.path.exists(dbp):
            print(f"  Found DB: {dbp}")
            conn = sqlite3.connect(dbp)
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            print(f"  Tables: {[t[0] for t in tables]}")
            # Check for today's learning events
            for (tname,) in tables:
                try:
                    rows = conn.execute(f"SELECT * FROM {tname} WHERE timestamp LIKE '2026-05-29%' LIMIT 5").fetchall()
                    if rows:
                        print(f"  [{tname}] {len(rows)} rows today:")
                        for r in rows:
                            print(f"    {str(r)[:120]}")
                except:
                    pass
            conn.close()
except Exception as e:
    print(f"  Error: {e}")

print()
print("DONE")
