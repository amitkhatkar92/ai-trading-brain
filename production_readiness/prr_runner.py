"""
production_readiness/prr_runner.py — PRR-001 Main Runner.

Orchestrates all 9 phases, generates all reports, returns a summary dict.

Usage:
    python -m production_readiness.prr_runner [--date YYYY-MM-DD] [--dry-run] [--json]

Called by orchestrator._do_eod_learning() via run_prr().
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


def _collect_prr_data(today: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Run all PRR-001 phases and collect their outputs into a single dict.
    Each phase is failure-isolated.
    """
    data: Dict[str, Any] = {"date": today}

    # ── Phase 1: Edge Gate ──────────────────────────────────────────────
    try:
        from .ph1_edge_gate import get_edge_gate_summary, patch_knowledge_provider
        patch_knowledge_provider()
        data["edge_gate"] = get_edge_gate_summary()
    except Exception as e:
        log.warning("[PRR] Phase 1 failed: %s", e)
        data["edge_gate"] = None

    # ── Phase 2: SHORT DNA ──────────────────────────────────────────────
    try:
        from .ph2_short_dna import run_short_dna_audit
        # Gather current features from market intelligence if available
        features = _get_market_features()
        regime   = _get_current_regime()
        data["short_dna"] = run_short_dna_audit(features=features, regime=regime, today=today)
    except Exception as e:
        log.warning("[PRR] Phase 2 failed: %s", e)
        data["short_dna"] = None

    # ── Phase 3: Signal Freshness ───────────────────────────────────────
    try:
        from .ph3_signal_freshness import build_freshness_report
        signals = _get_recent_signals()
        data["freshness"] = build_freshness_report(signals, today=today)
    except Exception as e:
        log.warning("[PRR] Phase 3 failed: %s", e)
        data["freshness"] = None

    # ── Phase 4: Universe Coverage ──────────────────────────────────────
    try:
        from .ph4_universe import build_universe_coverage_report
        data["universe"] = build_universe_coverage_report(today=today)
    except Exception as e:
        log.warning("[PRR] Phase 4 failed: %s", e)
        data["universe"] = None

    # ── Phase 5: Daily Pipeline (included if already run; not re-run) ────
    # Phase 5 is run separately by orchestrator; here we just slot the result in
    data.setdefault("pipeline", None)

    # ── Phase 6: Knowledge Validity ─────────────────────────────────────
    try:
        from .ph6_knowledge_validity import build_knowledge_validity_report
        data["knowledge_validity"] = build_knowledge_validity_report(today=today)
    except Exception as e:
        log.warning("[PRR] Phase 6 failed: %s", e)
        data["knowledge_validity"] = None

    # ── Phase 7: Missed Opportunities ───────────────────────────────────
    try:
        from .ph7_missed_opps import build_missed_opportunity_report
        misses = _get_todays_misses()
        data["missed_opps"] = build_missed_opportunity_report(misses, today=today)
    except Exception as e:
        log.warning("[PRR] Phase 7 failed: %s", e)
        data["missed_opps"] = None

    # ── Phase 8: Learning Impact ─────────────────────────────────────────
    try:
        from .ph8_learning_impact import get_learning_impact_summary
        data["learning_impact"] = get_learning_impact_summary(today=today)
    except Exception as e:
        log.warning("[PRR] Phase 8 failed: %s", e)
        data["learning_impact"] = None

    # ── Phase 9: Certification ───────────────────────────────────────────
    try:
        from .ph9_certification import build_certificate
        ils_score = _get_ils_score(data)
        gva_score = _get_gva_score()
        data["certificate"] = build_certificate(
            edge_gate          = data.get("edge_gate"),
            short_dna          = data.get("short_dna"),
            freshness          = data.get("freshness"),
            universe           = data.get("universe"),
            pipeline           = data.get("pipeline"),
            knowledge_validity = data.get("knowledge_validity"),
            learning_impact    = data.get("learning_impact"),
            ils_score          = ils_score,
            gva_score          = gva_score,
            today              = today,
        )
    except Exception as e:
        log.warning("[PRR] Phase 9 failed: %s", e)
        data["certificate"] = None

    return data


def run_prr(
    report_date: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Top-level entry point — runs all 9 PRR phases, writes 9 reports.
    Returns a summary dict for the orchestrator to log.
    """
    today = report_date or datetime.now().date().isoformat()
    t0 = time.monotonic()
    log.info("[PRR-001] ── Starting PRR pipeline for %s (dry_run=%s) ──", today, dry_run)

    data = _collect_prr_data(today, dry_run=dry_run)

    # Write reports (non-dry-run only)
    if not dry_run:
        try:
            from .prr_reporter import write_all_reports
            write_all_reports(data, today=today)
        except Exception as e:
            log.warning("[PRR-001] Report writing failed: %s", e)

    cert = data.get("certificate")
    verdict = getattr(cert, "verdict", "UNKNOWN") if cert else "UNKNOWN"
    elapsed = time.monotonic() - t0

    log.info(
        "[PRR-001] Complete in %.1fs | verdict=%s ils=%.1f gva=%.1f",
        elapsed,
        verdict,
        getattr(cert, "ils_score", 0.0) if cert else 0.0,
        getattr(cert, "gva_score", 0.0) if cert else 0.0,
    )

    return {
        "date":                 today,
        "certification_status": verdict,
        "ils_score":            getattr(cert, "ils_score", 0.0) if cert else 0.0,
        "gva_score":            getattr(cert, "gva_score", 0.0) if cert else 0.0,
        "critical_failures":    getattr(cert, "critical_failures", 0) if cert else 0,
        "warnings":             getattr(cert, "warnings", 0) if cert else 0,
        "elapsed_seconds":      round(elapsed, 2),
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_market_features() -> Dict[str, float]:
    """Try to load current market features from MarketIntelligence snapshot."""
    try:
        from market_intelligence.market_intelligence_ai import MarketIntelligenceAI
        mi = MarketIntelligenceAI()
        snap = mi.get_snapshot()
        if snap and hasattr(snap, "__dict__"):
            raw = {k: v for k, v in vars(snap).items() if isinstance(v, (int, float))}
            return raw
    except Exception:
        pass
    return {}


def _get_current_regime() -> str:
    """Get current market regime label."""
    try:
        from market_intelligence.market_intelligence_ai import MarketIntelligenceAI
        mi = MarketIntelligenceAI()
        snap = mi.get_snapshot()
        regime = getattr(snap, "regime", None)
        if regime:
            return getattr(regime, "value", str(regime))
    except Exception:
        pass
    return "UNKNOWN"


def _get_recent_signals() -> list:
    """Load recent TradeSignal objects from the trade log/paper trades."""
    try:
        import csv
        from pathlib import Path
        from datetime import datetime
        signals_path = Path("data/paper_trades.csv")
        if not signals_path.exists():
            return []
        # Build minimal mock objects with just the timestamp attribute
        class _Mock:
            def __init__(self, symbol, ts_str):
                self.symbol = symbol
                try:
                    self.timestamp = datetime.fromisoformat(ts_str)
                except Exception:
                    self.timestamp = datetime.now()
        mocks = []
        with open(signals_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get("symbol", "")
                ts  = row.get("timestamp", "") or row.get("entry_time", "")
                if sym and ts:
                    mocks.append(_Mock(sym, ts))
        return mocks[-200:]   # last 200 signals
    except Exception:
        return []


def _get_todays_misses() -> list:
    """Get today's missed opportunities from the PGA analysis if available."""
    try:
        from pathlib import Path
        import json as _json
        from datetime import datetime
        today_s = datetime.now().date().isoformat()
        pga_dir = Path("data/pga") / today_s
        miss_file = pga_dir / "missed_opportunities.json"
        if miss_file.exists():
            return _json.loads(miss_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _get_ils_score(data: Dict[str, Any]) -> float:
    """Extract ILS score from today's ILC result if available."""
    try:
        from institutional_learning.ilc_score import compute_ils_score
        # Try to load today's ILC records
        from institutional_learning.ilc_verification import get_all_records, run_verification_pass
        from institutional_learning.ilc_roi import compute_all_roi
        from institutional_learning.ilc_lifecycle import update_lifecycle
        records   = get_all_records()
        verified  = run_verification_pass(dry_run=True)
        roi_list  = compute_all_roi(records)
        lifecycle = update_lifecycle(verified, dry_run=True)
        ils = compute_ils_score(records, verified, lifecycle, roi_list)
        return getattr(ils, "overall_score", 0.0)
    except Exception:
        return 0.0


def _get_gva_score() -> float:
    """Get current GVA score."""
    try:
        from growth_validator.growth_validator_ai import GrowthValidatorAI
        gva = GrowthValidatorAI()
        result = gva.run_daily_validation()
        if hasattr(result, "score"):
            return float(result.score)
        if isinstance(result, dict):
            return float(result.get("score", 0.0))
    except Exception:
        pass
    return 0.0


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _main():
    parser = argparse.ArgumentParser(description="PRR-001 Production Readiness Runner")
    parser.add_argument("--date",    default=None, help="Report date YYYY-MM-DD (default: today)")
    parser.add_argument("--dry-run", action="store_true", help="Skip writing reports to disk")
    parser.add_argument("--json",    action="store_true", help="Print result as JSON")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    result = run_prr(report_date=args.date, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n{'='*60}")
        print(f"  PRR-001 Production Readiness — {result['date']}")
        print(f"{'='*60}")
        print(f"  Verdict:          {result['certification_status']}")
        print(f"  ILS Score:        {result['ils_score']:.1f}/100")
        print(f"  GVA Score:        {result['gva_score']:.1f}/100")
        print(f"  Critical failures: {result['critical_failures']}")
        print(f"  Observations:      {result['warnings']}")
        print(f"  Elapsed:           {result['elapsed_seconds']:.1f}s")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    _main()
