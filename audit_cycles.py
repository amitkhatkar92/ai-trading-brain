#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

ct = sqlite3.connect('/tmp/ct.db')
ct.row_factory = sqlite3.Row

# Date range: last 30 trading days from 2026-06-09
# Approx: go back 42 calendar days to cover 30 trading days
cutoff = '2026-04-25'

print("=== ALL ABORTED / ERROR CYCLES (had_error=1) ===")
rows = ct.execute("""
    SELECT cycle_id, started_at, completed_at, had_error, regime, vix, breadth, pcr,
           signals_generated, strategies_assigned, trades_executed, cycle_ms
    FROM ct_cycles
    WHERE had_error = 1
      AND started_at >= ?
    ORDER BY started_at
""", (cutoff,)).fetchall()

for r in rows:
    print(f"  {r['started_at']} | cycle_ms={r['cycle_ms']} | regime={r['regime']} | "
          f"vix={r['vix']} | pcr={r['pcr']} | signals={r['signals_generated']} | "
          f"trades={r['trades_executed']}")

print(f"\n  Total error cycles: {len(rows)}")

print("\n=== MarketIntelligence ABORT EVENTS from ct_events ===")
abort_evts = ct.execute("""
    SELECT e.ts, e.cycle_id, e.event_type, e.source_agent, e.payload
    FROM ct_events e
    WHERE (e.payload LIKE '%CRITICAL%MarketIntelligence%'
        OR e.payload LIKE '%MarketIntelligence%aborted%'
        OR e.payload LIKE '%MarketIntelligence%CRITICAL%'
        OR e.event_type LIKE '%abort%'
        OR e.event_type LIKE '%ABORT%'
        OR e.event_type LIKE '%critical%latency%'
        OR e.event_type LIKE '%CRITICAL_LATENCY%')
      AND e.ts >= ?
    ORDER BY e.ts
""", (cutoff,)).fetchall()

for r in abort_evts:
    print(f"  {r['ts']} | cycle={r['cycle_id']} | type={r['event_type']} | "
          f"agent={r['source_agent']} | payload={str(r['payload'])[:120]}")

print(f"\n  Total abort events: {len(abort_evts)}")

print("\n=== DISTINCT EVENT TYPES in ct_events ===")
etypes = ct.execute("SELECT DISTINCT event_type, COUNT(*) as n FROM ct_events GROUP BY event_type ORDER BY n DESC LIMIT 30").fetchall()
for r in etypes:
    print(f"  {r['event_type']}: {r['n']}")

print("\n=== SYSTEM_LOGS abort entries ===")
tb = sqlite3.connect('/tmp/tb.db')
tb.row_factory = sqlite3.Row
slogs = tb.execute("""
    SELECT ts, level, component, event_type, message
    FROM system_logs
    WHERE (message LIKE '%CRITICAL%latency%' OR message LIKE '%aborted%cycle%'
        OR event_type LIKE '%abort%' OR event_type LIKE '%CRITICAL%')
      AND ts >= ?
    ORDER BY ts
""", (cutoff,)).fetchall()
for r in slogs:
    print(f"  {r['ts']} | {r['level']} | {r['component']} | {r['event_type']} | {r['message'][:100]}")
print(f"\n  Total system_log abort entries: {len(slogs)}")
