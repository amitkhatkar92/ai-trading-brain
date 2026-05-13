"""
One-time migration: backfill disabled_reason for legacy disabled strategies.

Any strategy that is functionally DISABLED (metrics breach threshold) but has
disabled_reason=None gets stamped with LEGACY_DISABLE_PRE_METADATA to preserve
historical honesty — we are not fabricating an EARLY_ABORT reason retroactively.

Run once inside the container:
    python3 /app/scripts/backfill_shm_metadata.py
"""

import json
import os
import sys
from datetime import datetime

HEALTH_DB_PATH = "/app/data/strategy_health.json"

# Thresholds mirrored from strategy_health_monitor.py
EARLY_ABORT_MIN_TRADES = 8
MIN_TRADES             = 30
EARLY_ABORT_MAX_WR     = 0.25
LEGACY_REASON          = "LEGACY_DISABLE_PRE_METADATA"


def is_functionally_disabled(rec: dict) -> bool:
    trades  = rec.get("trades", 0)
    wins    = rec.get("wins", 0)
    total_r = rec.get("total_r", 0.0)
    wr = wins / trades if trades > 0 else 0.0
    return (
        EARLY_ABORT_MIN_TRADES <= trades < MIN_TRADES
        and wr < EARLY_ABORT_MAX_WR
        and total_r < 0
    )


def main():
    if not os.path.exists(HEALTH_DB_PATH):
        print(f"[Backfill] ERROR: {HEALTH_DB_PATH} not found.")
        sys.exit(1)

    with open(HEALTH_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    patched = 0
    for name, rec in data.items():
        has_reason = rec.get("disabled_reason") is not None
        if has_reason:
            print(f"[Backfill] {name}: already has reason={rec['disabled_reason']} — skip")
            continue

        if is_functionally_disabled(rec):
            trades  = rec["trades"]
            wins    = rec.get("wins", 0)
            total_r = rec.get("total_r", 0.0)
            wr = wins / trades if trades > 0 else 0.0

            rec["disabled_reason"]         = LEGACY_REASON
            rec["disabled_at_trades"]      = trades
            rec["disabled_wr"]             = round(wr, 4)
            rec["disabled_total_r"]        = round(total_r, 6)
            # Preserve historical honesty: disabled_since = "unknown"
            # Only stamp if currently null
            if rec.get("disabled_since") is None:
                rec["disabled_since"] = "pre-metadata-deploy"
            rec.setdefault("sessions_since_disabled", 0)
            rec.setdefault("cooldown_override", False)

            print(
                f"[Backfill] PATCHED {name}: "
                f"reason={LEGACY_REASON}  trades={trades}  wr={wr:.0%}  total_r={total_r:.4f}"
            )
            patched += 1
        else:
            print(f"[Backfill] {name}: not functionally disabled — skip")

    if patched > 0:
        with open(HEALTH_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n[Backfill] Done. Patched {patched} record(s). Saved to {HEALTH_DB_PATH}")
    else:
        print("\n[Backfill] Nothing to patch.")


if __name__ == "__main__":
    main()
