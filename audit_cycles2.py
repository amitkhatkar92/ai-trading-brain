#!/usr/bin/env python3
import sqlite3
from datetime import datetime

ct = sqlite3.connect('/tmp/ct.db')
ct.row_factory = sqlite3.Row

# Inspect ct_cycles more carefully
# A MarketIntelligence abort = cycle started but completed with no signals
# AND very high cycle_ms (matching the abort latencies we know: 15k-26k ms)
# OR had_error=1

# First: check date range of data
first = ct.execute("SELECT MIN(started_at), MAX(started_at), COUNT(*) FROM ct_cycles").fetchone()
print(f"ct_cycles date range: {first[0]} to {first[1]}, total={first[2]}")

# Check what had_error looks like
err_vals = ct.execute("SELECT had_error, COUNT(*) FROM ct_cycles GROUP BY had_error").fetchall()
print(f"had_error values: {[(r[0], r[1]) for r in err_vals]}")

# Cycles with 0 signals generated (likely aborted before OpportunityEngine)
zero_sig = ct.execute("""
    SELECT started_at, cycle_ms, regime, signals_generated, trades_executed, had_error
    FROM ct_cycles
    WHERE signals_generated = 0
    ORDER BY started_at DESC
    LIMIT 30
""").fetchall()
print(f"\nZero-signal cycles (last 30):")
for r in zero_sig:
    print(f"  {r['started_at']} | ms={r['cycle_ms']} | regime={r['regime']} | err={r['had_error']}")

# Look for high cycle_ms cycles (potential aborts: > 14000ms at MarketIntelligence level)
print(f"\nHigh latency cycles (cycle_ms >= 14000):")
high_lat = ct.execute("""
    SELECT started_at, cycle_ms, regime, vix, pcr, signals_generated, trades_executed, had_error
    FROM ct_cycles
    WHERE cycle_ms >= 14000
    ORDER BY started_at
""").fetchall()
for r in high_lat:
    print(f"  {r['started_at']} | ms={r['cycle_ms']} | sig={r['signals_generated']} | "
          f"regime={r['regime']} | vix={r['vix']} | err={r['had_error']}")
print(f"  Total: {len(high_lat)}")

# Check system.halt events (potential cycle aborts)
print(f"\nsystem.halt events:")
halts = ct.execute("""
    SELECT e.ts, e.cycle_id, e.event_type, e.payload
    FROM ct_events e
    WHERE e.event_type = 'system.halt'
    ORDER BY e.ts
""").fetchall()
for r in halts:
    print(f"  {r['ts']} | cycle={r['cycle_id']} | payload={str(r['payload'])[:200]}")

# system.cycle.started but no system.cycle.complete = aborted cycles
print(f"\nCycles started but never completed (aborted):")
aborted = ct.execute("""
    SELECT s.ts as start_ts, s.cycle_id, s.payload
    FROM ct_events s
    WHERE s.event_type = 'system.cycle.started'
      AND NOT EXISTS (
          SELECT 1 FROM ct_events c
          WHERE c.event_type = 'system.cycle.complete'
            AND c.cycle_id = s.cycle_id
      )
    ORDER BY s.ts
    LIMIT 50
""").fetchall()
for r in aborted:
    print(f"  {r['start_ts']} | cycle={r['cycle_id']} | {str(r['payload'])[:100]}")
print(f"  Total aborted (started, no complete): {len(aborted)}")
