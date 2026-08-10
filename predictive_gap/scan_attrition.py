"""predictive_gap/scan_attrition.py — Daily scan-attrition staging file.

Writes a per-symbol record each time a stock is evaluated by the scanner or
StrategyLab but does NOT generate an actionable opportunity.  This lets PGA
distinguish:

    IN_UNIVERSE_NOT_SCANNED  — in universe but never entered scanner batch
    SCANNED_NO_SIGNAL        — in scanner watchlist; price evaluated; no signal
    SCANNED_SIGNAL_REJECTED  — signal generated; StrategyLab rejected it

Each record is appended to data/scan_attrition/YYYY-MM-DD.jsonl during the
trading day.  The PGA collector reads the file at 15:35 IST.

This is an AUDIT/EVIDENCE trail only.
- No decision logic is modified.
- No thresholds are changed.
- No order is created or cancelled.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

ROOT              = Path(__file__).parent.parent
ATTRITION_DIR     = ROOT / "data" / "scan_attrition"

# Rejection stage constants (written to scanner_stage field)
STAGE_SCANNER_NO_SIGNAL   = "SCANNER_NO_SIGNAL"
STAGE_STRATEGY_LAB_REJECT = "STRATEGY_LAB_REJECT"

_WRITE_LOCK = threading.Lock()


@dataclass
class ScanAttritionRecord:
    date: str               # YYYY-MM-DD
    timestamp: str          # ISO-8601
    symbol: str
    scan_cycle: str         # "intraday_cycle_N" | "deep_scan_NAME" | "phase_d"
    scanner_stage: str      # STAGE_* constant
    strategy: str           # strategy name if assigned, else ""
    regime: str             # market regime at scan time
    scanner_score: float    # confidence or quality score (0 if not available)
    threshold_used: float   # threshold that was not met (0 if not applicable)
    rejection_reason: str   # e.g. "BACKTEST_GATE_FAIL", "RR_2.1_below_min_2.5"
    is_actionable: bool     # False for attrition records (always)
    source: str             # "EquityScannerAI" | "StrategyLab"
    extra: Dict = field(default_factory=dict)


def append_attrition(records: List[ScanAttritionRecord]) -> None:
    """Append one or more records to today's attrition JSONL file."""
    if not records:
        return
    today = date.today().isoformat()
    ATTRITION_DIR.mkdir(parents=True, exist_ok=True)
    path = ATTRITION_DIR / f"{today}.jsonl"
    lines = [json.dumps(asdict(r), ensure_ascii=False) for r in records]
    payload = "\n".join(lines) + "\n"
    try:
        with _WRITE_LOCK:
            with open(path, "a", encoding="utf-8") as f:
                f.write(payload)
    except Exception as exc:
        log.warning("[ScanAttrition] Write failed: %s", exc)


def load_attrition(report_date: str) -> List[ScanAttritionRecord]:
    """Load all attrition records for a given date from the JSONL staging file."""
    path = ATTRITION_DIR / f"{report_date}.jsonl"
    if not path.exists():
        return []
    records: List[ScanAttritionRecord] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(ScanAttritionRecord(**{
                        k: d.get(k, v)
                        for k, v in ScanAttritionRecord.__dataclass_fields__.items()  # type: ignore[attr-defined]
                        if k != "extra"
                    }, extra=d.get("extra", {})))
                except Exception:
                    pass
    except Exception as exc:
        log.warning("[ScanAttrition] Read failed: %s", exc)
    return records


def make_scanner_no_signal(
    symbol: str,
    cycle: str,
    regime: str,
    scanner_score: float = 0.0,
    threshold_used: float = 0.0,
    rejection_reason: str = "SCANNER_BELOW_THRESHOLD",
) -> ScanAttritionRecord:
    """Convenience factory for scanner-level attrition records."""
    return ScanAttritionRecord(
        date=date.today().isoformat(),
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        scan_cycle=cycle,
        scanner_stage=STAGE_SCANNER_NO_SIGNAL,
        strategy="",
        regime=regime,
        scanner_score=round(scanner_score, 4),
        threshold_used=round(threshold_used, 4),
        rejection_reason=rejection_reason,
        is_actionable=False,
        source="EquityScannerAI",
    )


def make_strategy_lab_reject(
    symbol: str,
    cycle: str,
    regime: str,
    strategy: str,
    scanner_score: float,
    rejection_reason: str,
    backtest_score: Optional[float] = None,
) -> ScanAttritionRecord:
    """Convenience factory for StrategyLab-level attrition records."""
    return ScanAttritionRecord(
        date=date.today().isoformat(),
        timestamp=datetime.now().isoformat(),
        symbol=symbol,
        scan_cycle=cycle,
        scanner_stage=STAGE_STRATEGY_LAB_REJECT,
        strategy=strategy,
        regime=regime,
        scanner_score=round(scanner_score, 4),
        threshold_used=0.0,
        rejection_reason=rejection_reason,
        is_actionable=False,
        source="StrategyLab",
        extra={"backtest_score": round(backtest_score, 4) if backtest_score is not None else None},
    )
