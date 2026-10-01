"""
validation_engine/validation_history.py
=========================================
Research-only persistence for ValidationEngine's own ValidationReport output.

ROOT-CAUSE CONTEXT (information-utilization audit, 2026-10-01):
ValidationEngine.validate() already runs daily at EOD (gated on >=30 official
trades, see orchestrator/master_orchestrator.py) and already logs its own
verdict via [ValidationReport]/[ValidationEngine] log lines -- but the
returned ValidationReport object itself was discarded by the only call site,
so nothing could query "what was the last verdict" or see a trend over time.

This module closes that gap the same additive, read-only way every other
evidence log in this repo does: append-only JSONL + read-only accessors.
Advisory/observability only -- does NOT gate any trade, strategy enable/
disable, or capital decision. ValidationEngine's own verdict computation is
completely unchanged.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "validation_engine"
)
_HISTORY_PATH = os.path.join(_DATA_DIR, "portfolio_validation_history.jsonl")


def record_validation_report(report: Any, trading_date: Optional[str] = None) -> None:
    """Append-only snapshot of a ValidationReport. Fails open (never raises)."""
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        record = {
            "trading_date": trading_date or datetime.now(timezone.utc).date().isoformat(),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "strategy_name": getattr(report, "strategy_name", "?"),
            "overall_score": getattr(report, "overall_score", 0.0),
            "verdict": getattr(report, "verdict", "PENDING"),
            "stage_scores": [
                {
                    "stage": s.stage, "passed": s.passed,
                    "score": s.score, "weight": s.weight,
                }
                for s in getattr(report, "stage_scores", []) or []
            ],
        }
        with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass


def get_validation_report_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only accessor -- last n recorded reports, oldest-first."""
    if not os.path.exists(_HISTORY_PATH):
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out[-n:] if n else out


def get_latest_validation_report() -> Optional[Dict[str, Any]]:
    """Read-only accessor -- the most recently recorded report, or None."""
    hist = get_validation_report_history(n=1)
    return hist[-1] if hist else None
