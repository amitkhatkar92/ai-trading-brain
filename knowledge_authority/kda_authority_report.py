"""
knowledge_authority/kda_authority_report.py
=============================================
KDA-002 — Authority validation report generator.

Produces:
  data/klp/kda/kda_authority_validation.json   — top-level authority status
  data/klp/kda/source_performance.jsonl         — per-source learning metrics

Diagnostic only. authority_status must NOT automatically enable live execution.

Safety contract:
  broker_calls = 0, orders = 0, no_lookahead = True, PAPER_TRADING unchanged
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .kda_outcome_models import (
    AuthorityBucketResult,
    AuthorityStatus,
    AuthorityValidationReport,
    EvidenceTierResult,
    KDAOutcomeRecord,
    OutcomeStatus,
    SourcePerformanceRecord,
)


_AUTHORITY_BUCKETS = [
    (0.00, 0.20, "0.00-0.20"),
    (0.20, 0.40, "0.20-0.40"),
    (0.40, 0.60, "0.40-0.60"),
    (0.60, 0.80, "0.60-0.80"),
    (0.80, 1.00, "0.80-1.00"),
]

_EVIDENCE_TIERS = [
    "INSUFFICIENT",
    "DEVELOPING",
    "USEFUL",
    "VALIDATED",
    "DECISION_ELIGIBLE",
]

# Minimum samples before making a directional accuracy claim
_MIN_N_FOR_ACCURACY = 5

# Promotion gates
_GATE_MIN_N         = 10
_GATE_PROMISING_N   = 15
_GATE_USEFUL_N      = 30
_GATE_VALIDATED_N   = 50
_GATE_STRONG_N      = 100

_GATE_PROMISING_ACC   = 0.55
_GATE_USEFUL_ACC      = 0.57
_GATE_VALIDATED_ACC   = 0.60
_GATE_STRONG_ACC      = 0.65

_GATE_VALIDATED_TGT   = 0.40
_GATE_STRONG_TGT      = 0.50


class KDAAuthorityReporter:
    """
    Generates the KDA authority validation report from a set of outcome records.
    Reads from in-memory list; write paths are configurable for testability.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else Path("data/klp/kda")

    def generate_report(
        self,
        outcomes: List[KDAOutcomeRecord],
        source_contributions: Optional[List[Dict[str, Any]]] = None,
    ) -> AuthorityValidationReport:
        """
        Generate authority validation report from outcome records.
        No network calls, no lookahead — all computation from in-memory data.
        """
        complete   = [o for o in outcomes if o.status == OutcomeStatus.OUTCOME_COMPLETE.value]
        pending    = sum(1 for o in outcomes if o.status == OutcomeStatus.OUTCOME_PENDING.value)
        no_data    = sum(1 for o in outcomes if o.status == OutcomeStatus.OUTCOME_NO_DATA.value)
        directional = [o for o in complete
                       if o.decision in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")]

        n_complete = len(complete)

        dir_acc    = _safe_mean([o.direction_correct for o in directional])
        tgt_rate   = _safe_rate([o.target_hit        for o in directional])
        stop_rate  = _safe_rate([o.stop_hit          for o in directional])
        avg_ret    = _safe_mean_f([o.return_t5        for o in directional])
        med_ret    = _safe_median([o.return_t5        for o in directional])
        avg_mfe    = _safe_mean_f([o.mfe              for o in directional])
        avg_mae    = _safe_mean_f([o.mae              for o in directional])

        authority_buckets  = self._analyze_buckets(directional)
        evidence_tiers     = self._analyze_tiers(complete)
        calibration        = self._check_calibration(directional)
        horizon_val        = self._horizon_validation(complete)
        target_val         = self._target_validation(directional)
        source_perf        = self._source_performance(complete, source_contributions or [])

        authority_status, why_not = self._determine_status(
            n_complete, dir_acc, tgt_rate, len(directional)
        )

        return AuthorityValidationReport(
            generated_at        = datetime.now(timezone.utc).isoformat(),
            authority_status    = authority_status,
            why_not_promoted    = why_not,
            total_decisions     = len(outcomes),
            complete_outcomes   = n_complete,
            pending_outcomes    = pending,
            no_data_outcomes    = no_data,
            direction_accuracy  = dir_acc,
            target_hit_rate     = tgt_rate,
            stop_hit_rate       = stop_rate,
            avg_return_t5       = avg_ret,
            median_return_t5    = med_ret,
            avg_mfe             = avg_mfe,
            avg_mae             = avg_mae,
            authority_buckets   = authority_buckets,
            evidence_tiers      = evidence_tiers,
            calibration         = calibration,
            horizon_validation  = horizon_val,
            target_validation   = target_val,
            source_performance  = source_perf,
            no_lookahead        = True,
            broker_calls        = 0,
            orders              = 0,
            modifications       = 0,
            cancellations       = 0,
        )

    def save(self, report: AuthorityValidationReport) -> None:
        """Persist report to disk (non-blocking, best-effort)."""
        try:
            self._base_dir.mkdir(parents=True, exist_ok=True)
            path = self._base_dir / "kda_authority_validation.json"
            with path.open("w", encoding="utf-8") as fh:
                json.dump(report.as_dict(), fh, indent=2, default=str)
        except Exception:
            pass

    def save_source_performance(self, records: List[SourcePerformanceRecord]) -> None:
        """Append-write source performance records to JSONL."""
        try:
            self._base_dir.mkdir(parents=True, exist_ok=True)
            path = self._base_dir / "source_performance.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for r in records:
                    fh.write(json.dumps(r.as_dict(), default=str) + "\n")
        except Exception:
            pass

    # ── authority bucket analysis ─────────────────────────────────────────

    def _analyze_buckets(
        self, directional: List[KDAOutcomeRecord]
    ) -> List[AuthorityBucketResult]:
        results = []
        for bmin, bmax, label in _AUTHORITY_BUCKETS:
            subset = [
                o for o in directional
                if bmin <= o.knowledge_authority < bmax
                or (bmax == 1.00 and o.knowledge_authority == 1.00)
            ]
            n = len(subset)
            results.append(AuthorityBucketResult(
                bucket             = label,
                bucket_min         = bmin,
                bucket_max         = bmax,
                n                  = n,
                direction_accuracy = _safe_mean([o.direction_correct for o in subset]) if n >= _MIN_N_FOR_ACCURACY else None,
                target_hit_rate    = _safe_rate([o.target_hit for o in subset])        if n >= _MIN_N_FOR_ACCURACY else None,
                stop_hit_rate      = _safe_rate([o.stop_hit for o in subset])          if n >= _MIN_N_FOR_ACCURACY else None,
                avg_mfe            = _safe_mean_f([o.mfe for o in subset])             if n >= _MIN_N_FOR_ACCURACY else None,
                avg_mae            = _safe_mean_f([o.mae for o in subset])             if n >= _MIN_N_FOR_ACCURACY else None,
                median_return      = _safe_median([o.return_t5 for o in subset])       if n >= _MIN_N_FOR_ACCURACY else None,
            ))
        return results

    # ── evidence tier analysis ────────────────────────────────────────────

    def _analyze_tiers(
        self, complete: List[KDAOutcomeRecord]
    ) -> List[EvidenceTierResult]:
        results = []
        for tier in _EVIDENCE_TIERS:
            subset = [o for o in complete if o.evidence_state == tier]
            n = len(subset)
            dir_sub = [o for o in subset if o.decision in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")]
            results.append(EvidenceTierResult(
                tier               = tier,
                n                  = n,
                direction_accuracy = _safe_mean([o.direction_correct for o in dir_sub]) if len(dir_sub) >= _MIN_N_FOR_ACCURACY else None,
                target_hit_rate    = _safe_rate([o.target_hit for o in dir_sub])        if len(dir_sub) >= _MIN_N_FOR_ACCURACY else None,
                stop_hit_rate      = _safe_rate([o.stop_hit for o in dir_sub])          if len(dir_sub) >= _MIN_N_FOR_ACCURACY else None,
                median_return      = _safe_median([o.return_t5 for o in dir_sub])       if len(dir_sub) >= _MIN_N_FOR_ACCURACY else None,
            ))
        return results

    # ── calibration ───────────────────────────────────────────────────────

    def _check_calibration(
        self, directional: List[KDAOutcomeRecord]
    ) -> Dict[str, Any]:
        """
        Group by knowledge_authority buckets and check whether higher authority
        corresponds to higher actual direction accuracy.
        """
        calibration: Dict[str, Any] = {"buckets": []}
        for bmin, bmax, label in _AUTHORITY_BUCKETS:
            subset = [
                o for o in directional
                if bmin <= o.knowledge_authority < bmax
                or (bmax == 1.00 and o.knowledge_authority == 1.00)
            ]
            decided = [o for o in subset if o.direction_correct is not None]
            if decided:
                actual_rate = sum(1 for o in decided if o.direction_correct) / len(decided)
            else:
                actual_rate = None
            calibration["buckets"].append({
                "authority_bucket": label,
                "n":                len(decided),
                "expected_rate":    (bmin + bmax) / 2,
                "actual_rate":      actual_rate,
                "calibration_error": abs(actual_rate - (bmin + bmax) / 2) if actual_rate is not None else None,
            })
        return calibration

    # ── horizon validation ────────────────────────────────────────────────

    def _horizon_validation(self, complete: List[KDAOutcomeRecord]) -> Dict[str, Any]:
        with_horizon = [o for o in complete if o.horizon_error is not None]
        if not with_horizon:
            return {"status": "INSUFFICIENT_SAMPLE", "n": 0}

        errors = [o.horizon_error for o in with_horizon]
        mae    = statistics.median(errors) if errors else None

        p25_acc = _safe_mean([
            1.0 if o.horizon_error is not None and o.expected_days_p25 is not None
                   and o.horizon_error <= o.expected_days_p25
            else 0.0
            for o in with_horizon
        ])

        return {
            "n":                      len(with_horizon),
            "median_absolute_error":  mae,
            "p25_accuracy":           p25_acc,
            "move_speed_counts": {
                "FAST_MOVE":   sum(1 for o in with_horizon if o.move_speed == "FAST_MOVE"),
                "NORMAL_MOVE": sum(1 for o in with_horizon if o.move_speed == "NORMAL_MOVE"),
                "SLOW_MOVE":   sum(1 for o in with_horizon if o.move_speed == "SLOW_MOVE"),
                "UNRESOLVED":  sum(1 for o in with_horizon if o.move_speed == "UNRESOLVED"),
            },
        }

    # ── target validation ─────────────────────────────────────────────────

    def _target_validation(self, directional: List[KDAOutcomeRecord]) -> Dict[str, Any]:
        with_target = [o for o in directional if o.target_comparison is not None]
        if not with_target:
            return {"status": "INSUFFICIENT_SAMPLE", "n": 0}

        from collections import Counter
        counts = Counter(o.target_comparison for o in with_target)
        total  = len(with_target)

        return {
            "n":               total,
            "TOO_AGGRESSIVE":  counts.get("TOO_AGGRESSIVE",  0) / total,
            "REASONABLE":      counts.get("REASONABLE",       0) / total,
            "TOO_CONSERVATIVE":counts.get("TOO_CONSERVATIVE", 0) / total,
            "target_hit_rate": _safe_rate([o.target_hit for o in directional]),
        }

    # ── source performance ────────────────────────────────────────────────

    @staticmethod
    def _source_performance(
        complete: List[KDAOutcomeRecord],
        contributions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build per-source performance summaries from recorded contributions.
        contributions: list of InformationContribution.as_dict() items linked to outcomes.
        """
        if not contributions:
            return []

        source_map: Dict[str, Dict] = {}
        for c in contributions:
            src = c.get("source", "UNKNOWN")
            if src not in source_map:
                source_map[src] = {
                    "source": src,
                    "sample_count": 0,
                    "support_count": 0,
                    "contradiction_count": 0,
                    "decision_change_count": 0,
                    "correct_change_count": 0,
                    "incorrect_change_count": 0,
                }
            e = source_map[src]
            e["sample_count"] += 1
            direction = c.get("direction", "NEUTRAL")
            if direction == "SUPPORT":
                e["support_count"] += 1
            elif direction == "CONTRADICT":
                e["contradiction_count"] += 1

        result = []
        for src, data in source_map.items():
            dc = data["decision_change_count"]
            cc = data["correct_change_count"]
            iv = cc / dc if dc > 0 else 0.0
            result.append(SourcePerformanceRecord(
                source                  = src,
                sample_count            = data["sample_count"],
                support_count           = data["support_count"],
                contradiction_count     = data["contradiction_count"],
                decision_change_count   = dc,
                correct_change_count    = cc,
                incorrect_change_count  = data["incorrect_change_count"],
                incremental_value       = iv,
                oos_value               = 0.0,
            ).as_dict())
        return result

    # ── authority promotion logic ─────────────────────────────────────────

    @staticmethod
    def _determine_status(
        n_complete:    int,
        dir_acc:       Optional[float],
        tgt_rate:      Optional[float],
        n_directional: int,
    ) -> tuple[str, List[str]]:
        why_not: List[str] = []

        if n_complete < _GATE_MIN_N:
            why_not.append(f"Insufficient outcomes: {n_complete} < {_GATE_MIN_N}")
            return AuthorityStatus.NOT_VALIDATED.value, why_not

        if dir_acc is None:
            why_not.append("Direction accuracy not computable (no directional decisions with outcomes)")
            return AuthorityStatus.NOT_VALIDATED.value, why_not

        if n_complete >= _GATE_STRONG_N and dir_acc >= _GATE_STRONG_ACC and (tgt_rate or 0) >= _GATE_STRONG_TGT:
            return AuthorityStatus.STRONG_VALIDATED.value, []

        if n_complete >= _GATE_VALIDATED_N and dir_acc >= _GATE_VALIDATED_ACC and (tgt_rate or 0) >= _GATE_VALIDATED_TGT:
            return AuthorityStatus.VALIDATED.value, []

        if n_complete >= _GATE_USEFUL_N and dir_acc >= _GATE_USEFUL_ACC:
            if tgt_rate is not None and tgt_rate < _GATE_VALIDATED_TGT:
                why_not.append(f"Target hit rate {tgt_rate:.1%} < {_GATE_VALIDATED_TGT:.0%} threshold")
            return AuthorityStatus.USEFUL.value, why_not

        if n_complete >= _GATE_PROMISING_N and dir_acc >= _GATE_PROMISING_ACC:
            if n_complete < _GATE_USEFUL_N:
                why_not.append(f"Sample size {n_complete} < {_GATE_USEFUL_N} for USEFUL gate")
            if dir_acc < _GATE_USEFUL_ACC:
                why_not.append(f"Direction accuracy {dir_acc:.1%} < {_GATE_USEFUL_ACC:.0%} for USEFUL gate")
            return AuthorityStatus.PROMISING.value, why_not

        if dir_acc < _GATE_PROMISING_ACC:
            why_not.append(f"Direction accuracy {dir_acc:.1%} < {_GATE_PROMISING_ACC:.0%} minimum")
        if n_complete < _GATE_PROMISING_N:
            why_not.append(f"Sample size {n_complete} < {_GATE_PROMISING_N} for PROMISING gate")

        return AuthorityStatus.NOT_VALIDATED.value, why_not


# ─────────────────────────────────────────────────────────────────────────────
# Pure stat helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_mean(values: List[Optional[bool]]) -> Optional[float]:
    decided = [v for v in values if v is not None]
    if not decided:
        return None
    return sum(1 for v in decided if v) / len(decided)


def _safe_rate(values: List[Optional[bool]]) -> Optional[float]:
    decided = [v for v in values if v is not None]
    if not decided:
        return None
    return sum(1 for v in decided if v) / len(decided)


def _safe_mean_f(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return statistics.mean(vals)


def _safe_median(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return statistics.median(vals)
