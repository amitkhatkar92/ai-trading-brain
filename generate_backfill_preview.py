"""
Generate OUTCOME_TRACKING_BACKFILL_PREVIEW_001.json.

READ-ONLY: computes outcomes for all historical signal_births but does NOT
write to the database (dry_run=True). Saves the preview JSON locally.
"""
import json, sqlite3, sys, os
sys.path.insert(0, '/root/ai-trading-brain')
os.chdir('/root/ai-trading-brain')

from oios.engine.signal_outcome_tracker import (
    compute_signal_outcome, resolve_signal_outcomes, FS_NO_DATA, FS_PENDING
)

DB = '/root/ai-trading-brain/data/market_behavior.db'
OUT = '/tmp/OUTCOME_TRACKING_BACKFILL_PREVIEW_001.json'

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# Get latest OHLCV date
as_of = con.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
print(f"as_of_date: {as_of}")

# Get all unresolved signals
rows = con.execute("""
    SELECT signal_id, symbol, expected_move_direction, birth_price,
           detected_at, expected_ttl_days, expected_move_pct, archetype_id
    FROM signal_births
    WHERE final_state IS NULL
    ORDER BY detected_at ASC
""").fetchall()

print(f"signals to preview: {len(rows)}")

preview = []
stats = {"total": 0, "WIN": 0, "LOSS": 0, "EXPIRED": 0, "PENDING": 0, "NO_DATA": 0, "error": 0}

for row in rows:
    stats["total"] += 1
    try:
        outcome = compute_signal_outcome(
            conn              = con,
            signal_id         = row["signal_id"],
            symbol            = row["symbol"],
            direction         = row["expected_move_direction"],
            birth_price       = row["birth_price"],
            detected_at       = row["detected_at"],
            expected_ttl_days = row["expected_ttl_days"],
            expected_move_pct = row["expected_move_pct"] or 8.0,
            as_of_date        = as_of,
        )
        if outcome is None:
            stats["error"] += 1
            continue

        stats[outcome.final_state] = stats.get(outcome.final_state, 0) + 1

        preview.append({
            "signal_id":                    outcome.signal_id,
            "symbol":                       outcome.symbol,
            "archetype_id":                 row["archetype_id"],
            "signal_timestamp":             row["detected_at"],
            "direction":                    outcome.direction,
            "entry":                        row["birth_price"],
            "observation_window":           f"{row['detected_at']} to {outcome.obs_end_date}",
            "reconstructed_actual_move_pct": outcome.actual_move_pct,
            "reconstructed_MFE":            outcome.peak_move_pct,
            "reconstructed_MAE":            outcome.max_adverse_pct,
            "proposed_final_state":         outcome.final_state,
            "days_to_peak":                 outcome.days_to_peak,
            "final_age_calendar_days":      outcome.final_age_calendar_days,
            "expected_move_pct":            row["expected_move_pct"],
            "data_source":                  "ohlcv_daily",
            "confidence":                   "HIGH" if outcome.final_state != "NO_DATA" else "NO_DATA",
        })
    except Exception as e:
        stats["error"] += 1
        print(f"  ERROR {row['signal_id'][:8]} {row['symbol']}: {e}")

con.close()

output = {
    "preview_id": "OUTCOME_TRACKING_BACKFILL_PREVIEW_001",
    "generated_at": "2026-08-14",
    "as_of_date": as_of,
    "description": "READ-ONLY preview. No database records were modified.",
    "stats": stats,
    "win_rate_preview": stats["WIN"] / (stats["WIN"] + stats["LOSS"] + stats["EXPIRED"]) if (stats["WIN"] + stats["LOSS"] + stats["EXPIRED"]) > 0 else None,
    "signals": preview,
}

with open(OUT, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nStats: {json.dumps(stats, indent=2)}")
print(f"Win rate (closed signals only): {output['win_rate_preview']}")
print(f"\nPreview saved to {OUT}")
print(f"Total signals in preview: {len(preview)}")
