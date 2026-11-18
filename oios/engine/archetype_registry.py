"""
oios/engine/archetype_registry.py

MAS_v1.2 Table 2 (archetype_versions): "initial version 1 for all archetypes". The table
existed but was never seeded, so signal_births.archetype_version pointed at nothing and a
later change of detection rules could not be separated from earlier outcomes.

Seeding is idempotent and never rewrites an existing version. A rule change must add a new
version row (Layer 6 owns that); this only guarantees version 1 exists for every archetype
the scanners can emit, plus any archetype id already present in signal_births.
"""
from __future__ import annotations

import json
import sqlite3

from ..scanners import layer_1a, layer_1b

# archetype_id -> (signal_type, direction)
ARCHETYPES: dict[str, tuple[str, str]] = {
    "DNA_1A_MOMENTUM_CONT":      (layer_1a.SIGNAL_TYPE, "LONG"),
    "DNA_1A_52W_HIGH_EXPAND":    (layer_1a.SIGNAL_TYPE, "LONG"),
    "DNA_1A_SECTOR_BKT":         (layer_1a.SIGNAL_TYPE, "LONG"),
    "DNA_1A_RESULTS_FOLLOWTHR":  (layer_1a.SIGNAL_TYPE, "LONG"),
    "DNA_1A_MOMENTUM_BREAKDOWN": (layer_1a.SIGNAL_TYPE, "SHORT"),
    "DNA_1A_52W_LOW_EXPAND":     (layer_1a.SIGNAL_TYPE, "SHORT"),
    "DNA_1B_QUIET_ACCUMULATION": (layer_1b.SIGNAL_TYPE, "LONG"),
    "DNA_1B_DELIVERY_EXPANSION": (layer_1b.SIGNAL_TYPE, "LONG"),
    "DNA_1B_LOW_NOISE_STRENGTH": (layer_1b.SIGNAL_TYPE, "LONG"),
    "DNA_1B_SECTOR_PRE_BKT":    (layer_1b.SIGNAL_TYPE, "LONG"),
}

_DEFAULTS = {
    "1A": {"min_write_threshold": layer_1a.MIN_WRITE_THRESHOLD, "expected_move_pct": layer_1a.EXPECTED_MOVE_PCT,
           "expected_ttl_days": layer_1a.EXPECTED_TTL_DAYS},
    "1B": {"min_write_threshold": layer_1b.MIN_WRITE_THRESHOLD, "expected_move_pct": layer_1b.EXPECTED_MOVE_PCT,
           "expected_ttl_days": layer_1b.EXPECTED_TTL_DAYS},
}


def seed_archetype_versions(conn: sqlite3.Connection, today: str) -> int:
    """Insert version 1 for every known archetype that has no version row. Returns rows added."""
    existing = {r[0] for r in conn.execute("SELECT DISTINCT archetype_id FROM archetype_versions")}
    added = 0
    for archetype_id, (signal_type, direction) in ARCHETYPES.items():
        if archetype_id in existing:
            continue
        snapshot = {"signal_type": signal_type, "direction": direction, **_DEFAULTS[signal_type],
                    "source": "scanner_defaults_v1"}
        conn.execute(
            "INSERT OR IGNORE INTO archetype_versions "
            "(archetype_id, version_number, effective_from, change_reason, parameter_snapshot, approved_by) "
            "VALUES (?, 1, ?, 'INITIAL_VERSION', ?, 'SYSTEM')",
            (archetype_id, today, json.dumps(snapshot, sort_keys=True)))
        existing.add(archetype_id)
        added += 1
    # archetypes seen in real signals but not listed above still get a version-1 anchor
    for (archetype_id,) in conn.execute(
            "SELECT DISTINCT archetype_id FROM signal_births WHERE archetype_id IS NOT NULL").fetchall():
        if archetype_id in existing:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO archetype_versions "
            "(archetype_id, version_number, effective_from, change_reason, parameter_snapshot, approved_by) "
            "VALUES (?, 1, ?, 'INITIAL_VERSION', ?, 'SYSTEM')",
            (archetype_id, today, json.dumps({"source": "signal_births"})))
        existing.add(archetype_id)
        added += 1
    conn.commit()
    return added
