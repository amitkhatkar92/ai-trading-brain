"""
hkap/hkap_kde_bridge.py
==========================
Self-Learning Ecosystem — Phase 6: HKAP -> KDE evidence expansion.

Original roadmap wording ("reuses DTA-031's historical-replay bridge
shape") turned out to be a structural mismatch, found during audit before
any code was written: DTA-031's bridge writes per-(symbol, date) trade
OUTCOME records (entry/target/stop/T+1..T+5 returns) that
HistoricalBehaviourEngine.load_outcomes() globs. HKAP does not produce
anything in that shape -- its finest granularity is a per-DNA-id,
per-YEAR aggregate statistic (hkap/hkap_models.py: YearDNASnapshot /
CrossYearDNARecord / CrossYearEdgeRecord), not a trade outcome. Building
a literal DTA-031-shaped bridge would require FABRICATING a concrete
entry/target/stop/return HKAP never computed -- the same fabrication
risk already rejected for PGA Category A. Not done.

Instead, this bridges HKAP's REAL output into kde/ (Knowledge Discovery
Engine) -- confirmed via test_kde.py to be the purpose-built, structurally
correct consumer for exactly HKAP's shape (hkap_packages/dna_records/
edge_records), previously also fully disconnected from any pipeline.

KBL stages:
  ACQUISITION  : HKAPEngine.run()/run_year() (already exists, unchanged --
               a separate, deliberate, manual/costly step; see
               scripts note below). This module NEVER triggers a
               download or a year run itself.
  VALIDATION   : CrossYearAnalyzer's own lifecycle/confidence
               classification (already exists, unchanged) + KDE's own
               min_raw_score/min_overall_score promotion gate (already
               exists, unchanged) -- no new statistical gate invented here.
  SYNTHESIS    : KDEEngine.run() -- already exists, unchanged.
  PROPAGATION  : run_hkap_kde_discovery() persists an append-only summary
               to data/kde/bridge/run_history.jsonl;
               get_latest_discovery_run() is a read-only accessor for a
               future dashboard/Telegram command.
  GOVERNANCE   : advisory/research-only. Deliberately NOT wired into
               master_orchestrator.py's daily EOD loop -- HKAP/KDE are a
               periodic, multi-year HISTORICAL research computation, not
               a daily live-trading event (unlike Phase 4/5). Not wired
               into HBE/KDA either, for the same fabrication-risk reason
               ACQUISITION above avoids DTA-031's literal shape. Callable
               on whatever cadence a human or a future scheduler chooses.

Real HKAP data must exist on disk first (run HKAPEngine.run(years=...)
separately -- see the one-time seed script used to produce the first
real 2023-2024/40-symbol dataset this phase). This module only reads
what is ALREADY persisted; it never downloads anything.

Safety contract: read-only w.r.t. all trading/decision state. Writes only
to data/kde/reports/ (KDE's own existing report writer) and
data/kde/bridge/run_history.jsonl (new, append-only). Zero imports from
execution_engine, order_manager, broker APIs, risk_control, or
knowledge_authority. Never raises.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR  = os.path.join(_ROOT, "data", "kde", "bridge")
HISTORY_FILE = os.path.join(HISTORY_DIR, "run_history.jsonl")

MIN_YEARS_FOR_DISCOVERY = 2  # KDE/CrossYearAnalyzer both require >=2 years


def run_hkap_kde_discovery(min_years: int = MIN_YEARS_FOR_DISCOVERY) -> Dict[str, Any]:
    """
    Load already-persisted HKAP year packages (no download), run
    CrossYearAnalyzer + KDEEngine over them, and persist a summary record.
    Never raises. Returns a dict describing what happened.
    """
    try:
        return _run_impl(min_years)
    except Exception as exc:
        log.debug("[HKAPKDEBridge] discovery run error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl(min_years: int) -> Dict[str, Any]:
    from hkap.hkap_engine import HKAPEngine
    from hkap.cross_year_analyzer import CrossYearAnalyzer
    from kde.kde_engine import KDEEngine
    from kde.kde_config import KDEConfig

    engine = HKAPEngine()  # loads whatever is already on disk; no network calls
    packages = engine.get_completed_packages()

    if len(packages) < min_years:
        return {
            "status": "INSUFFICIENT_YEARS",
            "years_available": sorted(packages.keys()),
            "min_years_required": min_years,
        }

    dna_records, edge_records = CrossYearAnalyzer().analyze(packages)

    kde = KDEEngine(KDEConfig())
    result = kde.run(packages, dna_records, edge_records)

    top = sorted(result.discoveries, key=lambda d: -d.score.overall)[:10]
    summary = {
        "status":              "OK",
        "generated_at":        datetime.now(timezone.utc).isoformat(),
        "years_used":          sorted(packages.keys()),
        "dna_record_count":    len(dna_records),
        "edge_record_count":   len(edge_records),
        "total_discoveries":   len(result.discoveries),
        "high_value_count":    result.statistics.high_value_count,
        "avg_score":           result.statistics.avg_score,
        "top_discoveries": [
            {
                "discovery_id": d.discovery_id,
                "scheme_id":    d.scheme_id,
                "answer":       d.answer,
                "score":        d.score.overall,
                "potential_value": d.potential_value,
            }
            for d in top
        ],
        "reports": result.reports,
    }
    _record_run(summary)
    return summary


def _record_run(summary: Dict[str, Any]) -> None:
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")
    except Exception as exc:
        log.debug("[HKAPKDEBridge] history write skipped: %s", exc)


def get_latest_discovery_run() -> Optional[Dict[str, Any]]:
    """Read-only accessor for a future dashboard/Telegram command. Never raises."""
    try:
        if not os.path.exists(HISTORY_FILE):
            return None
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
        return json.loads(lines[-1]) if lines else None
    except Exception:
        return None


def get_discovery_run_history(n: int = 10) -> List[Dict[str, Any]]:
    """Return the last n recorded discovery runs, oldest first. Never raises."""
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
        return [json.loads(ln) for ln in lines[-n:]]
    except Exception:
        return []
