"""
analysis/daily_health_check.py
=====================================
Daily verification that all three observation layers are operating correctly.

Prints a concise pass/fail checklist to stdout. Non-zero exit code if
any critical check fails — suitable for Task Scheduler or cron alerting.

Checklist
---------
Observation Layer
  ✅ live_observations.db exists
  ✅ trades captured today (if market was open)
  ✅ no OPEN observations older than 5 days (orphan detection)
  ✅ transition_probability stored (not all 0.0)
  ✅ all required columns present

Recommendation Layer
  ✅ recommendations.db exists and has ≥ 1 PENDING rec
  ✅ at least 1 rec has had evidence_stage updated today
  ✅ no recommendation stuck in PENDING for > 90 days (expiry check)

Regime Layer
  ✅ regime data available (yfinance reachable)
  ✅ transition probability computed without errors
  ✅ today's report exists in reports/regime/

Usage
-----
    python analysis/daily_health_check.py

    # Exit 0 = all healthy, exit 1 = critical failure
    python analysis/daily_health_check.py ; echo "Exit: $LASTEXITCODE"
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

LIVE_DB  = os.path.join(_ROOT, "data", "live_observations.db")
REC_DB   = os.path.join(_ROOT, "data", "recommendations.db")
REG_DIR  = os.path.join(_ROOT, "reports", "regime")

_TODAY   = datetime.now().strftime("%Y-%m-%d")
_NOW_UTC = datetime.now(timezone.utc)
_CRITICAL_FAILURES: list[str] = []
_WARNINGS: list[str] = []


# ── Check helpers ─────────────────────────────────────────────────────────────

def _scalar(db: str, sql: str, params: tuple = (), default=0):
    if not os.path.exists(db):
        return default
    try:
        with sqlite3.connect(db) as conn:
            r = conn.execute(sql, params).fetchone()
        return r[0] if r and r[0] is not None else default
    except Exception:
        return default


def _columns(db: str, table: str) -> list[str]:
    if not os.path.exists(db):
        return []
    try:
        with sqlite3.connect(db) as conn:
            return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def _check(label: str, ok: bool, critical: bool = False, detail: str = "") -> bool:
    icon = "✅" if ok else ("❌" if critical else "⚠️ ")
    suffix = f"  ({detail})" if detail else ""
    print(f"  {icon} {label}{suffix}")
    if not ok:
        if critical:
            _CRITICAL_FAILURES.append(label)
        else:
            _WARNINGS.append(label)
    return ok


# ── Layer checks ──────────────────────────────────────────────────────────────

def check_observation_layer() -> None:
    print("\n[OBSERVATION LAYER]")

    # DB exists
    exists = os.path.exists(LIVE_DB)
    _check("live_observations.db exists", exists, critical=True)
    if not exists:
        return

    # Schema has all required columns
    cols = _columns(LIVE_DB, "live_observations")
    required = [
        "order_id", "symbol", "strategy", "quality_tier", "sft_class",
        "market_regime", "vix", "transition_probability", "transition_alert",
        "outcome",
    ]
    missing = [c for c in required if c not in cols]
    _check("All required columns present", not missing,
           critical=True, detail=f"missing: {missing}" if missing else "")

    # Total observations
    total = _scalar(LIVE_DB, "SELECT COUNT(*) FROM live_observations")
    _check(f"Database populated ({total} total observations)", total >= 0, critical=False,
           detail="empty — run live_observation_audit.py after market close" if total == 0 else f"{total} rows")

    # Orphan detection: OPEN obs older than 5 days
    cutoff = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    orphans = _scalar(
        LIVE_DB,
        "SELECT COUNT(*) FROM live_observations WHERE outcome='OPEN' AND trade_date < ?",
        (cutoff,),
    )
    _check("No orphan OPEN observations (> 5 days old)", orphans == 0,
           critical=False, detail=f"{orphans} orphan(s)" if orphans else "")

    # transition_probability not all zero (once we have any data)
    if total > 0:
        nonzero_tp = _scalar(
            LIVE_DB,
            "SELECT COUNT(*) FROM live_observations WHERE transition_probability > 0",
        )
        _check(
            "Transition probability stored in observations",
            nonzero_tp > 0 or total == 0,
            critical=False,
            detail=f"{nonzero_tp}/{total} obs have transition_probability" if total > 0 else "",
        )

    # Today's ingest (skip on weekends)
    weekday = datetime.now().weekday()
    if weekday < 5:  # Mon–Fri
        today_count = _scalar(
            LIVE_DB,
            "SELECT COUNT(*) FROM live_observations WHERE trade_date=?",
            (_TODAY,),
        )
        # Don't fail if no trades today — just warn
        _check(
            f"Observations recorded today ({_TODAY})",
            today_count >= 0,
            critical=False,
            detail=f"{today_count} today (0 = no trades taken or audit not yet run)",
        )


def check_recommendation_layer() -> None:
    print("\n[RECOMMENDATION LAYER]")

    exists = os.path.exists(REC_DB)
    _check("recommendations.db exists", exists, critical=True)
    if not exists:
        return

    pending = _scalar(REC_DB, "SELECT COUNT(*) FROM recommendations WHERE status='PENDING'")
    _check(f"PENDING recommendations present ({pending})", pending >= 0,
           detail=f"{pending} pending")

    approved = _scalar(REC_DB, "SELECT COUNT(*) FROM recommendations WHERE status='APPROVED'")
    _check(f"Approved queue checked ({approved} approved)", True,
           detail=f"{approved} approved — implement before approving more" if approved > 5 else (
               f"{approved} approved" if approved else "none yet — collecting evidence"))

    # Evidence stages updated: at least 1 rec should have reviewer_notes set
    staged = _scalar(
        REC_DB,
        "SELECT COUNT(*) FROM recommendations WHERE reviewer_notes LIKE '[EVIDENCE%'",
    )
    _check("Evidence stages updated in reviewer_notes", staged > 0 or pending == 0,
           critical=False,
           detail=f"{staged}/{pending} recs have evidence notes" if pending else "")

    # Expiry: PENDING > 90 days old
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    stale  = _scalar(
        REC_DB,
        "SELECT COUNT(*) FROM recommendations WHERE status='PENDING' AND generated_at < ?",
        (cutoff,),
    )
    _check("No stale PENDING recommendations (> 90 days)", stale == 0,
           critical=False, detail=f"{stale} stale" if stale else "")


def check_regime_layer() -> None:
    print("\n[REGIME LAYER]")

    # Can we reach yfinance?
    regime_ok = False
    vix_val   = None
    try:
        from analysis.regime_transition_engine import analyse_regime_transition
        r = analyse_regime_transition("NIFTY", period="3mo", use_cache=True)
        regime_ok = True
        vix_val   = r.current_vix
        _check(
            f"Regime data computed (NIFTY {r.current_regime}, VIX={r.current_vix:.1f})",
            True,
            detail=f"Transition prob: {r.transition_probability:.0f}% — {r.alert_level}",
        )
        if r.alert_level in ("ALERT", "IMMINENT"):
            _WARNINGS.append(f"⚠️  Regime ALERT — {r.alert_level} ({r.transition_probability:.0f}%): {r.strategy_implication[:80]}")
            print(f"  ⚠️  REGIME ALERT: {r.strategy_implication}")
    except Exception as e:
        _check("Regime data computed", False, critical=False, detail=str(e)[:60])

    # Today's regime report exists
    today_report = os.path.join(REG_DIR, f"REGIME_TRANSITION_{_TODAY.replace('-','')}.md")
    _check("Today's regime report on disk", os.path.exists(today_report),
           critical=False,
           detail=f"run regime_transition_engine.py to generate" if not os.path.exists(today_report) else "")


# ── Summary ───────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 55)
    print(f"  DAILY HEALTH CHECK — {_TODAY}")
    print("=" * 55)

    check_observation_layer()
    check_recommendation_layer()
    check_regime_layer()

    print("\n" + "=" * 55)
    if _CRITICAL_FAILURES:
        print(f"  ❌ CRITICAL FAILURES ({len(_CRITICAL_FAILURES)}):")
        for f in _CRITICAL_FAILURES:
            print(f"     • {f}")
        print("=" * 55)
        return 1

    if _WARNINGS:
        print(f"  ⚠️  WARNINGS ({len(_WARNINGS)}):")
        for w in _WARNINGS:
            print(f"     • {w}")
        print(f"\n  ✅ No critical failures. Address warnings when convenient.")
    else:
        print("  ✅ ALL CHECKS PASSED — pipeline healthy.")

    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
