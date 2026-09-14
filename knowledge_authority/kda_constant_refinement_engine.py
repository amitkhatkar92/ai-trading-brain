"""
knowledge_authority/kda_constant_refinement_engine.py
========================================================
KDA-CRE-001 — Knowledge Decision Authority Constant Refinement Engine.

Fully automated, no-human-step self-refinement of KDA's fixed evidence-gate
constants (knowledge_decision_authority.py). Same proven shape as RSL-001's
ranking_adjustment_engine_001.py (shadow-then-live, bounded, auto-rollback),
reused as a TEMPLATE only — zero imports from scripts/knowledge_system/,
zero shared storage. Owns its own store: data/kda_cre/.

WHY ONLY 3 CONSTANTS (not 5)
-----------------------------
knowledge_decision_authority.py declares 5 threshold constants, but
_AUTHORITY_KNOWLEDGE_MIN and _AUTHORITY_STRATEGY_MIN are dead code since
ARCH-005 (_classify_authority no longer reads them — authority role is now
architecture-fixed to KNOWLEDGE for all non-INSUFFICIENT states). Only the
3 constants actually read by _classify_evidence_state / _compute_authority
are managed here: _ESS_DECISION_ELIGIBLE, _STABILITY_DECISION_MIN,
_CONTRADICTION_DECISION_MIN.

LIFECYCLE (fully automated, no human step at any transition)
--------------------------------------------------------------
  WAITING_FOR_EVIDENCE -- not enough new resolved KDA outcomes yet, and/or
                          the dynamic cooldown floor has not elapsed.
  SHADOW_ACTIVE         -- a statistically-validated candidate value is
                          being confirmed against NEW, held-out outcome
                          data (never the same data used to propose it).
  ACTIVE                -- shadow-confirmed; candidate value is now live
                          (read by knowledge_decision_authority.py).
  ROLLED_BACK           -- live performance degraded past the guardrail;
                          automatically reverted to the previous value.
  REJECTED              -- shadow period failed to reconfirm the effect.

SELF-SCHEDULING ("the system decides the period", not a human calendar)
--------------------------------------------------------------------------
Two independent gates must BOTH pass before any candidate is even
evaluated for a given constant:

  1. Evidence-driven trigger: >= MIN_NEW_EVIDENCE_PER_CHECK new COMPLETE
     outcomes must have accumulated since this constant was last checked.
     This is why the interval is not a fixed calendar number — a busy
     month clears this in days, a quiet month takes longer.

  2. Dynamic cooldown floor: a MINIMUM number of days must have elapsed
     since the last LIVE value change to this constant, and that minimum
     is itself calculated (not guessed) from the system's own recently
     observed outcome-arrival rate -- see _calculate_dynamic_cooldown_days().
     This is a safety rail, not a schedule: it exists so a short burst of
     correlated evidence (e.g. one trending week) cannot cause rapid,
     unstable back-to-back changes to a live-money decision gate.

STATISTICAL VALIDATION (mirrors RHV-001's proven scorecard shape)
---------------------------------------------------------------------
Time-ordered 70/30 train/OOS split (never shuffled) on resolved outcomes,
bootstrap CI (1000 iters, seeded) on the accuracy delta between the
current threshold's accepted population and a candidate's, 4-check
scorecard (sample size, CI excludes zero, train/OOS sign consistency,
effect magnitude). Because this gates live-money trades (not a research
ranking), the minimum sample size required here is materially higher
than RHV-001's generic bar.

SAFETY CONTRACT (never violated)
-----------------------------------
  broker_calls = 0, orders = 0, no_lookahead = True
  No imports from OrderManager, execution_engine, broker APIs, dhan_feed
  Every accepted/rejected/rolled-back change is appended, never overwritten,
  to constant_change_ledger.jsonl with full reasoning, for research reuse.
  knowledge_decision_authority.py's public interface (evaluate(), inputs,
  outputs) is completely unchanged — only the internal constant VALUES can
  move, and only within pre-declared bounds, and only after validation.
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

ACTOR = "KDA-CRE-001"   # automated actor identity (no human name), mirrors RHV-001 convention

# ─────────────────────────────────────────────────────────────────────────────
# Storage — isolated (data/kda_cre/ only, never data/klp/kda/ files are modified)
# ─────────────────────────────────────────────────────────────────────────────

_ROOT       = Path(__file__).parent.parent
_STORE_DIR  = _ROOT / "data" / "kda_cre"
_DATASET_PATH   = _STORE_DIR / "kda_outcome_dataset.jsonl"      # cached decision+outcome join
_OVERRIDES_PATH = _STORE_DIR / "active_constant_overrides.json"  # live values, read by KDA
_STATE_PATH     = _STORE_DIR / "refinement_state.json"           # per-constant scheduling state
_LEDGER_PATH    = _STORE_DIR / "constant_change_ledger.jsonl"     # append-only audit trail

_KDA_LEDGER_DIR = _ROOT / "data" / "klp" / "kda"   # read-only source (KDALedger's own directory)

# ─────────────────────────────────────────────────────────────────────────────
# Tunable constant registry — the ONLY 3 constants actually live post-ARCH-005
# ─────────────────────────────────────────────────────────────────────────────

TUNABLE_CONSTANTS: Dict[str, Dict[str, Any]] = {
    "_ESS_DECISION_ELIGIBLE": {
        "default": 100.0, "min": 20.0, "max": 300.0, "step": 10.0,
        "feature": "effective_sample_size",
    },
    "_STABILITY_DECISION_MIN": {
        "default": 0.6, "min": 0.3, "max": 0.9, "step": 0.05,
        "feature": "stability",
    },
    "_CONTRADICTION_DECISION_MIN": {
        "default": 0.4, "min": 0.1, "max": 0.8, "step": 0.05,
        "feature": "contradiction_factor",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Guardrails
# ─────────────────────────────────────────────────────────────────────────────

MIN_NEW_EVIDENCE_PER_CHECK = 30      # new resolved outcomes needed before re-checking a constant
ABSOLUTE_MIN_COOLDOWN_DAYS = 30      # hard safety floor -- never bypassed regardless of data volume
EVIDENCE_VELOCITY_WINDOW_DAYS = 30   # window used to measure the system's own outcome-arrival rate

MIN_SAMPLE_FOR_VALIDATION = 50       # higher than RHV-001's generic 10 -- this gates live-money trades
TRAIN_FRACTION      = 0.70           # time-ordered split, never shuffled
BOOTSTRAP_ITERS     = 1000
CI_LOW_PCT, CI_HIGH_PCT = 5, 95      # 90% CI
MIN_EFFECT          = 0.03           # minimum meaningful accuracy delta (3 percentage points)
_RNG_SEED           = 20260912

SHADOW_MIN_DAYS         = 15    # minimum elapsed days before a shadow candidate can be judged
SHADOW_MIN_NEW_OUTCOMES = 30    # minimum NEW (post-shadow-start) outcomes required to judge it

ROLLBACK_DEGRADATION_PP    = 0.05   # 5pp degradation vs the pre-promotion baseline triggers auto-revert
MIN_POST_PROMOTION_SAMPLE  = 30     # minimum post-promotion outcomes before judging rollback

STATUS_WAITING  = "WAITING_FOR_EVIDENCE"
STATUS_SHADOW   = "SHADOW_ACTIVE"
STATUS_ACTIVE   = "ACTIVE"
STATUS_ROLLED_BACK = "ROLLED_BACK"
STATUS_REJECTED = "REJECTED"

_MAX_EVAL_BARS_BUFFER = 25   # calendar days to wait before attempting outcome evaluation (>= 20 trading bars)


# ─────────────────────────────────────────────────────────────────────────────
# Atomic JSON / JSONL I/O helpers (mirror ranking_adjustment_engine_001.py)
# ─────────────────────────────────────────────────────────────────────────────

def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    os.replace(tmp, path)


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _log_ledger(event_type: str, constant_name: str, reason: str, **extra: Any) -> None:
    """Append one immutable, research-reusable audit entry. Never raises."""
    try:
        record = {
            "event_id":  str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor":     ACTOR,
            "event_type": event_type,        # SHADOW_STARTED | PROMOTED | REJECTED | ROLLED_BACK
            "constant_name": constant_name,
            "reason":    reason,
            **extra,
        }
        _append_jsonl(_LEDGER_PATH, record)
    except Exception as exc:
        log.debug("[KDA-CRE] ledger write failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API — consumed by knowledge_decision_authority.py
# ─────────────────────────────────────────────────────────────────────────────

_cache_mtime: Optional[float] = None
_cache_values: Optional[Dict[str, float]] = None


def get_effective_constants(overrides_path: Optional[Path] = None) -> Dict[str, float]:
    """
    Return the 3 live tunable constants. Sources validated overrides when
    present; otherwise (missing file, corrupt file, any error, or a
    constant simply not yet overridden) falls back to the original
    hardcoded default for that constant. Never raises.

    mtime-gated cache: only re-parses the override file when it changes,
    so this is safe to call on every KDA evaluate() (hot intraday path).
    """
    global _cache_mtime, _cache_values
    path = overrides_path or _OVERRIDES_PATH
    defaults = {name: cfg["default"] for name, cfg in TUNABLE_CONSTANTS.items()}

    try:
        if not path.exists():
            return defaults
        mtime = path.stat().st_mtime
        if overrides_path is None and _cache_values is not None and _cache_mtime == mtime:
            return _cache_values

        raw = json.loads(path.read_text())
        result = dict(defaults)
        for name, cfg in TUNABLE_CONSTANTS.items():
            entry = raw.get(name)
            if not isinstance(entry, dict):
                continue
            value = entry.get("value")
            if not isinstance(value, (int, float)):
                continue
            value = float(value)
            if cfg["min"] <= value <= cfg["max"]:
                result[name] = value

        if overrides_path is None:
            _cache_mtime, _cache_values = mtime, result
        return result
    except Exception as exc:
        log.debug("[KDA-CRE] get_effective_constants fallback to defaults: %s", exc)
        return defaults


# ─────────────────────────────────────────────────────────────────────────────
# Outcome dataset — incremental join of KDA decisions + computed outcomes
# ─────────────────────────────────────────────────────────────────────────────

def _load_all_kda_decisions() -> List[Dict[str, Any]]:
    from .kda_ledger import KDALedger
    return KDALedger(base_dir=_KDA_LEDGER_DIR).load_all_decisions()


def refresh_outcome_dataset() -> Dict[str, Any]:
    """
    Incrementally evaluate any KDA decisions old enough to have resolved
    outcomes but not yet in the cached dataset. Reuses the existing,
    already-tested KDAOutcomeEngine and bar-fetch helper -- no new
    lookahead-risk logic is introduced. Never raises.
    """
    summary = {"new_records": 0, "skipped_too_recent": 0, "no_data": 0}
    try:
        from .kda_models import KDADecisionRecord
        from .kda_outcome_engine import KDAOutcomeEngine
        from .knowledge_decision_pipeline import _fetch_post_decision_bars

        existing = _read_jsonl(_DATASET_PATH)
        seen_ids = {r.get("decision_id") for r in existing}

        decisions = _load_all_kda_decisions()
        engine = KDAOutcomeEngine()
        cutoff = (date.today() - timedelta(days=_MAX_EVAL_BARS_BUFFER)).isoformat()

        for d in decisions:
            decision_id = d.get("decision_id")
            if not decision_id or decision_id in seen_ids:
                continue
            trading_date = str(d.get("timestamp", ""))[:10] or None
            if not trading_date or trading_date > cutoff:
                summary["skipped_too_recent"] += 1
                continue
            try:
                kda_rec = KDADecisionRecord.from_dict(d)
                bars = _fetch_post_decision_bars(kda_rec.symbol, trading_date, horizon=20)
                entry_px = float(d.get("entry_price") or 0.0) or None
                outcome = engine.evaluate(
                    decision=kda_rec, bars=bars, entry_price=entry_px, trading_date=trading_date,
                )
                joined = {
                    "decision_id": decision_id,
                    "symbol": kda_rec.symbol,
                    "trading_date": trading_date,
                    "direction": kda_rec.direction,
                    "decision": kda_rec.decision.value,
                    "evidence_state": kda_rec.evidence_state.value,
                    "effective_sample_size": kda_rec.effective_sample_size,
                    "stability": kda_rec.authority_components.stability,
                    "contradiction_factor": kda_rec.authority_components.contradiction_factor,
                    "knowledge_authority": kda_rec.knowledge_authority,
                    "status": outcome.status,
                    "direction_correct": outcome.direction_correct,
                    "decision_correct": outcome.decision_correct,
                }
                _append_jsonl(_DATASET_PATH, joined)
                seen_ids.add(decision_id)
                if outcome.status == "OUTCOME_COMPLETE":
                    summary["new_records"] += 1
                else:
                    summary["no_data"] += 1
            except Exception as exc:
                log.debug("[KDA-CRE] outcome join error for %s: %s", decision_id, exc)
    except Exception as exc:
        log.debug("[KDA-CRE] refresh_outcome_dataset error: %s", exc)
    return summary


def _load_dataset(min_date: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _read_jsonl(_DATASET_PATH)
    rows = [r for r in rows if r.get("status") == "OUTCOME_COMPLETE" and r.get("direction_correct") is not None]
    if min_date:
        rows = [r for r in rows if r.get("trading_date", "") >= min_date]
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Statistics (pure functions, mirror ranking_hypothesis_validator_001.py's shape)
# ─────────────────────────────────────────────────────────────────────────────

def _time_split(records: List[Dict], train_fraction: float = TRAIN_FRACTION) -> Tuple[List[Dict], List[Dict]]:
    """Time-ordered train/OOS split by trading_date. Never shuffles -- no leakage."""
    dates = sorted({r.get("trading_date", "") for r in records if r.get("trading_date")})
    if not dates:
        return [], []
    split_idx = max(1, int(len(dates) * train_fraction))
    split_idx = min(split_idx, len(dates) - 1) if len(dates) > 1 else split_idx
    split_date = dates[split_idx] if split_idx < len(dates) else dates[-1]
    train = [r for r in records if r.get("trading_date", "") < split_date]
    oos   = [r for r in records if r.get("trading_date", "") >= split_date]
    return train, oos


def _accuracy(records: List[Dict]) -> Tuple[float, int]:
    if not records:
        return 0.0, 0
    n = len(records)
    correct = sum(1 for r in records if r.get("direction_correct") is True)
    return correct / n, n


def _accepted(records: List[Dict], feature: str, threshold: float) -> List[Dict]:
    return [r for r in records if isinstance(r.get(feature), (int, float)) and r[feature] >= threshold]


def _bootstrap_ci_diff(pop_a: List[Dict], pop_b: List[Dict],
                        iters: int = BOOTSTRAP_ITERS, seed: int = _RNG_SEED) -> Tuple[float, float]:
    """Bootstrap CI on (accuracy(pop_a) - accuracy(pop_b))."""
    if not pop_a or not pop_b:
        return 0.0, 0.0
    a = [1 if r.get("direction_correct") else 0 for r in pop_a]
    b = [1 if r.get("direction_correct") else 0 for r in pop_b]
    rng = random.Random(seed)
    diffs = []
    for _ in range(iters):
        sa = rng.choices(a, k=len(a))
        sb = rng.choices(b, k=len(b))
        diffs.append(sum(sa) / len(sa) - sum(sb) / len(sb))
    diffs.sort()
    lo = diffs[max(0, int(len(diffs) * CI_LOW_PCT / 100.0))]
    hi = diffs[min(len(diffs) - 1, int(len(diffs) * CI_HIGH_PCT / 100.0))]
    return lo, hi


def run_scorecard(records: List[Dict], feature: str, current_value: float,
                   candidate_value: float) -> Dict[str, Any]:
    """
    4-check scorecard comparing the population accepted by `candidate_value`
    against the population accepted by `current_value`. Never raises.
    """
    train, oos = _time_split(records)

    train_cur = _accepted(train, feature, current_value)
    train_cand = _accepted(train, feature, candidate_value)
    oos_cur = _accepted(oos, feature, current_value)
    oos_cand = _accepted(oos, feature, candidate_value)

    train_acc_cur, _ = _accuracy(train_cur)
    train_acc_cand, train_n = _accuracy(train_cand)
    oos_acc_cur, _ = _accuracy(oos_cur)
    oos_acc_cand, oos_n = _accuracy(oos_cand)

    ci_low, ci_high = _bootstrap_ci_diff(oos_cand, oos_cur)

    train_effect = train_acc_cand - train_acc_cur
    oos_effect = oos_acc_cand - oos_acc_cur

    c1_sample = oos_n >= MIN_SAMPLE_FOR_VALIDATION and train_n >= MIN_SAMPLE_FOR_VALIDATION
    c2_ci_excludes_zero = (ci_low > 0) or (ci_high < 0)
    c3_consistent = (train_effect > 0) == (oos_effect > 0) and train_n > 0 and oos_n > 0
    c4_magnitude = abs(oos_effect) >= MIN_EFFECT

    checks = {
        "C1_sample_size": c1_sample, "C2_ci_excludes_zero": c2_ci_excludes_zero,
        "C3_train_oos_consistent": c3_consistent, "C4_effect_magnitude": c4_magnitude,
    }
    passed = sum(1 for v in checks.values() if v)
    validated = passed >= 3 and oos_effect > 0   # only ever move in the improving direction

    return {
        "validated": validated, "checks": checks, "checks_passed": passed, "checks_total": len(checks),
        "train_n": train_n, "oos_n": oos_n,
        "train_acc_candidate": round(train_acc_cand, 4), "train_acc_current": round(train_acc_cur, 4),
        "oos_acc_candidate": round(oos_acc_cand, 4), "oos_acc_current": round(oos_acc_cur, 4),
        "ci_low": round(ci_low, 4), "ci_high": round(ci_high, 4),
        "oos_effect": round(oos_effect, 4), "train_effect": round(train_effect, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Self-scheduling: dynamic, data-driven cooldown (the "precisely calculated duration")
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_dynamic_cooldown_days(dataset: List[Dict]) -> int:
    """
    Minimum days required between two LIVE changes to the same constant.
    Derived from the system's own recently observed outcome-arrival rate,
    not a human guess: floor = ceil(MIN_NEW_EVIDENCE_PER_CHECK / daily_rate),
    but never below ABSOLUTE_MIN_COOLDOWN_DAYS (safety rail against acting
    on a short burst of correlated evidence).
    """
    cutoff = (date.today() - timedelta(days=EVIDENCE_VELOCITY_WINDOW_DAYS)).isoformat()
    recent = [r for r in dataset if r.get("trading_date", "") >= cutoff]
    daily_rate = len(recent) / float(EVIDENCE_VELOCITY_WINDOW_DAYS) if recent else 0.0
    if daily_rate <= 0:
        return ABSOLUTE_MIN_COOLDOWN_DAYS
    calculated = math.ceil(MIN_NEW_EVIDENCE_PER_CHECK / daily_rate)
    return max(ABSOLUTE_MIN_COOLDOWN_DAYS, calculated)


def _load_state() -> Dict[str, Any]:
    return _read_json(_STATE_PATH, {})


def _save_state(state: Dict[str, Any]) -> None:
    _write_json(_STATE_PATH, state)


def _default_const_state() -> Dict[str, Any]:
    return {
        "status": STATUS_WAITING,
        "last_checked_evidence_count": 0,
        "last_change_at": None,
        "shadow_candidate_value": None,
        "shadow_started_at": None,
        "shadow_started_evidence_count": None,
        "promoted_baseline_accuracy": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestration — one call per EOD cycle, fully automated
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    """
    Single EOD entry point. Wrapped in try/except by the caller (mirrors
    every other EOD stage's non-fatal convention). Never raises internally
    either -- every constant is processed independently so one failure
    cannot block the others.
    """
    summary: Dict[str, Any] = {"per_constant": {}}
    try:
        refresh_outcome_dataset()
        dataset = _load_dataset()
        state = _load_state()
        overrides = _read_json(_OVERRIDES_PATH, {})

        for name, cfg in TUNABLE_CONSTANTS.items():
            try:
                result = _process_constant(name, cfg, dataset, state, overrides)
                summary["per_constant"][name] = result
            except Exception as exc:
                log.debug("[KDA-CRE] constant %s processing error: %s", name, exc)
                summary["per_constant"][name] = {"status": "ERROR", "error": str(exc)}

        _save_state(state)
        _write_json(_OVERRIDES_PATH, overrides)
    except Exception as exc:
        log.debug("[KDA-CRE] run_daily_refinement_check error: %s", exc)
        summary["error"] = str(exc)
    return summary


def _process_constant(
    name: str, cfg: Dict[str, Any], dataset: List[Dict[str, Any]],
    state: Dict[str, Any], overrides: Dict[str, Any],
) -> Dict[str, Any]:
    const_state = state.setdefault(name, _default_const_state())
    current_value = float(overrides.get(name, {}).get("value", cfg["default"]))

    # ── Stage 1: rollback monitor for an already-ACTIVE (live) override ──────
    if const_state["status"] == STATUS_ACTIVE and const_state.get("last_change_at"):
        post = [r for r in dataset if r.get("trading_date", "") >= const_state["last_change_at"][:10]]
        if len(post) >= MIN_POST_PROMOTION_SAMPLE:
            accepted = _accepted(post, cfg["feature"], current_value)
            live_acc, live_n = _accuracy(accepted)
            baseline = const_state.get("promoted_baseline_accuracy")
            if baseline is not None and live_n >= MIN_POST_PROMOTION_SAMPLE and (baseline - live_acc) > ROLLBACK_DEGRADATION_PP:
                old_value = current_value
                # revert to whatever value preceded this promotion, else the hardcoded default
                reverted_value = const_state.get("pre_promotion_value", cfg["default"])
                overrides[name] = {"value": reverted_value, "set_at": datetime.now(timezone.utc).isoformat()}
                const_state["status"] = STATUS_ROLLED_BACK
                const_state["last_change_at"] = datetime.now(timezone.utc).isoformat()
                _log_ledger(
                    "ROLLED_BACK", name,
                    reason=(f"Live accuracy {round(live_acc,4)} on n={live_n} degraded "
                            f"{round(baseline-live_acc,4)} vs promotion baseline {baseline} "
                            f"(> {ROLLBACK_DEGRADATION_PP} threshold)."),
                    old_value=old_value, new_value=reverted_value, sample=live_n,
                )
                return {"status": STATUS_ROLLED_BACK, "old_value": old_value, "new_value": reverted_value}

    # ── Stage 2: judge a pending SHADOW candidate ─────────────────────────────
    if const_state["status"] == STATUS_SHADOW:
        started_at = const_state.get("shadow_started_at")
        started_evidence = const_state.get("shadow_started_evidence_count") or 0
        days_elapsed = (date.today() - date.fromisoformat(started_at[:10])).days if started_at else 0
        new_since_start = [r for r in dataset if r.get("trading_date", "") >= (started_at or "")[:10]]

        if days_elapsed < SHADOW_MIN_DAYS or len(new_since_start) < SHADOW_MIN_NEW_OUTCOMES:
            return {"status": STATUS_SHADOW, "days_elapsed": days_elapsed, "new_since_start": len(new_since_start)}

        candidate_value = const_state["shadow_candidate_value"]
        # Re-validate on ONLY the new, held-out, post-shadow-start data -- genuine
        # out-of-sample confirmation, never the same data used to propose it.
        scorecard = run_scorecard(new_since_start, cfg["feature"], current_value, candidate_value)

        if scorecard["validated"]:
            pre_value = current_value
            overrides[name] = {"value": candidate_value, "set_at": datetime.now(timezone.utc).isoformat()}
            accepted_now = _accepted(new_since_start, cfg["feature"], candidate_value)
            baseline_acc, _ = _accuracy(accepted_now)
            const_state.update({
                "status": STATUS_ACTIVE,
                "last_change_at": datetime.now(timezone.utc).isoformat(),
                "pre_promotion_value": pre_value,
                "promoted_baseline_accuracy": baseline_acc,
                "shadow_candidate_value": None, "shadow_started_at": None,
                "shadow_started_evidence_count": None,
            })
            _log_ledger(
                "PROMOTED", name,
                reason=(f"Shadow-confirmed on held-out data: OOS effect={scorecard['oos_effect']}, "
                        f"{scorecard['checks_passed']}/{scorecard['checks_total']} checks passed."),
                old_value=pre_value, new_value=candidate_value, evidence=scorecard,
            )
            return {"status": STATUS_ACTIVE, "old_value": pre_value, "new_value": candidate_value}
        else:
            const_state.update({
                "status": STATUS_REJECTED, "shadow_candidate_value": None,
                "shadow_started_at": None, "shadow_started_evidence_count": None,
            })
            _log_ledger(
                "REJECTED", name,
                reason=(f"Shadow period failed to reconfirm the effect on held-out data: "
                        f"{scorecard['checks_passed']}/{scorecard['checks_total']} checks passed."),
                old_value=current_value, candidate_value=candidate_value, evidence=scorecard,
            )
            const_state["status"] = STATUS_WAITING
            return {"status": STATUS_REJECTED, "candidate_value": candidate_value}

    # ── Stage 3: evidence-driven + cooldown-gated trigger for a NEW candidate ─
    total_evidence = len(dataset)
    new_since_last_check = total_evidence - const_state.get("last_checked_evidence_count", 0)
    if new_since_last_check < MIN_NEW_EVIDENCE_PER_CHECK:
        return {"status": STATUS_WAITING, "reason": "insufficient_new_evidence",
                "new_since_last_check": new_since_last_check, "required": MIN_NEW_EVIDENCE_PER_CHECK}

    cooldown_days = _calculate_dynamic_cooldown_days(dataset)
    if const_state.get("last_change_at"):
        days_since_change = (datetime.now(timezone.utc) - datetime.fromisoformat(const_state["last_change_at"])).days
        if days_since_change < cooldown_days:
            return {"status": STATUS_WAITING, "reason": "cooldown_active",
                    "days_since_change": days_since_change, "cooldown_required": cooldown_days}

    const_state["last_checked_evidence_count"] = total_evidence

    step = cfg["step"]
    candidates = [
        v for v in (current_value + step, current_value - step)
        if cfg["min"] <= v <= cfg["max"]
    ]
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for cand in candidates:
        scorecard = run_scorecard(dataset, cfg["feature"], current_value, cand)
        if scorecard["validated"] and (best is None or scorecard["oos_effect"] > best[1]["oos_effect"]):
            best = (cand, scorecard)

    if best is None:
        return {"status": STATUS_WAITING, "reason": "no_validated_candidate",
                "new_since_last_check": new_since_last_check}

    cand_value, scorecard = best
    const_state.update({
        "status": STATUS_SHADOW,
        "shadow_candidate_value": cand_value,
        "shadow_started_at": datetime.now(timezone.utc).isoformat(),
        "shadow_started_evidence_count": total_evidence,
    })
    _log_ledger(
        "SHADOW_STARTED", name,
        reason=(f"Evidence trigger fired ({new_since_last_check} new outcomes, "
                f"cooldown={cooldown_days}d satisfied). Initial scorecard: "
                f"OOS effect={scorecard['oos_effect']}, "
                f"{scorecard['checks_passed']}/{scorecard['checks_total']} checks passed. "
                f"Must reconfirm on held-out data for >= {SHADOW_MIN_DAYS} days / "
                f">= {SHADOW_MIN_NEW_OUTCOMES} new outcomes before promotion."),
        old_value=current_value, candidate_value=cand_value, evidence=scorecard,
    )
    return {"status": STATUS_SHADOW, "candidate_value": cand_value}
