"""
institutional_learning/ilc_verification.py — Phase 8: Learning Verification Engine.

THE KEY NEW CAPABILITY.

Every learning action receives:
  - A unique Learning ID
  - A baseline metric snapshot
  - Verification dates at 30, 60, 90 trading days
  - Automatic measurement + verdict at each checkpoint

Verdicts: IMPROVED | NO_CHANGE | DECLINED
Actions:  Promote | Downgrade confidence | Retire / Rollback

Permanent rule: No knowledge becomes Institutional until
demonstrating measurable improvement.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ilc_config import (
    CALENDAR_DAYS_MAP, CT_DB, ILC_DIR,
    LEARNING_REGISTRY, PAPER_TRADES_CSV, VERIFICATION_WINDOWS,
)
from .ilc_models import LearningConfidence, LearningRecord, VerificationResult

log = logging.getLogger(__name__)

_REGISTRY_LOCK = threading.Lock()

# Metric improvement/decline thresholds
IMPROVEMENT_THRESHOLD = 0.05   # 5% improvement needed for IMPROVED verdict
DECLINE_THRESHOLD     = -0.05  # 5% decline triggers DECLINED verdict


# ── Registry persistence ──────────────────────────────────────────────────────

def _load_registry() -> List[LearningRecord]:
    """Load all learning records from the persistent JSON registry."""
    ILC_DIR.mkdir(parents=True, exist_ok=True)
    if not LEARNING_REGISTRY.exists():
        return []
    try:
        with open(LEARNING_REGISTRY, encoding="utf-8") as f:
            data = json.load(f)
        records = []
        for r in data:
            vrs = [VerificationResult(**v) for v in r.get("verification_results", [])]
            rec = LearningRecord(
                learning_id=r["learning_id"],
                created_date=r["created_date"],
                action_type=r["action_type"],
                category=r["category"],
                symbol=r["symbol"],
                description=r["description"],
                target_system=r["target_system"],
                expected_benefit=r.get("expected_benefit", ""),
                prediction_metric=r.get("prediction_metric", "scan_hit_rate"),
                measurement_windows=r.get("measurement_windows", VERIFICATION_WINDOWS),
                baseline_metrics=r.get("baseline_metrics", {}),
                verification_results=vrs,
                status=r.get("status", "PENDING"),
                confidence=r.get("confidence", LearningConfidence.LOW),
                eig_score=r.get("eig_score", 0.0),
                roi=r.get("roi"),
                executed=r.get("executed", False),
                outcome=r.get("outcome", ""),
            )
            records.append(rec)
        return records
    except Exception as e:
        log.warning("[ILC-Verify] Registry load failed: %s", e)
        return []


def _save_registry(records: List[LearningRecord]) -> None:
    """Atomically persist the registry."""
    ILC_DIR.mkdir(parents=True, exist_ok=True)
    data = []
    for r in records:
        data.append({
            "learning_id":        r.learning_id,
            "created_date":       r.created_date,
            "action_type":        r.action_type,
            "category":           r.category,
            "symbol":             r.symbol,
            "description":        r.description,
            "target_system":      r.target_system,
            "expected_benefit":   r.expected_benefit,
            "prediction_metric":  r.prediction_metric,
            "measurement_windows": r.measurement_windows,
            "baseline_metrics":   r.baseline_metrics,
            "verification_results": [vars(v) for v in r.verification_results],
            "status":             r.status,
            "confidence":         r.confidence,
            "eig_score":          r.eig_score,
            "roi":                r.roi,
            "executed":           r.executed,
            "outcome":            r.outcome,
        })
    tmp = str(LEARNING_REGISTRY) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, LEARNING_REGISTRY)


# ── Baseline metric measurement ───────────────────────────────────────────────

def _scan_hit_rate(symbol: str, start_date: str, end_date: str) -> float:
    """
    Compute scan hit rate: fraction of trading days where symbol was in ct_events.
    """
    if not CT_DB.exists():
        return 0.0
    try:
        with sqlite3.connect(CT_DB) as conn:
            # Total trading days with any cycle in the window
            total = conn.execute(
                "SELECT COUNT(DISTINCT DATE(ts)) FROM ct_events WHERE DATE(ts) BETWEEN ? AND ?",
                (start_date, end_date),
            ).fetchone()[0]
            # Days where THIS symbol appeared
            hits = conn.execute(
                """
                SELECT COUNT(DISTINCT DATE(ts)) FROM ct_events
                WHERE DATE(ts) BETWEEN ? AND ?
                  AND (event_type LIKE '%opportunity%' OR event_type LIKE '%equity%')
                  AND json_extract(payload, '$.symbol') = ?
                """,
                (start_date, end_date, symbol),
            ).fetchone()[0]
        return hits / max(total, 1)
    except Exception as e:
        log.debug("[ILC-Verify] scan_hit_rate error for %s: %s", symbol, e)
        return 0.0


def _decision_confidence(symbol: str, start_date: str, end_date: str) -> float:
    """Average decision confidence for a symbol in a date range."""
    if not CT_DB.exists():
        return 0.0
    try:
        with sqlite3.connect(CT_DB) as conn:
            row = conn.execute(
                """
                SELECT AVG(CAST(d.confidence AS REAL))
                FROM ct_decisions d
                LEFT JOIN ct_cycles c ON d.cycle_id = c.cycle_id
                WHERE DATE(COALESCE(d.created_at, c.started_at)) BETWEEN ? AND ?
                  AND d.symbol = ?
                """,
                (start_date, end_date, symbol),
            ).fetchone()
        return float(row[0] or 0.0)
    except Exception as e:
        log.debug("[ILC-Verify] decision_confidence error for %s: %s", symbol, e)
        return 0.0


def _win_rate(symbol: str, start_date: str, end_date: str) -> float:
    """Win rate from paper trades CSV for a symbol in a date range."""
    # Journal housekeeping reasons — synthetic closes with no real market
    # outcome. Including them would dilute win rates with zero-PnL rows.
    _SKIP_REASONS = {
        "PAPER_MODE_ARTIFACT",          # ORJ-001 reconciliation
        "SESSION_EXPIRED_DEEP_ORPHAN",  # Pass 1.9 reconciliation
        "SYSTEM_CLEANUP",
        "ORPHAN_CLOSE",
        "emergency_close",
        "close_emergency",
    }
    if not PAPER_TRADES_CSV.exists():
        return 0.0
    try:
        import csv
        wins, total = 0, 0
        with open(PAPER_TRADES_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ts = row.get("timestamp", "")[:10]
                if ts < start_date or ts > end_date:
                    continue
                if row.get("event", "").upper() != "CLOSE":
                    continue
                if symbol and row.get("symbol", "") != symbol:
                    continue
                if row.get("reason", "") in _SKIP_REASONS:
                    continue
                pnl = float(row.get("pnl", 0) or 0)
                total += 1
                if pnl > 0:
                    wins += 1
        return wins / max(total, 1) if total > 0 else 0.0
    except Exception as e:
        log.debug("[ILC-Verify] win_rate error for %s: %s", symbol, e)
        return 0.0


def _dna_count(symbol: str) -> float:
    """Count active DNA records for a symbol."""
    from .ilc_config import DNA_DB
    if not DNA_DB.exists():
        return 0.0
    try:
        with sqlite3.connect(DNA_DB) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM consensus_dna WHERE symbol=? AND status IN ('ACTIVE','PROMOTED')",
                (symbol,),
            ).fetchone()
        return float(row[0] or 0)
    except Exception:
        return 0.0


def _measure_metric(metric_name: str, symbol: str, start_date: str, end_date: str) -> float:
    """Dispatch to the appropriate metric function."""
    if metric_name == "scan_hit_rate":
        return _scan_hit_rate(symbol, start_date, end_date)
    if metric_name == "decision_confidence":
        return _decision_confidence(symbol, start_date, end_date)
    if metric_name == "win_rate":
        return _win_rate(symbol, start_date, end_date)
    if metric_name == "dna_count":
        return _dna_count(symbol)
    return 0.0


def _capture_baseline(action, metric_name: str) -> Dict[str, float]:
    """Capture baseline metrics at action creation time (last 30 trading days)."""
    end_date   = date.today().isoformat()
    start_date = (date.today() - timedelta(days=45)).isoformat()  # ~30 trading days
    baseline   = _measure_metric(metric_name, action.symbol, start_date, end_date)
    return {metric_name: baseline}


def _pick_metric_for_category(category: str) -> str:
    """Choose the most appropriate prediction metric for a learning category."""
    return {
        "A": "decision_confidence",   # calibration → improves confidence
        "B": "scan_hit_rate",         # knowledge reinforcement → better scan
        "C": "scan_hit_rate",         # hypothesis → scanner improvement
        "D": "win_rate",              # research → should improve P&L
        "E": "dna_count",             # DNA candidate → more DNA records
        "F": "scan_hit_rate",         # HKAP → scanner finds historical patterns
        "G": "scan_hit_rate",         # KDE → relationship discovery
    }.get(category, "scan_hit_rate")


# ── Verification date logic ───────────────────────────────────────────────────

def _verification_dates(created_date: str) -> Dict[int, str]:
    """Compute calendar dates for each verification window."""
    created = datetime.strptime(created_date, "%Y-%m-%d").date()
    result  = {}
    for window_days in VERIFICATION_WINDOWS:
        cal_days = CALENDAR_DAYS_MAP.get(window_days, window_days * 1.5)
        verify_date = created + timedelta(days=int(cal_days))
        result[window_days] = verify_date.isoformat()
    return result


def _is_due(record: LearningRecord, today: str) -> Optional[int]:
    """
    Return the next verification window (days) that is due today, or None.
    A window is due if today >= verification_date AND that window hasn't been measured yet.
    """
    v_dates = _verification_dates(record.created_date)
    measured_windows = {vr.window_days for vr in record.verification_results}

    for window in sorted(VERIFICATION_WINDOWS):
        if window in measured_windows:
            continue
        if today >= v_dates.get(window, "9999-99-99"):
            return window
    return None


# ── Core verification logic ───────────────────────────────────────────────────

def _run_verification(record: LearningRecord, window_days: int, today: str) -> VerificationResult:
    """Measure current metric and compare to baseline to determine verdict."""
    metric_name    = record.prediction_metric
    baseline_value = record.baseline_metrics.get(metric_name, 0.0)

    # Measurement window: from creation to today
    start_date = record.created_date
    end_date   = today

    measured_value = _measure_metric(metric_name, record.symbol, start_date, end_date)

    # Compute relative change
    if baseline_value > 0:
        change_pct = (measured_value - baseline_value) / baseline_value
    elif measured_value > 0:
        change_pct = 1.0   # went from 0 to something → improvement
    else:
        change_pct = 0.0   # stayed at 0

    if change_pct >= IMPROVEMENT_THRESHOLD:
        verdict  = "IMPROVED"
        promoted = True
    elif change_pct <= DECLINE_THRESHOLD:
        verdict  = "DECLINED"
        promoted = False
    else:
        verdict  = "NO_CHANGE"
        promoted = False

    retired     = (verdict == "DECLINED" and window_days == max(VERIFICATION_WINDOWS))
    action_taken = (
        "PROMOTED to institutional knowledge" if promoted
        else "RETIRED — knowledge rolled back" if retired
        else "Downgraded confidence" if verdict == "NO_CHANGE"
        else ""
    )

    return VerificationResult(
        learning_id=record.learning_id,
        window_days=window_days,
        verification_date=_verification_dates(record.created_date)[window_days],
        measured_date=today,
        metric_name=metric_name,
        baseline_value=round(baseline_value, 4),
        measured_value=round(measured_value, 4),
        change_pct=round(change_pct, 4),
        verdict=verdict,
        promoted=promoted,
        retired=retired,
        action_taken=action_taken,
    )


def _update_record_status(record: LearningRecord) -> None:
    """Update the overall record status based on all completed verifications."""
    if not record.verification_results:
        record.status = "PENDING"
        return

    verdicts    = [vr.verdict for vr in record.verification_results]
    any_retired = any(vr.retired for vr in record.verification_results)
    any_promoted = any(vr.promoted for vr in record.verification_results)

    if any_retired:
        record.status = "RETIRED"
    elif any_promoted:
        record.status = "IMPROVED"
    elif len(verdicts) < len(VERIFICATION_WINDOWS):
        record.status = "MEASURING"
    elif all(v == "NO_CHANGE" for v in verdicts):
        record.status = "NO_CHANGE"
        # Downgrade confidence
        if record.confidence == LearningConfidence.HIGH:
            record.confidence = LearningConfidence.MEDIUM
        elif record.confidence == LearningConfidence.MEDIUM:
            record.confidence = LearningConfidence.LOW
    elif "DECLINED" in verdicts:
        record.status = "DECLINED"


# ── Public API ────────────────────────────────────────────────────────────────

def register_learning_actions(
    actions: list,
    confidences: List[str],
    eig_results: list,
    today: str,
    dry_run: bool = False,
) -> List[LearningRecord]:
    """
    Register new learning actions in the persistent registry.
    Existing actions (same symbol + category + date) are deduplicated.

    Returns the newly created LearningRecord objects.
    """
    with _REGISTRY_LOCK:
        registry = _load_registry()
        existing_keys = {
            (r.created_date, r.symbol, r.category)
            for r in registry
        }

        eig_map = {e.action_id: e for e in eig_results}
        new_records: List[LearningRecord] = []

        for action, conf in zip(actions, confidences):
            key = (today, action.symbol, action.category)
            if key in existing_keys:
                continue

            metric_name = _pick_metric_for_category(action.category)
            baseline    = _capture_baseline(action, metric_name)
            eig_r       = eig_map.get(action.action_id)
            eig_score   = eig_r.eig_score if eig_r else 0.0

            rec = LearningRecord(
                learning_id=action.action_id,
                created_date=today,
                action_type=action.action_type,
                category=action.category,
                symbol=action.symbol,
                description=action.description,
                target_system=action.target_system,
                expected_benefit=(
                    f"Improve {metric_name} for {action.symbol} via {action.target_system}"
                ),
                prediction_metric=metric_name,
                baseline_metrics=baseline,
                confidence=conf,
                eig_score=eig_score,
                executed=action.scheduled,
                outcome=action.outcome,
            )
            new_records.append(rec)
            existing_keys.add(key)

        if not dry_run and new_records:
            registry.extend(new_records)
            _save_registry(registry)
            log.info("[ILC-Verify] Registered %d new learning records", len(new_records))

        return new_records


def run_verification_pass(today: str, dry_run: bool = False) -> List[VerificationResult]:
    """
    Check all learning records for due verifications.
    Runs measurement, assigns verdict, updates registry.

    Returns all VerificationResult objects generated today.
    """
    with _REGISTRY_LOCK:
        registry = _load_registry()
        new_results: List[VerificationResult] = []
        changed = False

        for record in registry:
            if record.status == "RETIRED":
                continue

            due_window = _is_due(record, today)
            if due_window is None:
                continue

            log.info(
                "[ILC-Verify] Measuring %d-day window for %s %s (id=%s)",
                due_window, record.symbol, record.category, record.learning_id,
            )

            vr = _run_verification(record, due_window, today)
            record.verification_results.append(vr)
            _update_record_status(record)
            new_results.append(vr)
            changed = True

            log.info(
                "[ILC-Verify] %s %s → %s (baseline=%.3f measured=%.3f Δ=%.1f%%)",
                record.symbol, record.category, vr.verdict,
                vr.baseline_value, vr.measured_value, vr.change_pct * 100,
            )

        if not dry_run and changed:
            _save_registry(registry)

    n_improved  = sum(1 for r in new_results if r.verdict == "IMPROVED")
    n_no_change = sum(1 for r in new_results if r.verdict == "NO_CHANGE")
    n_declined  = sum(1 for r in new_results if r.verdict == "DECLINED")
    log.info(
        "[ILC-Verify] Pass complete: checked=%d improved=%d no_change=%d declined=%d",
        len(new_results), n_improved, n_no_change, n_declined,
    )
    return new_results


def get_all_records() -> List[LearningRecord]:
    """Return all records from the registry (read-only)."""
    return _load_registry()
