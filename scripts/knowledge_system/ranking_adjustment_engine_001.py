"""
scripts/knowledge_system/ranking_adjustment_engine_001.py
============================================================
Ranking Self-Learning Loop (RSL-001) — Stage B: Automated Ranking
Adjustment Engine (Phase E).

Isolated, standalone equivalent of OIOS's shadow-mode/pending_adjustments
pattern (oios/engine/adaptive_intelligence.py, shadow_mode.py) — same
conceptual shape (guardrails, shadow-then-live, auto-rollback), reused as
a TEMPLATE only. Zero imports from oios/, zero shared storage. This
module owns its own store: data/ksl/ranking_shadow_candidates.json.

Lifecycle (fully automated, no human step at any transition):
  SHADOW_ELIGIBLE  -- a validated hypothesis (RHV-001 verdict=VALIDATED)
                      registered here, not yet observed live.
  SHADOW_ACTIVE    -- parallel/shadow scoring is being computed (via
                      annotate_adjusted_scores) alongside the live,
                      unmodified C2 ranking. Zero effect on real
                      selection while in this state.
  ACTIVE           -- shadow period confirmed the effect; the adjustment
                      now actually influences selection (bounded, small,
                      reversible — see apply guardrails below).
  ROLLED_BACK      -- live performance degraded past the guardrail;
                      automatically reverted. No human step.
  REJECTED         -- shadow period failed to confirm the effect.

Guardrails (values chosen to mirror OIOS's already-proven numbers,
reused as constants only — no code coupling):
  MIN_OBS_FOR_ACTIVATION   min shadow-period sample before a promotion
                           decision is made
  MAX_WEIGHT               bounded contribution cap (secondary key can
                           never dominate c2_score)
  COOLDOWN_DAYS            no repeat activation attempts for the same
                           feature within this window
  ROLLBACK_DEGRADATION_PP  live post-activation correct-select rate
                           dropping this many percentage points below
                           the OOS baseline triggers auto-revert

Safety: this module only ever writes to files under data/ksl/. It never
imports execution_engine, order_manager, dhan_feed, or any live trading
module, and the C2 selector's frozen scoring formula
(opportunity_engine/final_c2_selector.py) is never modified. The only
consumer of this module's output is the shadow-only observer
scripts/final_trading_architecture_shadow_001.py.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.knowledge_system.ksl_models import KnowledgeFinding, KSLShadowCandidate

# ─────────────────────────────────────────────────────────────────────────────
# Storage paths — isolated from OIOS (data/ksl/ only, never oios/ or market_behavior.db)
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES_PATH   = ROOT / "data" / "ksl" / "ranking_shadow_candidates.json"
ACTIVE_CONFIG_PATH = ROOT / "data" / "ksl" / "active_ranking_adjustments.json"
SHADOW_JSONL_PATH  = ROOT / "data" / "logs" / "final_trading_architecture_shadow_001.jsonl"

# ─────────────────────────────────────────────────────────────────────────────
# Guardrails (mirrors OIOS's proven numbers — reused as constants only)
# ─────────────────────────────────────────────────────────────────────────────

STATUS_SHADOW_ELIGIBLE = "SHADOW_ELIGIBLE"
STATUS_SHADOW_ACTIVE   = "SHADOW_ACTIVE"
STATUS_ACTIVE          = "ACTIVE"
STATUS_ROLLED_BACK     = "ROLLED_BACK"
STATUS_REJECTED        = "REJECTED"

REQUIRED_OBSERVATION_DAYS = 10       # min new trading dates before a promotion decision
MIN_OBS_FOR_ACTIVATION    = 20       # min qualifying evidence rows in the shadow window
MAX_WEIGHT                = 0.15     # bounded contribution cap (mirrors OIOS's +-15%)
DEFAULT_WEIGHT            = 0.10     # starting bounded weight when first promoted to ACTIVE
COOLDOWN_DAYS             = 90       # one activation attempt per feature per quarter
ROLLBACK_DEGRADATION_PP   = 0.05     # 5pp degradation vs OOS baseline triggers auto-revert
MIN_OBS_FOR_ROLLBACK_CHECK = 20      # min post-activation rows before judging rollback
MAX_CONCURRENT_SHADOW     = 5        # sanity cap on simultaneously shadow-tested features


def _feature_id(area: str, direction: str, miss_reason: Optional[str]) -> str:
    return f"{area}|{direction}|{miss_reason or 'UNKNOWN'}"


# ─────────────────────────────────────────────────────────────────────────────
# Store I/O (atomic writes — mirrors HypothesisRegistry's write-to-temp pattern)
# ─────────────────────────────────────────────────────────────────────────────

def _load_candidates() -> List[KSLShadowCandidate]:
    if not CANDIDATES_PATH.exists():
        return []
    try:
        raw = json.loads(CANDIDATES_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [KSLShadowCandidate.from_dict(d) for d in raw]


def _save_candidates(candidates: List[KSLShadowCandidate]) -> None:
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CANDIDATES_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps([c.to_dict() for c in candidates], indent=2, default=str))
    os.replace(tmp, CANDIDATES_PATH)


def _load_active_config() -> Dict[str, Any]:
    if not ACTIVE_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(ACTIVE_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_active_config(config: Dict[str, Any]) -> None:
    ACTIVE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ACTIVE_CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2, default=str))
    os.replace(tmp, ACTIVE_CONFIG_PATH)


def _load_raw_shadow_records(since_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read SHADOW_CANDIDATE rows from the raw shadow JSONL (has RSL-001 fields)."""
    if not SHADOW_JSONL_PATH.exists():
        return []
    out = []
    with open(SHADOW_JSONL_PATH) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("record_type") != "SHADOW_CANDIDATE":
                continue
            if since_date and r.get("trade_date", "") < since_date:
                continue
            out.append(r)
    return out


def _ge2(rec: Dict[str, Any]) -> Optional[bool]:
    t1 = rec.get("t1_ret_pct")
    if t1 is None:
        return None
    direction = rec.get("direction")
    correct = (direction == "UP" and t1 > 0) or (direction == "DOWN" and t1 < 0)
    return bool(correct and abs(t1) >= 2.0)


# ─────────────────────────────────────────────────────────────────────────────
# Stage B1 — registration (called by ranking_hypothesis_validator_001 on VALIDATED)
# ─────────────────────────────────────────────────────────────────────────────

def register_shadow_candidate(
    finding: KnowledgeFinding,
    area: str,
    direction: str,
    miss_reason: Optional[str],
    scorecard: Dict[str, Any],
) -> Optional[KSLShadowCandidate]:
    """
    Register a validated hypothesis as a shadow-eligible candidate.
    Enforces cooldown + concurrency guardrails. Returns None if blocked.
    """
    feat_id = _feature_id(area, direction, miss_reason)
    candidates = _load_candidates()

    active_states = (STATUS_SHADOW_ELIGIBLE, STATUS_SHADOW_ACTIVE, STATUS_ACTIVE)
    live_count = sum(1 for c in candidates if c.status in active_states)
    if live_count >= MAX_CONCURRENT_SHADOW:
        print(f"[RAE-001] Blocked — MAX_CONCURRENT_SHADOW ({MAX_CONCURRENT_SHADOW}) reached.")
        return None

    today = date.today().isoformat()
    for c in candidates:
        if c.feature_id == feat_id and c.status in active_states:
            print(f"[RAE-001] Blocked — feature '{feat_id}' already {c.status}.")
            return None
        if c.feature_id == feat_id and c.created_at[:10] >= _cooldown_floor(today):
            print(f"[RAE-001] Blocked — feature '{feat_id}' within {COOLDOWN_DAYS}-day cooldown.")
            return None

    candidate = KSLShadowCandidate(
        candidate_id=f"RSL-{uuid.uuid4().hex[:12]}",
        research_question_id=finding.research_question_id,
        finding_id=finding.finding_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        baseline_version="FINAL_TRADING_ARCHITECTURE_SHADOW_001_v1",
        candidate_version=f"FINAL_TRADING_ARCHITECTURE_SHADOW_001_v1+ADJ:{feat_id}",
        reason=f"RHV-001 validated: {scorecard['checks_passed']}/{scorecard['checks_total']} scorecard, "
               f"OOS effect={scorecard['oos_effect']} (miss_rate {scorecard['oos_miss_rate']} vs "
               f"baseline {scorecard['baseline']}), CI=[{scorecard['ci_low']},{scorecard['ci_high']}]",
        evidence=f"train_n={scorecard['train_n']} oos_n={scorecard['oos_n']}",
        oos_dir_acc=round(1.0 - scorecard["oos_miss_rate"], 4),
        oos_ge2_rate=round(scorecard["oos_miss_rate"], 4),
        expected_improvement=f"Reduce {miss_reason} misses via bounded v3_score secondary key "
                              f"(weight<={MAX_WEIGHT})",
        risk="LOW — observation-only shadow system, never touches live/paper trading",
        required_observation_days=REQUIRED_OBSERVATION_DAYS,
        promotion_requirements=(
            f"Shadow period (>= {REQUIRED_OBSERVATION_DAYS} new trading dates, "
            f">= {MIN_OBS_FOR_ACTIVATION} qualifying rows) must replicate the same-signed "
            f"effect before promotion to ACTIVE."
        ),
        status=STATUS_SHADOW_ELIGIBLE,
        feature_id=feat_id,
        status_reason="Registered from RHV-001 validated finding.",
    )
    candidates.append(candidate)
    _save_candidates(candidates)
    return candidate


def _cooldown_floor(today_iso: str) -> str:
    from datetime import timedelta
    d = date.fromisoformat(today_iso) - timedelta(days=COOLDOWN_DAYS)
    return d.isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Stage B2 — shadow tracking (daily, EOD-loop wired)
# ─────────────────────────────────────────────────────────────────────────────

def advance_shadow_tracking() -> Dict[str, Any]:
    """
    Activate newly-eligible candidates into shadow observation; promote
    confirmed ones to ACTIVE; reject unconfirmed ones. Fully automated.
    """
    summary = {"activated_shadow": 0, "promoted_live": 0, "rejected": 0}
    candidates = _load_candidates()
    if not candidates:
        return summary

    today = date.today().isoformat()
    changed = False

    for c in candidates:
        if c.status == STATUS_SHADOW_ELIGIBLE:
            c.status = STATUS_SHADOW_ACTIVE
            c.shadow_start_date = today
            c.shadow_activated_at = datetime.now(timezone.utc).isoformat()
            c.status_reason = "Shadow observation started."
            summary["activated_shadow"] += 1
            changed = True

    for c in candidates:
        if c.status != STATUS_SHADOW_ACTIVE or not c.shadow_start_date:
            continue
        area, direction, miss_reason = (c.feature_id.split("|") + [None, None, None])[:3]
        window = _load_raw_shadow_records(since_date=c.shadow_start_date)
        window = [r for r in window if r.get("direction") == direction]
        distinct_dates = {r.get("trade_date") for r in window if r.get("trade_date")}
        if len(distinct_dates) < REQUIRED_OBSERVATION_DAYS:
            continue

        qualifying = [r for r in window if r.get("would_select_adjusted") is not None]
        if len(qualifying) < MIN_OBS_FOR_ACTIVATION:
            continue

        # Shadow effect: among candidates the ADJUSTED ranking would newly select
        # (would_select_adjusted=True, selected_final_5=False under the frozen
        # ranking), what fraction are real >=2% movers?
        would_select_new = [r for r in qualifying
                             if r.get("would_select_adjusted") and not r.get("selected_final_5")]
        if len(would_select_new) < 5:
            c.status = STATUS_REJECTED
            c.status_reason = "Shadow period produced too few new-selection candidates to judge."
            changed = True
            continue

        hits = sum(1 for r in would_select_new if _ge2(r))
        hit_rate = hits / len(would_select_new)

        if hit_rate >= (1.0 - c.oos_dir_acc) * 0.8:  # within 80% of the OOS-projected capture rate
            c.status = STATUS_ACTIVE
            c.live_activated_at = datetime.now(timezone.utc).isoformat()
            c.status_reason = f"Shadow confirmed: hit_rate={round(hit_rate, 4)} on n={len(would_select_new)}."
            _activate_in_config(c)
            summary["promoted_live"] += 1
        else:
            c.status = STATUS_REJECTED
            c.status_reason = f"Shadow failed to confirm: hit_rate={round(hit_rate, 4)} on n={len(would_select_new)}."
            summary["rejected"] += 1
        changed = True

    if changed:
        _save_candidates(candidates)
    return summary


def _activate_in_config(candidate: KSLShadowCandidate) -> None:
    parts = candidate.feature_id.split("|")
    direction = parts[1] if len(parts) > 1 else "UP"
    miss_reason = parts[2] if len(parts) > 2 else None
    config = _load_active_config()
    config[direction] = {
        "candidate_id": candidate.candidate_id,
        "feature_id": candidate.feature_id,
        "miss_reason": miss_reason,
        "weight": DEFAULT_WEIGHT,
        "activated_at": candidate.live_activated_at,
        "baseline_oos_dir_acc": candidate.oos_dir_acc,
    }
    _save_active_config(config)


# ─────────────────────────────────────────────────────────────────────────────
# Stage B3 — auto-rollback monitor (daily, EOD-loop wired)
# ─────────────────────────────────────────────────────────────────────────────

def check_rollback() -> Dict[str, Any]:
    """Monitor ACTIVE adjustments for post-activation degradation; auto-revert."""
    summary = {"checked": 0, "rolled_back": 0}
    candidates = _load_candidates()
    active = [c for c in candidates if c.status == STATUS_ACTIVE and c.live_activated_at]
    if not active:
        return summary

    changed = False
    for c in active:
        summary["checked"] += 1
        parts = c.feature_id.split("|")
        direction = parts[1] if len(parts) > 1 else "UP"
        activation_date = c.live_activated_at[:10]
        window = _load_raw_shadow_records(since_date=activation_date)
        window = [r for r in window if r.get("direction") == direction and r.get("selected_final_5")]
        if len(window) < MIN_OBS_FOR_ROLLBACK_CHECK:
            continue

        hits = sum(1 for r in window if _ge2(r))
        live_dir_acc = hits / len(window)

        if (c.oos_dir_acc - live_dir_acc) > ROLLBACK_DEGRADATION_PP:
            c.status = STATUS_ROLLED_BACK
            c.rolled_back_at = datetime.now(timezone.utc).isoformat()
            c.status_reason = (
                f"Auto-rollback: live_dir_acc={round(live_dir_acc, 4)} vs "
                f"OOS baseline={c.oos_dir_acc} (degradation > {ROLLBACK_DEGRADATION_PP})."
            )
            _deactivate_in_config(direction)
            summary["rolled_back"] += 1
            changed = True

    if changed:
        _save_candidates(candidates)
    return summary


def _deactivate_in_config(direction: str) -> None:
    config = _load_active_config()
    if direction in config:
        del config[direction]
        _save_active_config(config)


# ─────────────────────────────────────────────────────────────────────────────
# Shadow-scoring hook — consumed by scripts/final_trading_architecture_shadow_001.py
# ─────────────────────────────────────────────────────────────────────────────

def annotate_adjusted_scores(recs: List[Dict[str, Any]], direction: str) -> List[Dict[str, Any]]:
    """
    Additive, always-safe hook. Computes a parallel adjusted score for
    every candidate (cheap, observation-only) so shadow tracking has data
    to judge. Only OVERRIDES the real c2_score/ranking when this
    direction has an ACTIVE adjustment — before that, this function never
    changes selection behaviour. Never raises; returns `recs` unchanged
    on any error.
    """
    try:
        config = _load_active_config()
        active_entry = config.get(direction)
        weight = active_entry["weight"] if active_entry else DEFAULT_WEIGHT
        weight = max(0.0, min(weight, MAX_WEIGHT))

        v3_scores = [float(r.get("v3_score") or 0.0) for r in recs]
        max_v3 = max(v3_scores) if v3_scores else 0.0

        for r in recs:
            c2 = r.get("c2_score")
            if c2 is None:
                continue
            v3 = float(r.get("v3_score") or 0.0)
            v3_norm = (v3 / max_v3) if max_v3 > 0 else 0.0
            adjusted = c2 + weight * v3_norm
            r["c2_score_shadow_adjusted"] = round(adjusted, 6)

        if active_entry:
            # Rank purely by the adjusted score to compute would-select flags.
            ranked = sorted(
                [r for r in recs if r.get("c2_score_shadow_adjusted") is not None],
                key=lambda r: -r["c2_score_shadow_adjusted"],
            )
            top_symbols = {r["symbol"] for r in ranked[:5]} if ranked else set()
            for r in recs:
                r["would_select_adjusted"] = r.get("symbol") in top_symbols

            # ACTIVE: this direction's live adjustment actually changes selection.
            for r in recs:
                if r.get("c2_score_shadow_adjusted") is not None:
                    r["c2_score"] = r["c2_score_shadow_adjusted"]
                    r["ranking_adjustment_applied"] = active_entry["candidate_id"]
        else:
            # SHADOW_ACTIVE-only: compute would_select_adjusted for observation,
            # never touch the real c2_score used for actual selection.
            ranked = sorted(
                [r for r in recs if r.get("c2_score_shadow_adjusted") is not None],
                key=lambda r: -r["c2_score_shadow_adjusted"],
            )
            top_symbols = {r["symbol"] for r in ranked[:5]} if ranked else set()
            for r in recs:
                r["would_select_adjusted"] = r.get("symbol") in top_symbols

        return recs
    except Exception as exc:
        print(f"[RAE-001] annotate_adjusted_scores failed (non-fatal, recs unchanged): {exc}")
        return recs


if __name__ == "__main__":
    print(json.dumps({
        "shadow_tracking": advance_shadow_tracking(),
        "rollback_check": check_rollback(),
    }, indent=2, default=str))
