import sqlite3, sys
conn = sqlite3.connect('/app/data/control_tower.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT cycle_id,started_at,regime,vix,signals_generated,strategies_assigned,"
    "risk_approved,sim_approved,trades_executed FROM ct_cycles "
    "WHERE started_at LIKE '2026-04-09%' ORDER BY started_at"
).fetchall()
if not rows:
    print("NO CYCLES TODAY")
for r in rows:
    d = dict(r)
    ts   = (d.get('started_at') or '')[:16]
    reg  = d.get('regime') or '?'
    vix  = d.get('vix') or 0
    sig  = d.get('signals_generated') or 0
    strt = d.get('strategies_assigned') or 0
    risk = d.get('risk_approved') or 0
    sim  = d.get('sim_approved') or 0
    exe  = d.get('trades_executed') or 0
    print(f"{ts} | {reg:<12} | VIX={vix:.1f} | sig={sig} strat={strt} risk={risk} sim={sim} exec={exe}")

print("---DECISIONS---")
dec = conn.execute(
    "SELECT ts,symbol,strategy,confidence,decision FROM ct_decisions "
    "WHERE ts LIKE '2026-04-09%' ORDER BY ts"
).fetchall()
for d in dec:
    print(dict(d))
conn.close()
