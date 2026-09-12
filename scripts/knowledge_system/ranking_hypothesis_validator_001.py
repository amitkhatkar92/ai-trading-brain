"""
scripts/knowledge_system/ranking_hypothesis_validator_001.py
==============================================================
Ranking Self-Learning Loop (RSL-001) — Stage A: Automated Hypothesis Validator.

Completes the pending Phase B step: KSL-001 already accumulates shadow
evidence and auto-registers PROPOSED hypotheses in the ARS Hypothesis
Registry, but nothing ever tested them. This module runs a rigorous,
fully-automated statistical validation of each pending KSL_AUTO hypothesis
against the shadow evidence ledger and records a verdict — no human
review step, matching the pattern already proven in this codebase by
h001.py (H-CRITICAL-001: PROPOSED -> ... -> CONFIRMED, actor is a script).

Procedure per hypothesis (time-ordered, leakage-safe):
  1. Parse (problem_area, direction) from the hypothesis title.
  2. Load the matching evidence subset from shadow_evidence_ledger.jsonl.
  3. Time-split 70/30 by trade_date (train / OOS) — never shuffled.
  4. Bootstrap-resample the OOS subset (1000 iters) for a 90% CI on the
     effect size (miss_rate - baseline).
  5. Scorecard (4 checks, majority-vote — mirrors the proven 4/6 pattern
     from strategy_lab/backtesting_ai.py's quality_score()):
       C1 sample size, C2 CI excludes baseline, C3 train/OOS consistency,
       C4 minimum effect magnitude.
  6. Verdict: >=3/4 -> VALIDATED, <=1/4 -> NO_INCREMENTAL_VALUE,
     else -> INSUFFICIENT_SAMPLE (retried next run, more data accrues).
  7. Automated hypothesis lifecycle transition (PROPOSED -> ... -> RUNNING
     -> VALIDATED/REJECTED), actor="RHV-001". No human step at any point.
  8. On VALIDATED, hands off to ranking_adjustment_engine_001 to register
     a shadow-eligible candidate (Phase E).

Safety: read-only against shadow_evidence_ledger.jsonl; the only writes
are to the ARS hypothesis registry (status/lifecycle) and this module's
own append-only findings ledger. Zero broker/order/execution imports.
"""
from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.knowledge_system.knowledge_pattern_miner_001 import load_evidence
from scripts.knowledge_system.ksl_models import Classification, FindingVerdict, KnowledgeFinding

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

LEDGER_PATH        = ROOT / "data" / "shadow_evidence_ledger.jsonl"
FINDINGS_LEDGER     = ROOT / "data" / "ksl" / "ranking_findings_ledger.jsonl"

VALIDATOR_ACTOR    = "RHV-001"          # automated actor identity (no human name)
TRAIN_FRACTION     = 0.70               # time-ordered split, never shuffled
MIN_OOS_N          = 20                 # C1: minimum OOS sample size
BASELINE_MISS_RATE = 0.55               # same reference used by knowledge_pattern_miner_001
MIN_EFFECT         = 0.05               # C4: minimum meaningful effect (matches miner's threshold)
BOOTSTRAP_ITERS    = 1000
CI_LOW_PCT         = 5                  # 90% CI: [5th, 95th] percentile
CI_HIGH_PCT        = 95
_RNG_SEED          = 20260912           # deterministic for test reproducibility


# ─────────────────────────────────────────────────────────────────────────────
# Statistics (pure functions — no I/O, unit-testable in isolation)
# ─────────────────────────────────────────────────────────────────────────────

def _time_split(records: List[Dict], train_fraction: float = TRAIN_FRACTION) -> Tuple[List[Dict], List[Dict]]:
    """Time-ordered train/OOS split by trade_date. Never shuffles — no leakage."""
    dates = sorted({r.get("trade_date", "") for r in records if r.get("trade_date")})
    if not dates:
        return [], []
    split_idx = max(1, int(len(dates) * train_fraction))
    split_idx = min(split_idx, len(dates) - 1) if len(dates) > 1 else split_idx
    split_date = dates[split_idx] if split_idx < len(dates) else dates[-1]
    train = [r for r in records if r.get("trade_date", "") < split_date]
    oos   = [r for r in records if r.get("trade_date", "") >= split_date]
    return train, oos


def _miss_rate(records: List[Dict]) -> Tuple[float, int]:
    """Fraction classified RANKING_MISS among the ge2-mover population. Returns (rate, n)."""
    if not records:
        return 0.0, 0
    n = len(records)
    misses = sum(1 for r in records if r.get("classification") == Classification.RANKING_MISS.value)
    return misses / n, n


def _bootstrap_ci(records: List[Dict], iters: int = BOOTSTRAP_ITERS,
                   seed: int = _RNG_SEED) -> Tuple[float, float]:
    """Bootstrap-resample miss_rate over `records`; return (ci_low, ci_high)."""
    if not records:
        return 0.0, 0.0
    is_miss = [1 if r.get("classification") == Classification.RANKING_MISS.value else 0 for r in records]
    n = len(is_miss)
    rng = random.Random(seed)
    rates = []
    for _ in range(iters):
        sample = rng.choices(is_miss, k=n)
        rates.append(sum(sample) / n)
    rates.sort()
    lo_idx = max(0, int(len(rates) * CI_LOW_PCT / 100.0))
    hi_idx = min(len(rates) - 1, int(len(rates) * CI_HIGH_PCT / 100.0))
    return rates[lo_idx], rates[hi_idx]


def run_scorecard(records: List[Dict], miss_reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the 4-check scorecard for a (direction, miss_reason) evidence subset.

    `records` must already be filtered to the relevant ge2-mover population
    (classification in RANKING_MISS/CORRECT_SELECT, ge2 is True).

    Returns a fully-populated result dict — never raises.
    """
    train, oos = _time_split(records)
    train_rate, train_n = _miss_rate(train)
    oos_rate, oos_n     = _miss_rate(oos)
    ci_low, ci_high      = _bootstrap_ci(oos)

    c1_sample       = oos_n >= MIN_OOS_N
    c2_ci_excludes  = (ci_low - BASELINE_MISS_RATE) > 0
    train_effect    = train_rate - BASELINE_MISS_RATE
    oos_effect      = oos_rate - BASELINE_MISS_RATE
    c3_consistent   = (train_effect > 0) == (oos_effect > 0) and train_n > 0 and oos_n > 0
    c4_magnitude    = oos_effect >= MIN_EFFECT

    checks = {"C1_sample_size": c1_sample, "C2_ci_excludes_baseline": c2_ci_excludes,
              "C3_train_oos_consistent": c3_consistent, "C4_effect_magnitude": c4_magnitude}
    passed = sum(1 for v in checks.values() if v)

    if passed >= 3:
        verdict = FindingVerdict.VALIDATED
    elif passed <= 1:
        verdict = FindingVerdict.NO_INCREMENTAL_VALUE
    else:
        verdict = FindingVerdict.INSUFFICIENT_SAMPLE

    return {
        "verdict":        verdict,
        "checks":         checks,
        "checks_passed":  passed,
        "checks_total":   len(checks),
        "train_n":        train_n,
        "oos_n":          oos_n,
        "train_miss_rate": round(train_rate, 4),
        "oos_miss_rate":   round(oos_rate, 4),
        "ci_low":          round(ci_low, 4),
        "ci_high":         round(ci_high, 4),
        "baseline":        BASELINE_MISS_RATE,
        "oos_effect":      round(oos_effect, 4),
        "miss_reason":     miss_reason,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Hypothesis title parsing (mirrors _try_register_hypothesis's title format)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_title(title: str) -> Optional[Tuple[str, str]]:
    """'KSL-001 Auto: {problem_area} — {direction}' -> (problem_area, direction)."""
    if not title.startswith("KSL-001 Auto:"):
        return None
    body = title[len("KSL-001 Auto:"):].strip()
    if "—" not in body:
        return None
    area, direction = body.split("—", 1)
    return area.strip(), direction.strip()


def _dominant_miss_reason(records: List[Dict]) -> Optional[str]:
    """Most common miss_reason among RANKING_MISS records — for feature_id labelling."""
    reasons: Dict[str, int] = {}
    for r in records:
        if r.get("classification") == Classification.RANKING_MISS.value:
            mr = r.get("miss_reason", "UNKNOWN")
            reasons[mr] = reasons.get(mr, 0) + 1
    if not reasons:
        return None
    return max(reasons, key=reasons.get)


# ─────────────────────────────────────────────────────────────────────────────
# Ledger writer
# ─────────────────────────────────────────────────────────────────────────────

def _log_finding(finding: KnowledgeFinding, extra: Optional[Dict] = None) -> None:
    FINDINGS_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    rec = finding.to_dict()
    if extra:
        rec.update(extra)
    with open(FINDINGS_LEDGER, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Automated hypothesis lifecycle (mirrors h001.py's H-CRITICAL-001 pattern)
# ─────────────────────────────────────────────────────────────────────────────

def _advance_to_running(hr, hyp) -> bool:
    """PROPOSED -> UNDER_REVIEW -> APPROVED -> PLANNED -> RUNNING, all automated."""
    from autonomous_research.hypothesis_models import HypothesisStatus
    try:
        status = hyp.status
        chain = [HypothesisStatus.UNDER_REVIEW, HypothesisStatus.APPROVED,
                 HypothesisStatus.PLANNED, HypothesisStatus.RUNNING]
        start_idx = 0
        if status == HypothesisStatus.UNDER_REVIEW:
            start_idx = 0
        elif status == HypothesisStatus.APPROVED:
            start_idx = 1
        elif status == HypothesisStatus.PLANNED:
            start_idx = 2
        elif status == HypothesisStatus.RUNNING:
            return True  # already there
        elif status != HypothesisStatus.PROPOSED:
            return False  # not eligible (already VALIDATED/CONFIRMED/REJECTED/ARCHIVED)

        for next_status in chain[start_idx:]:
            hr.update_status(
                hyp.hypothesis_id, next_status, actor=VALIDATOR_ACTOR,
                reason=f"RHV-001 automated pipeline step -> {next_status.value}",
            )
        return True
    except Exception as exc:
        print(f"[RHV-001] Lifecycle advance failed for {hyp.hypothesis_id}: {exc}")
        return False


def _apply_verdict(hr, hyp, scorecard: Dict[str, Any]) -> str:
    """RUNNING -> VALIDATED/REJECTED, automated actor. Returns final status value."""
    from autonomous_research.hypothesis_models import HypothesisStatus
    verdict = scorecard["verdict"]
    reason = (
        f"RHV-001 verdict={verdict.value} scorecard={scorecard['checks_passed']}/"
        f"{scorecard['checks_total']} oos_n={scorecard['oos_n']} "
        f"oos_effect={scorecard['oos_effect']}"
    )
    if verdict == FindingVerdict.VALIDATED:
        hr.update_status(hyp.hypothesis_id, HypothesisStatus.VALIDATED,
                          actor=VALIDATOR_ACTOR, reason=reason, metadata=scorecard)
        return HypothesisStatus.VALIDATED.value
    elif verdict == FindingVerdict.NO_INCREMENTAL_VALUE:
        hr.update_status(hyp.hypothesis_id, HypothesisStatus.REJECTED,
                          actor=VALIDATOR_ACTOR, reason=reason, metadata=scorecard)
        return HypothesisStatus.REJECTED.value
    else:
        # INSUFFICIENT_SAMPLE: stay RUNNING, retried next cycle as more data accrues
        return HypothesisStatus.RUNNING.value


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def validate_pending_hypotheses(ledger_path: Path = LEDGER_PATH) -> Dict[str, Any]:
    """
    Validate all pending KSL_AUTO hypotheses. Fully automated, no human step.
    Returns a summary dict. Never raises — all failures are caught and logged.
    """
    summary: Dict[str, Any] = {"evaluated": 0, "validated": 0, "rejected": 0,
                                "insufficient": 0, "shadow_candidates_created": 0,
                                "errors": 0}
    try:
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry
        from autonomous_research.hypothesis_models import HypothesisStatus
    except Exception as exc:
        print(f"[RHV-001] ARS registry unavailable — skipping validation: {exc}")
        return summary

    try:
        kp = KnowledgeProvider()
        hr = HypothesisRegistry(knowledge_provider=kp)
        candidates = [
            h for h in hr.list_by_origin("KSL_AUTO")
            if h.status in (HypothesisStatus.PROPOSED, HypothesisStatus.RUNNING)
        ]
    except Exception as exc:
        print(f"[RHV-001] Failed to load hypothesis registry: {exc}")
        return summary

    if not candidates:
        return summary

    all_evidence = load_evidence(ledger_path)

    for hyp in candidates:
        try:
            parsed = _parse_title(hyp.title)
            if not parsed:
                continue
            area, direction = parsed
            summary["evaluated"] += 1

            subset = [
                r for r in all_evidence
                if r.get("direction") == direction
                and r.get("classification") in (Classification.RANKING_MISS.value,
                                                 Classification.CORRECT_SELECT.value)
                and r.get("ge2") is True
            ]
            miss_reason = _dominant_miss_reason(subset)
            scorecard = run_scorecard(subset, miss_reason=miss_reason)

            if not _advance_to_running(hr, hyp):
                continue

            final_status = _apply_verdict(hr, hyp, scorecard)

            finding = KnowledgeFinding(
                finding_id=f"RHV-{uuid.uuid4().hex[:12]}",
                research_question_id=hyp.knowledge_gap.replace("RQ: ", "") if hyp.knowledge_gap else "",
                experiment_id=hyp.hypothesis_id,
                verdict=scorecard["verdict"],
                baseline_metrics={"miss_rate": scorecard["train_miss_rate"], "n": scorecard["train_n"]},
                candidate_metrics={"miss_rate": scorecard["oos_miss_rate"], "n": scorecard["oos_n"]},
                delta={"oos_effect": scorecard["oos_effect"]},
                oos_result=f"ci=[{scorecard['ci_low']},{scorecard['ci_high']}]",
                leakage_result="TIME_ORDERED_SPLIT_NO_SHUFFLE",
                sample_size=scorecard["oos_n"],
                confidence=scorecard["checks_passed"] / scorecard["checks_total"],
                limitations="Shadow-ledger evidence only; single-market, single-session horizon.",
                recommendation=(
                    "Promote to shadow-testing." if scorecard["verdict"] == FindingVerdict.VALIDATED
                    else "No action." if scorecard["verdict"] == FindingVerdict.NO_INCREMENTAL_VALUE
                    else "Retry once more evidence accrues."
                ),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            _log_finding(finding, extra={
                "hypothesis_id": hyp.hypothesis_id, "area": area, "direction": direction,
                "miss_reason": miss_reason, "final_hypothesis_status": final_status,
                "scorecard": scorecard["checks"],
            })

            if scorecard["verdict"] == FindingVerdict.VALIDATED:
                summary["validated"] += 1
                try:
                    from scripts.knowledge_system.ranking_adjustment_engine_001 import (
                        register_shadow_candidate,
                    )
                    created = register_shadow_candidate(
                        finding=finding, area=area, direction=direction,
                        miss_reason=miss_reason, scorecard=scorecard,
                    )
                    if created:
                        summary["shadow_candidates_created"] += 1
                except Exception as adj_exc:
                    print(f"[RHV-001] Shadow-candidate registration failed (non-fatal): {adj_exc}")
            elif scorecard["verdict"] == FindingVerdict.NO_INCREMENTAL_VALUE:
                summary["rejected"] += 1
            else:
                summary["insufficient"] += 1

        except Exception as exc:
            summary["errors"] += 1
            print(f"[RHV-001] Validation failed for hypothesis (non-fatal): {exc}")

    return summary


if __name__ == "__main__":
    result = validate_pending_hypotheses()
    print(json.dumps(result, indent=2, default=str))
