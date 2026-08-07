"""
production_readiness/ph2_short_dna.py — Phase 2: SHORT DNA Operationalisation.

Operationalises H001 (Loser DNA cross-year validation — CONFIRMED).
Loads loser DNA from institutional_dna.db and evaluates current feature
snapshots to generate SHORT signal confidence boosts.

Governance: identical rules to BUY — same confidence gate, regime check,
            risk, portfolio, and decision thresholds.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .prr_config import (
    DNA_DB,
    LOSER_DNA_CONFIDENCE_GATE,
    LOSER_DNA_MAX_BOOST,
)
from .prr_models import ShortDNAAudit, ShortDNASignal

log = logging.getLogger(__name__)


def _load_loser_dna() -> List[Dict[str, Any]]:
    """Load active loser DNA patterns from the institutional_dna.db."""
    if not DNA_DB.exists():
        return []
    try:
        with sqlite3.connect(DNA_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, feature_name, direction, category, lifecycle,
                       confidence, effect_size, regime_consistency,
                       sector_consistency, evidence_count, metadata
                FROM dna
                WHERE category = 'loser'
                  AND lifecycle = 'INSTITUTIONAL'
                  AND CAST(confidence AS REAL) >= ?
                  AND is_current = 1
                ORDER BY CAST(confidence AS REAL) DESC
            """, (LOSER_DNA_CONFIDENCE_GATE,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        log.warning("[ShortDNA] DB load failed: %s", e)
        return []


def _parse_conditions(metadata_str: str) -> List[str]:
    """Extract condition strings from DNA metadata JSON."""
    try:
        m = json.loads(metadata_str or "{}")
        return m.get("conditions", [])
    except Exception:
        return []


def evaluate_short_dna(
    features: Dict[str, float],
    regime: str = "UNKNOWN",
) -> Tuple[float, List[str]]:
    """
    Evaluate current market features against loser DNA patterns.

    Returns (confidence_boost, matching_conditions)
    confidence_boost: 0.0 if no match, up to LOSER_DNA_MAX_BOOST if multiple match.
    """
    loser_dna = _load_loser_dna()
    if not loser_dna:
        return 0.0, []

    # Loser DNA is valid in all regimes except extreme bull trends
    if regime.upper() in ("BULL_TREND_STRONG",):
        return 0.0, ["Regime not compatible with loser DNA SHORT generation"]

    matched_conditions: List[str] = []
    total_conf_weight = 0.0
    n_matched = 0

    for dna in loser_dna:
        conditions = _parse_conditions(dna.get("metadata") or "")
        feature_name = dna.get("feature_name", "")
        direction = (dna.get("direction") or "").upper()

        # Only use SHORT/SELL direction loser DNA
        if direction not in ("SHORT", "SELL"):
            continue

        # Check if the primary feature exists in current context
        if feature_name in features:
            feat_val = features[feature_name]
            # Evaluate first condition (feature threshold check)
            for cond in conditions[:3]:
                try:
                    cond_clean = cond.strip()
                    if not cond_clean:
                        continue
                    # Parse simple condition: "feature_name OP threshold"
                    parts = cond_clean.split()
                    if len(parts) == 3:
                        _, op, thresh = parts
                        thresh = float(thresh)
                        check_val = features.get(feature_name, feat_val)
                        if   op == ">" and check_val > thresh:
                            matched_conditions.append(cond_clean)
                            n_matched += 1
                            total_conf_weight += float(dna.get("confidence") or 0.0)
                        elif op == "<" and check_val < thresh:
                            matched_conditions.append(cond_clean)
                            n_matched += 1
                            total_conf_weight += float(dna.get("confidence") or 0.0)
                        elif op == ">=" and check_val >= thresh:
                            matched_conditions.append(cond_clean)
                            n_matched += 1
                            total_conf_weight += float(dna.get("confidence") or 0.0)
                        elif op == "<=" and check_val <= thresh:
                            matched_conditions.append(cond_clean)
                            n_matched += 1
                            total_conf_weight += float(dna.get("confidence") or 0.0)
                except Exception:
                    continue

    if n_matched == 0:
        return 0.0, []

    # Scale boost: each matching condition adds weight, capped at max boost
    avg_conf = total_conf_weight / n_matched
    boost = min(avg_conf * n_matched * 0.30, LOSER_DNA_MAX_BOOST)
    log.info(
        "[ShortDNA] %d loser DNA conditions matched, boost=%.2f regime=%s",
        n_matched, boost, regime,
    )
    return round(boost, 3), matched_conditions[:10]


def get_short_dna_confidence_boost(
    features: Dict[str, float],
    regime: str = "UNKNOWN",
) -> float:
    """
    Public function for the scanner's _identify_setup() to call.
    Returns a confidence boost (0.0–LOSER_DNA_MAX_BOOST) when loser DNA conditions match.
    """
    boost, _ = evaluate_short_dna(features, regime)
    return boost


def run_short_dna_audit(
    features: Dict[str, float],
    regime: str = "UNKNOWN",
    today: str | None = None,
) -> ShortDNAAudit:
    """Generate the SHORT_TRADING_AUDIT dataset."""
    loser_dna = _load_loser_dna()
    boost, conditions = evaluate_short_dna(features, regime)
    today = today or datetime.now().date().isoformat()

    # Generate candidate signals for symbols with SHORT DNA support
    # The scanner uses this for live signals; here we just enumerate
    signals = []
    if boost > 0:
        # Example signal structure — actual symbols come from the scanner
        sig = ShortDNASignal(
            symbol="[scanner-generated]",
            direction="SHORT",
            dna_confidence=boost,
            matching_conditions=conditions,
            loser_pattern_id="H001/study002a",
            regime_compatible=True,
            governance_approved=(boost >= LOSER_DNA_CONFIDENCE_GATE),
            rejection_reason="" if boost >= LOSER_DNA_CONFIDENCE_GATE else "below_confidence_gate",
        )
        signals.append(sig)

    return ShortDNAAudit(
        date=today,
        total_loser_dna=len(loser_dna),
        conditions_evaluated=len([d for d in loser_dna if d.get("direction","").upper() in ("SHORT","SELL")]),
        short_signals_generated=1 if boost > 0 else 0,
        short_signals_approved=1 if boost >= LOSER_DNA_CONFIDENCE_GATE else 0,
        regime=regime,
        confidence_gate=LOSER_DNA_CONFIDENCE_GATE,
        top_signals=signals,
    )
