"""
Options Failure Classifier
============================
DTA-001 Phase 5: Systematic Failure Classification

Every material failure in the options knowledge system is classified
into one of the 11 failure categories defined in the specification (§27).

Classification types:
    DATA_FAILURE           — wrong, missing, or low-quality data at decision time
    DISCOVERY_FAILURE      — underlying opportunity not identified
    KNOWLEDGE_FAILURE      — knowledge system gave wrong signal
    SELECTION_FAILURE      — wrong underlying selected (equity issue)
    TIMING_FAILURE         — entry or exit timing was wrong
    STRUCTURE_FAILURE      — wrong strategy type (straddle vs spread etc.)
    OPTION_SELECTION_FAILURE — right underlying, right direction, wrong contract
    RISK_FAILURE           — risk system allowed a bad trade or blocked a good one
    EXECUTION_FAILURE      — broker/execution error
    EXIT_FAILURE           — exit too early or too late
    REGIME_FAILURE         — regime mis-classification

Failures are stored per opportunity_id and fed back to the research pipeline
to inform future pattern discovery.

Persistence: data/options_failures.json (atomic write)
Singleton: get_options_failure_classifier()
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

from utils import get_logger

log = get_logger(__name__)

_PERSIST_PATH = "data/options_failures.json"
_INSTANCE: Optional["OptionsFailureClassifier"] = None
_INSTANCE_LOCK = threading.Lock()

# ── Failure type constants ─────────────────────────────────────────────────
FAIL_DATA           = "DATA_FAILURE"
FAIL_DISCOVERY      = "DISCOVERY_FAILURE"
FAIL_KNOWLEDGE      = "KNOWLEDGE_FAILURE"
FAIL_SELECTION      = "SELECTION_FAILURE"
FAIL_TIMING         = "TIMING_FAILURE"
FAIL_STRUCTURE      = "STRUCTURE_FAILURE"
FAIL_OPTION_SELECT  = "OPTION_SELECTION_FAILURE"
FAIL_RISK           = "RISK_FAILURE"
FAIL_EXECUTION      = "EXECUTION_FAILURE"
FAIL_EXIT           = "EXIT_FAILURE"
FAIL_REGIME         = "REGIME_FAILURE"

_ALL_TYPES: Set[str] = {
    FAIL_DATA, FAIL_DISCOVERY, FAIL_KNOWLEDGE, FAIL_SELECTION,
    FAIL_TIMING, FAIL_STRUCTURE, FAIL_OPTION_SELECT, FAIL_RISK,
    FAIL_EXECUTION, FAIL_EXIT, FAIL_REGIME,
}

# ── Auto-classification rules ──────────────────────────────────────────────
# These are heuristics; operators may manually override.
_AUTO_RULES = [
    # (condition_key_substring, failure_type)
    ("iv_source=MODEL_ESTIMATE",   FAIL_DATA),
    ("chain_quality_below",        FAIL_DATA),
    ("data_source=SYNTHETIC",      FAIL_DATA),
    ("missed_underlying",          FAIL_DISCOVERY),
    ("knowledge_state=INVALIDATED", FAIL_KNOWLEDGE),
    ("false_rejection",            FAIL_KNOWLEDGE),
    ("wrong_contract",             FAIL_OPTION_SELECT),
    ("option_selection_failure",   FAIL_OPTION_SELECT),
    ("regime_mismatch",            FAIL_REGIME),
    ("portfolio_heat",             FAIL_RISK),
    ("position_limit",             FAIL_RISK),
    ("gamma_risk",                 FAIL_EXIT),
    ("exit_too_early",             FAIL_EXIT),
    ("exit_too_late",              FAIL_EXIT),
    ("partial_fill",               FAIL_EXECUTION),
    ("order_rejected_broker",      FAIL_EXECUTION),
]


@dataclass
class FailureRecord:
    """One classified failure event."""
    failure_id:       str
    opportunity_id:   str
    symbol:           str
    strategy_name:    str
    failure_type:     str
    sub_type:         str         # more specific description
    description:      str
    evidence:         str         # raw note from the system
    pnl_rs:           float       # realized P&L at time of classification
    expected_pnl:     float
    improvement_hint: str         # what would have prevented this failure
    regime:           str
    classified_at:    str
    auto_classified:  bool        # True = rule-based, False = manual / hybrid
    severity:         str         # LOW / MEDIUM / HIGH / CRITICAL


def get_options_failure_classifier() -> "OptionsFailureClassifier":
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = OptionsFailureClassifier()
    return _INSTANCE


class OptionsFailureClassifier:
    """
    Classifies options trading failures by root cause.

    Failures are auto-classified from evidence strings and confirmed
    against known patterns.  Manual overrides are supported.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: List[FailureRecord] = []
        self._fail_counter = 0
        os.makedirs("data", exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def classify(
        self,
        opportunity_id:   str,
        symbol:           str,
        strategy_name:    str,
        evidence:         str,
        pnl_rs:           float,
        expected_pnl:     float,
        regime:           str = "",
        failure_type:     Optional[str] = None,
        sub_type:         str = "",
        description:      str = "",
        improvement_hint: str = "",
    ) -> Optional[FailureRecord]:
        """
        Classify a failure event.

        If failure_type is None, auto-classification is attempted.
        Returns None if no failure classification applies (not a failure).
        """
        # Only classify when there's a material loss
        if pnl_rs >= 0 and failure_type is None:
            return None

        # Auto-classify from evidence string
        auto = False
        if failure_type is None:
            failure_type, sub_type = self._auto_classify(evidence, pnl_rs, expected_pnl)
            auto = True

        if failure_type not in _ALL_TYPES:
            failure_type = FAIL_KNOWLEDGE  # fallback

        severity = self._compute_severity(pnl_rs, expected_pnl)

        with self._lock:
            self._fail_counter += 1
            fid = f"FAIL-{datetime.now().strftime('%Y%m%d')}-{self._fail_counter:06d}"
            rec = FailureRecord(
                failure_id=fid,
                opportunity_id=opportunity_id,
                symbol=symbol,
                strategy_name=strategy_name,
                failure_type=failure_type,
                sub_type=sub_type or failure_type,
                description=description or f"Automated classification: {failure_type}",
                evidence=evidence[:500],  # cap to 500 chars
                pnl_rs=pnl_rs,
                expected_pnl=expected_pnl,
                improvement_hint=improvement_hint or self._suggest_improvement(failure_type),
                regime=regime,
                classified_at=datetime.now().isoformat(),
                auto_classified=auto,
                severity=severity,
            )
            self._failures.append(rec)
            self._save_locked()

        log.info(
            "[FailureClassifier] %s: %s/%s sev=%s pnl=%.0f",
            opportunity_id, failure_type, sub_type or "-", severity, pnl_rs,
        )
        return rec

    def get_failure_distribution(self) -> Dict[str, int]:
        """Count of failures by type."""
        with self._lock:
            dist: Dict[str, int] = {t: 0 for t in _ALL_TYPES}
            for f in self._failures:
                dist[f.failure_type] = dist.get(f.failure_type, 0) + 1
            return dist

    def get_failures_by_type(self, failure_type: str) -> List[FailureRecord]:
        with self._lock:
            return [f for f in self._failures if f.failure_type == failure_type]

    def get_recent_failures(self, n: int = 20) -> List[FailureRecord]:
        with self._lock:
            return list(self._failures[-n:])

    def get_summary(self) -> Dict:
        with self._lock:
            total = len(self._failures)
            if not total:
                return {"total": 0, "distribution": {}}
            by_type = self.get_failure_distribution()
            high_sev = [f for f in self._failures if f.severity in ("HIGH", "CRITICAL")]
            return {
                "total": total,
                "distribution": by_type,
                "high_severity_count": len(high_sev),
                "top_failure_type": max(by_type, key=by_type.get) if by_type else None,
                "total_pnl_lost": sum(f.pnl_rs for f in self._failures),
            }

    # ── Internal ───────────────────────────────────────────────────────────

    def _auto_classify(self, evidence: str, pnl_rs: float, expected_pnl: float) -> Tuple[str, str]:
        evidence_lower = evidence.lower()
        for keyword, ftype in _AUTO_RULES:
            if keyword.lower() in evidence_lower:
                return ftype, keyword
        # Fallback: classify by magnitude
        if abs(pnl_rs) > abs(expected_pnl) * 2:
            return FAIL_RISK, "excessive_loss"
        return FAIL_KNOWLEDGE, "unclassified"

    def _compute_severity(self, pnl_rs: float, expected_pnl: float) -> str:
        if pnl_rs >= 0:
            return "LOW"
        loss = abs(pnl_rs)
        if expected_pnl > 0:
            ratio = loss / expected_pnl
            if ratio < 0.5:
                return "LOW"
            if ratio < 1.0:
                return "MEDIUM"
            if ratio < 2.0:
                return "HIGH"
        return "CRITICAL"

    def _suggest_improvement(self, failure_type: str) -> str:
        hints = {
            FAIL_DATA: "Use live market data; verify IV source before trading",
            FAIL_DISCOVERY: "Review scanning parameters and screener thresholds",
            FAIL_KNOWLEDGE: "Add more observations; verify OOS validation passed",
            FAIL_SELECTION: "Review equity selection criteria and regime filters",
            FAIL_TIMING: "Study optimal entry timing per regime/IVR combination",
            FAIL_STRUCTURE: "Review strategy type selection logic for context",
            FAIL_OPTION_SELECT: "Analyze multi-contract shadow data for better contract",
            FAIL_RISK: "Review risk gate thresholds using authenticated knowledge",
            FAIL_EXECUTION: "Check broker connectivity and security ID mapping",
            FAIL_EXIT: "Optimize exit timing with DTE/theta decay analysis",
            FAIL_REGIME: "Improve regime detection with multi-indicator consensus",
        }
        return hints.get(failure_type, "Review system logs for root cause")

    def _save_locked(self) -> None:
        try:
            data = {
                "failures": [vars(f) for f in self._failures],
                "fail_counter": self._fail_counter,
                "saved_at": datetime.now().isoformat(),
            }
            tmp = _PERSIST_PATH + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, default=str, indent=2)
            os.replace(tmp, _PERSIST_PATH)
        except Exception as exc:
            log.debug("[FailureClassifier] Save error: %s", exc)

    def _load(self) -> None:
        try:
            if not os.path.exists(_PERSIST_PATH):
                return
            with open(_PERSIST_PATH) as f:
                data = json.load(f)
            self._failures = [FailureRecord(**r) for r in data.get("failures", [])]
            self._fail_counter = data.get("fail_counter", 0)
            log.info("[FailureClassifier] Loaded %d failures.", len(self._failures))
        except Exception as exc:
            log.debug("[FailureClassifier] Load error: %s", exc)
            self._failures = []
