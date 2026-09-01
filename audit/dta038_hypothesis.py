"""
DTA-038 HypothesisEngine — automated hypothesis lifecycle management.

A hypothesis transitions through:
  OBSERVED → INVESTIGATING → HYPOTHESIS → VALIDATION_REQUIRED
  → [VALIDATED | REJECTED_HYP] → HUMAN_APPROVAL_REQUIRED → APPROVED → DEPLOYED

SAFETY: proposed changes are NEVER applied automatically.
        Status HUMAN_APPROVAL_REQUIRED requires explicit human action.

STORAGE
-------
  data/audit/dta038/DTA038_HYPOTHESIS_YYYY-MM-DD.jsonl  — hypothesis events (append-only)
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from audit.dta038_models import AnomalyRecord, Hypothesis, HypothesisStatus
import audit.dta038_trace as _trace_mod
from audit.dta038_trace import _now_utc, _today_str, _append_line


def _make_hyp_id(seq: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"HYP:{ts}:{seq:03d}"


class HypothesisEngine:

    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._hyps:   Dict[str, Hypothesis] = {}
        self._seq:    int = 0
        self._loaded: Optional[str] = None

    # ── Init ───────────────────────────────────────────────────────────────

    def _hyp_file(self, date_str: str) -> Path:
        return _trace_mod._DATA_DIR / f"DTA038_HYPOTHESIS_{date_str}.jsonl"

    def _ensure_loaded(self, date_str: str) -> None:
        with self._lock:
            if self._loaded == date_str:
                return
            self._load(date_str)
            self._loaded = date_str

    def _load(self, date_str: str) -> None:
        path = self._hyp_file(date_str)
        if not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        evt = json.loads(raw)
                    except Exception:
                        continue
                    if evt.get("event") == "HYP_CREATE":
                        hyp = Hypothesis(
                            hyp_id=evt["hyp_id"],
                            created_ts=evt["created_ts"],
                            status=HypothesisStatus(evt["status"]),
                            title=evt["title"],
                            observation=evt["observation"],
                            proposed_change=evt["proposed_change"],
                            evidence_count=evt.get("evidence_count", 1),
                            confidence_pct=evt.get("confidence_pct", 0.0),
                            last_updated_ts=evt["created_ts"],
                            tags=evt.get("tags", []),
                        )
                        self._hyps[hyp.hyp_id] = hyp
                    elif evt.get("event") == "HYP_UPDATE":
                        hid = evt.get("hyp_id", "")
                        if hid in self._hyps:
                            h = self._hyps[hid]
                            h.status = HypothesisStatus(evt.get("status", h.status.value))
                            h.evidence_count  = evt.get("evidence_count", h.evidence_count)
                            h.confidence_pct  = evt.get("confidence_pct", h.confidence_pct)
                            h.last_updated_ts = evt.get("ts", h.last_updated_ts)
                            if evt.get("human_verdict"):
                                h.human_verdict = evt["human_verdict"]
        except Exception:
            pass

    # ── Public API ─────────────────────────────────────────────────────────

    def raise_from_anomaly(self, anomaly: AnomalyRecord) -> Optional[Hypothesis]:
        """
        Convert a detected anomaly into a research hypothesis.
        Never raises. Returns None on failure.
        """
        try:
            return self._raise_impl(anomaly)
        except Exception:
            return None

    def _raise_impl(self, anomaly: AnomalyRecord) -> Optional[Hypothesis]:
        date_str = _today_str()
        self._ensure_loaded(date_str)

        title, observation, proposed_change, tags = self._template(anomaly)

        with self._lock:
            self._seq += 1
            hid = _make_hyp_id(self._seq)
            ts  = _now_utc()
            hyp = Hypothesis(
                hyp_id=hid,
                created_ts=ts,
                status=HypothesisStatus.HYPOTHESIS,
                title=title,
                observation=observation,
                proposed_change=proposed_change,
                evidence_count=1,
                confidence_pct=0.0,
                last_updated_ts=ts,
                tags=tags,
                supporting_cycles=[anomaly.cycle_id],
            )
            self._hyps[hid] = hyp

        rec = {
            "event":           "HYP_CREATE",
            "hyp_id":          hid,
            "created_ts":      ts,
            "status":          HypothesisStatus.HYPOTHESIS.value,
            "title":           title,
            "observation":     observation,
            "proposed_change": proposed_change,
            "evidence_count":  1,
            "confidence_pct":  0.0,
            "tags":            tags,
            "source_anomaly":  anomaly.anomaly_id,
        }
        _append_line(self._hyp_file(date_str), rec)
        return hyp

    def get_today_hypotheses(self) -> List[Hypothesis]:
        try:
            date_str = _today_str()
            self._ensure_loaded(date_str)
            with self._lock:
                return list(self._hyps.values())
        except Exception:
            return []

    def mark_validation_required(self, hyp_id: str) -> None:
        """Advance a HYPOTHESIS → VALIDATION_REQUIRED. Never raises."""
        try:
            self._update_status(hyp_id, HypothesisStatus.VALIDATION_REQUIRED)
        except Exception:
            pass

    def mark_human_approval_required(self, hyp_id: str) -> None:
        """Advance a VALIDATED hypothesis → HUMAN_APPROVAL_REQUIRED. Never raises."""
        try:
            self._update_status(hyp_id, HypothesisStatus.HUMAN_APPROVAL_REQUIRED)
        except Exception:
            pass

    def _update_status(self, hyp_id: str, new_status: HypothesisStatus) -> None:
        date_str = _today_str()
        self._ensure_loaded(date_str)
        ts = _now_utc()
        with self._lock:
            if hyp_id not in self._hyps:
                return
            self._hyps[hyp_id].status = new_status
            self._hyps[hyp_id].last_updated_ts = ts
        _append_line(self._hyp_file(date_str), {
            "event":   "HYP_UPDATE",
            "hyp_id":  hyp_id,
            "status":  new_status.value,
            "ts":      ts,
        })

    # ── Hypothesis templates ───────────────────────────────────────────────

    def _template(self, anomaly: AnomalyRecord):
        from audit.dta038_models import AnomalyKind as AK
        kind = anomaly.kind

        if kind == AK.ALL_REJECTED_AT_SAME_STAGE:
            return (
                "Single-stage pipeline bottleneck detected",
                anomaly.description,
                "Investigate whether the stage threshold is over-fitted to current regime. "
                "Review threshold value, check if risk parameters need tuning. "
                "REQUIRES HUMAN APPROVAL before any parameter change.",
                ["PIPELINE_BOTTLENECK", "THRESHOLD_REVIEW"],
            )
        elif kind == AK.NEAR_MISS_THRESHOLD:
            return (
                "Near-miss threshold events: signals just below decision floor",
                anomaly.description,
                "Monitor for recurring pattern. If ≥5 near-miss events in ≥3 days, "
                "consider threshold calibration study. VALIDATION_REQUIRED first.",
                ["NEAR_MISS", "THRESHOLD_CALIBRATION"],
            )
        elif kind == AK.STRATEGY_BOTTLENECK:
            return (
                "StrategyLab blocking majority of signals",
                anomaly.description,
                "Run StrategyLab health check. Verify strategies are not disabled or "
                "in warming-up state. Check backtest gate thresholds.",
                ["STRATEGY_HEALTH", "BACKTEST_GATE"],
            )
        elif kind == AK.HIGH_REJECTION_RATE:
            return (
                "High overall rejection rate — zero executions",
                anomaly.description,
                "Cross-check regime conditions, VIX level, and portfolio heat. "
                "Verify this is not a data-quality issue with the scanner.",
                ["REJECTION_RATE", "REGIME_CHECK"],
            )
        elif kind == AK.REPEATED_SYMBOL_REJECTION:
            return (
                "Symbol repeatedly rejected across multiple cycles",
                anomaly.description,
                "Analyse the persistent rejection reason for each symbol. "
                "If regime-driven, no action needed. If technical (e.g. stale data), fix.",
                ["REPEATED_REJECTION", "SYMBOL_INVESTIGATION"],
            )
        elif kind == AK.RESTART_GAP:
            return (
                "Process restart caused trace gap — stage history incomplete",
                anomaly.description,
                "Ensure DTA-038 trace is written BEFORE each stage transition. "
                "This is expected on first restart; no code change needed if already handled.",
                ["RESTART_GAP", "TRACE_INTEGRITY"],
            )
        else:
            return (
                f"Anomaly detected: {kind.value}",
                anomaly.description,
                "Investigate manually.",
                [kind.value],
            )
