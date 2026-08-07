"""Probe DTA-001 data sources."""
import sqlite3, json
from pathlib import Path

DATA = Path("data")
conn = sqlite3.connect(str(DATA / "control_tower.db"))
conn.row_factory = sqlite3.Row

# Get approved decisions
approved = conn.execute("""
    SELECT d.cycle_id, d.symbol, d.decision, d.confidence, d.strategy,
           d.rejection_reason, c.started_at, c.regime, c.vix
    FROM ct_decisions d
    JOIN ct_cycles c ON d.cycle_id = c.cycle_id
    WHERE d.decision = 'APPROVED'
    ORDER BY c.started_at DESC LIMIT 5
""").fetchall()
print("=== APPROVED DECISIONS ===")
for r in approved:
    print(dict(r))

print()
# Get events for one approved cycle
if approved:
    cid = approved[0]["cycle_id"]
    sym = approved[0]["symbol"]
    print(f"Events for cycle {cid} ({sym}):")
    evts = conn.execute("""
        SELECT ts, event_type, source_agent, payload
        FROM ct_events WHERE cycle_id = ?
        ORDER BY ts
    """, (cid,)).fetchall()
    for e in evts:
        p = str(e["payload"] or "")[:300]
        print(f"  [{e['event_type']}] src={e['source_agent']} | {p}")

print()
# Get an opportunity event payload (structure)
opp = conn.execute("""
    SELECT payload FROM ct_events
    WHERE event_type = 'opportunity.equity.found'
    LIMIT 3
""").fetchall()
print("=== OPPORTUNITY PAYLOADS ===")
for o in opp:
    try:
        p = json.loads(o["payload"])
        print(json.dumps(p, indent=2, default=str)[:800])
        print("---")
    except Exception:
        print(str(o["payload"])[:400])

conn.close()

print()
# Paper trades - what fields exist
import csv
with open(DATA / "paper_trades.csv") as f:
    reader = csv.DictReader(f)
    rows = [r for r in reader]
print(f"=== PAPER TRADES: {len(rows)} total ===")
if rows:
    print(f"Fields: {list(rows[0].keys())}")
    # Find RELIANCE trades
    rel = [r for r in rows if "RELIANCE" in r.get("symbol","")]
    print(f"RELIANCE trades: {len(rel)}")
    if rel:
        print("Sample RELIANCE trade:")
        print(json.dumps(rel[-1], indent=2))
