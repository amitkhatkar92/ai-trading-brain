"""
oios/scanners/signal_writer.py

Signal Birth Record Writer — Layer 4 Sub-C (active from Day 1 of Phase A).

Converts scanner RawSignal objects into persisted signal_births records
and routes them through the Opportunity Service.

This is the ONLY path from scanner output to the database.

Scanner → signal_writer.write_signal() → OpportunityService → Repository → DB

Per MAS Section 5, Layer 4:
  Every signal evaluated by any Discovery layer is assessed against the minimum
  threshold (base_score > 4.0). If met, a signal_births record and an associated
  opportunity_signals linkage are created immediately.
"""

from __future__ import annotations
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Optional

from ..domain.models import SignalBirth
from ..domain.opportunity_service import attach_or_create_opportunity
from ..db import repository as R

log = logging.getLogger(__name__)


@dataclass
class WriteResult:
    signal_id:      str
    opportunity_id: str
    was_new_opp:    bool


def write_signal(
    conn: sqlite3.Connection,
    raw,                            # RawSignal from layer_1a.py (or any scanner)
    birth_ttl_days: int,
    sector: str,
    today: Optional[str] = None,
) -> Optional[WriteResult]:
    """
    Persist one qualifying scanner signal and attach it to an opportunity.

    Returns WriteResult, or None if base_score ≤ MIN_WRITE_THRESHOLD (should
    not happen if callers filter, but guard here too).
    """
    from ..scanners.layer_1a import MIN_WRITE_THRESHOLD

    if raw.base_score <= MIN_WRITE_THRESHOLD:
        log.debug(
            "[SignalWriter] %s %s base_score=%.3f below threshold — not writing",
            raw.symbol, raw.archetype_id, raw.base_score,
        )
        return None

    signal_id = str(uuid.uuid4())

    # Build the canonical SignalBirth domain object
    sb = SignalBirth(
        signal_id               = signal_id,
        symbol                  = raw.symbol,
        archetype_id            = raw.archetype_id,
        archetype_version       = raw.archetype_version,
        signal_type             = raw.signal_type,
        detected_at             = raw.detected_at,
        birth_price             = raw.birth_price,
        base_score              = raw.base_score,
        regime_at_birth         = raw.regime,
        expected_ttl_days       = raw.expected_ttl_days,
        expected_move_direction = raw.direction,
        expected_move_pct       = raw.expected_move_pct,
        expected_move_pct_source= raw.expected_move_pct_source,
        theme_phase_at_birth    = raw.theme_phase_at_birth,
        consensus_score_at_birth= raw.consensus_score_at_birth,
    )

    # Persist signal_birth first (without opportunity_id — service will link it)
    with conn:
        R.create_signal_birth(conn, sb)

    # Route through Opportunity Service (merge-window rule)
    with conn:
        opp, was_new = attach_or_create_opportunity(
            conn       = conn,
            signal     = sb,
            birth_ttl_days = birth_ttl_days,
            regime     = raw.regime,
            theme_phase= raw.theme_phase_at_birth,
            today      = today or raw.detected_at,
        )

    log.info(
        "[SignalWriter] Wrote signal %s for %s %s score=%.3f → opp=%s (new=%s)",
        signal_id[:8], raw.symbol, raw.archetype_id, raw.base_score,
        opp.opportunity_id[:8], was_new,
    )

    return WriteResult(
        signal_id      = signal_id,
        opportunity_id = opp.opportunity_id,
        was_new_opp    = was_new,
    )


def write_scan_results(
    conn: sqlite3.Connection,
    scan_result,                    # ScanResult from layer_1a.run_scan()
    birth_ttl_days: int = 10,
    symbol_to_sector: Optional[dict[str, str]] = None,
) -> dict:
    """
    Write all qualifying signals from a scan result.
    Returns summary dict with counts.
    """
    written    = 0
    new_opps   = 0
    merged     = 0
    errors     = 0

    for raw in scan_result.qualifying_signals:
        sector = (symbol_to_sector or {}).get(raw.symbol, "UNKNOWN")
        try:
            result = write_signal(
                conn,
                raw,
                birth_ttl_days = birth_ttl_days,
                sector         = sector,
                today          = scan_result.scan_date,
            )
            if result:
                written += 1
                if result.was_new_opp:
                    new_opps += 1
                else:
                    merged += 1
        except Exception as exc:
            log.error(
                "[SignalWriter] Failed to write signal for %s %s: %s",
                raw.symbol, raw.archetype_id, exc,
            )
            errors += 1

    log.info(
        "[SignalWriter] Scan %s: written=%d new_opps=%d merged=%d errors=%d",
        scan_result.scan_date, written, new_opps, merged, errors,
    )
    return {"written": written, "new_opps": new_opps, "merged": merged, "errors": errors}
