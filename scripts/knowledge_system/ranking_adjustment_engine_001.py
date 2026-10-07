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
  SHADOW_ELIGIBLE     -- a validated hypothesis (RHV-001 verdict=VALIDATED)
                         registered here, not yet observed live.
  SHADOW_ACTIVE       -- parallel/shadow scoring is being computed (via
                         annotate_adjusted_scores) alongside the live,
                         unmodified C2 ranking. Zero effect on real
                         selection while in this state.
  PROVISIONAL_ACTIVE  -- DTA-RSL-PROVISIONAL-001: a REDUCED evidence bar
                         (fewer qualifying rows/new-picks than full
                         authentication) has been met with a non-negative
                         signal. Lets partially-authenticated research
                         become part of shadow selection NOW, at a small,
                         bounded weight (PROVISIONAL_WEIGHT) -- instead of
                         sitting at zero influence until the full bar is
                         reached. Continues accumulating evidence every
                         cycle; graduates to full ACTIVE (full weight)
                         the moment it also clears the original, stricter
                         bar -- i.e. "more research -> re-authenticate at
                         the original, higher standard", not a permanent
                         relaxation. Still subject to the same rollback
                         monitor as ACTIVE, just at a lower sample floor.
  ACTIVE              -- the ORIGINAL, full evidence bar is met; the
                         adjustment influences selection at full weight
                         (bounded, reversible — see guardrails below).
  ROLLED_BACK         -- live performance degraded past the guardrail;
                         automatically reverted. No human step.
  REJECTED            -- shadow period failed to confirm the effect, or
                         produced no usable signal within the maximum
                         observation window.

Guardrails (values chosen to mirror OIOS's already-proven numbers,
reused as constants only — no code coupling):
  MIN_OBS_FOR_ACTIVATION   min shadow-period sample before a FULL (ACTIVE)
                           promotion decision is made -- unchanged, this
                           is the "original idea of authentication"
  MIN_NEW_PICKS_FOR_FULL   min genuinely-new picks for FULL authentication
  MIN_NEW_PICKS_FOR_PROVISIONAL  lower bar for PROVISIONAL_ACTIVE -- gives
                           research a bounded, small, real voice before
                           enough evidence exists for full authentication
  PROVISIONAL_WEIGHT       smaller contribution cap for PROVISIONAL_ACTIVE
                           (a fraction of DEFAULT_WEIGHT)
  MAX_OBSERVATION_DAYS     fail-safe: reject if NEITHER bar is ever met
                           within this many trading dates (prevents an
                           indefinite, silently-stuck shadow candidate)
  MAX_WEIGHT               bounded contribution cap (secondary key can
                           never dominate c2_score)
  COOLDOWN_DAYS            no repeat activation attempts for the same
                           feature within this window -- recalibrated for
                           this early-stage system's real evidence
                           velocity (see constant comment); expected to
                           lengthen again once evidence volume grows
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

STATUS_SHADOW_ELIGIBLE    = "SHADOW_ELIGIBLE"
STATUS_SHADOW_ACTIVE      = "SHADOW_ACTIVE"
STATUS_PROVISIONAL_ACTIVE = "PROVISIONAL_ACTIVE"
STATUS_ACTIVE             = "ACTIVE"
STATUS_ROLLED_BACK        = "ROLLED_BACK"
STATUS_REJECTED           = "REJECTED"

REQUIRED_OBSERVATION_DAYS = 10       # min new trading dates before ANY promotion decision
MIN_OBS_FOR_ACTIVATION    = 20       # min qualifying evidence rows for FULL (ACTIVE) authentication
MIN_NEW_PICKS_FOR_FULL    = 5        # min genuinely-new picks for FULL (ACTIVE) authentication
MAX_WEIGHT                = 0.15     # bounded contribution cap (mirrors OIOS's +-15%)
DEFAULT_WEIGHT            = 0.10     # full weight once FULLY authenticated (ACTIVE)

# DTA-RSL-PROVISIONAL-001: at this early stage the system has near-zero
# accumulated evidence (confirmed live: 0 ACTIVE promotions ever) -- the
# full MIN_OBS_FOR_ACTIVATION/MIN_NEW_PICKS_FOR_FULL bar is the right
# long-term standard but leaves research with ZERO real influence while
# evidence is still thin. PROVISIONAL_ACTIVE gives a reduced-bar, smaller-
# weight tier so partially-authenticated research has SOME bounded voice
# now; it still must clear the ORIGINAL full bar above to reach full
# weight -- this is re-authentication at the original standard once more
# data exists, not a permanent relaxation.
MIN_NEW_PICKS_FOR_PROVISIONAL = 2    # reduced bar -- intentionally << MIN_NEW_PICKS_FOR_FULL
PROVISIONAL_WEIGHT            = 0.05 # half of DEFAULT_WEIGHT -- small, bounded, cautious
MIN_OBS_FOR_ROLLBACK_CHECK_PROVISIONAL = 10  # lower post-promotion monitoring floor, proportional to the smaller weight's smaller downside
MAX_OBSERVATION_DAYS      = 30       # fail-safe: reject if NEITHER bar is ever met by this many trading dates

# COOLDOWN_DAYS: was 90 (one quarter) -- sized for a mature system already
# generating lots of evidence. Recalibrated to this early-stage system's
# real evidence velocity (confirmed live: ~0.25 new-picks/day system-wide
# before the DTA-RSL-SCALE-FIX-001 formula fix). Expected to lengthen again
# once real evidence volume grows -- this is a realistic value for right
# now, not a permanent loosening.
COOLDOWN_DAYS             = 30       # one retry attempt per feature per month
ROLLBACK_DEGRADATION_PP   = 0.05     # 5pp degradation vs OOS baseline triggers auto-revert
MIN_OBS_FOR_ROLLBACK_CHECK = 20      # min post-ACTIVE-activation rows before judging rollback
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

    active_states = (STATUS_SHADOW_ELIGIBLE, STATUS_SHADOW_ACTIVE, STATUS_PROVISIONAL_ACTIVE, STATUS_ACTIVE)
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
            f"Shadow period (>= {REQUIRED_OBSERVATION_DAYS} new trading dates): "
            f">= {MIN_NEW_PICKS_FOR_PROVISIONAL} new-selection rows with a non-negative signal "
            f"-> PROVISIONAL_ACTIVE (weight={PROVISIONAL_WEIGHT}); "
            f">= {MIN_OBS_FOR_ACTIVATION} qualifying rows AND >= {MIN_NEW_PICKS_FOR_FULL} new-selection "
            f"rows replicating the same-signed effect -> full ACTIVE (weight={DEFAULT_WEIGHT})."
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
        if c.status not in (STATUS_SHADOW_ACTIVE, STATUS_PROVISIONAL_ACTIVE) or not c.shadow_start_date:
            continue
        area, direction, miss_reason = (c.feature_id.split("|") + [None, None, None])[:3]
        window = _load_raw_shadow_records(since_date=c.shadow_start_date)
        window = [r for r in window if r.get("direction") == direction]
        distinct_dates = {r.get("trade_date") for r in window if r.get("trade_date")}
        if len(distinct_dates) < REQUIRED_OBSERVATION_DAYS:
            continue

        qualifying = [r for r in window if r.get("would_select_adjusted") is not None]

        # Shadow effect: among candidates the ADJUSTED ranking would newly select
        # (would_select_adjusted=True, selected_final_5=False under the frozen
        # ranking), what fraction are real >=2% movers?
        would_select_new = [r for r in qualifying
                             if r.get("would_select_adjusted") and not r.get("selected_final_5")]

        full_bar_met = len(qualifying) >= MIN_OBS_FOR_ACTIVATION and len(would_select_new) >= MIN_NEW_PICKS_FOR_FULL
        provisional_bar_met = len(would_select_new) >= MIN_NEW_PICKS_FOR_PROVISIONAL

        if not full_bar_met and not provisional_bar_met:
            # DTA-RSL-PROVISIONAL-001 fail-safe: no usable signal of ANY kind yet.
            # Keep waiting (research deserves time), but not forever.
            if len(distinct_dates) >= MAX_OBSERVATION_DAYS:
                c.status = STATUS_REJECTED
                c.status_reason = (
                    f"No usable signal within the maximum observation window "
                    f"({MAX_OBSERVATION_DAYS} trading dates)."
                )
                summary["rejected"] += 1
                changed = True
            continue

        hits = sum(1 for r in would_select_new if _ge2(r)) if would_select_new else 0
        hit_rate = (hits / len(would_select_new)) if would_select_new else 0.0
        hit_rate_ok = hit_rate >= (1.0 - c.oos_dir_acc) * 0.8  # within 80% of the OOS-projected capture rate

        if full_bar_met and hit_rate_ok:
            # The ORIGINAL, full authentication bar is met -- promote/graduate
            # to full weight regardless of whether this candidate arrived here
            # via SHADOW_ACTIVE directly or via PROVISIONAL_ACTIVE first.
            c.status = STATUS_ACTIVE
            c.live_activated_at = datetime.now(timezone.utc).isoformat()
            c.status_reason = f"Fully authenticated: hit_rate={round(hit_rate, 4)} on n={len(would_select_new)}."
            _activate_in_config(c, weight=DEFAULT_WEIGHT)
            summary["promoted_live"] += 1
            changed = True
        elif full_bar_met and not hit_rate_ok:
            c.status = STATUS_REJECTED
            c.status_reason = f"Shadow failed to confirm: hit_rate={round(hit_rate, 4)} on n={len(would_select_new)}."
            summary["rejected"] += 1
            changed = True
        elif provisional_bar_met and hit_rate_ok:
            if c.status != STATUS_PROVISIONAL_ACTIVE:
                c.status = STATUS_PROVISIONAL_ACTIVE
                if not c.live_activated_at:
                    c.live_activated_at = datetime.now(timezone.utc).isoformat()
                c.status_reason = (
                    f"Provisionally authenticated (reduced bar): hit_rate={round(hit_rate, 4)} "
                    f"on n={len(would_select_new)}. Continuing to accumulate evidence toward "
                    f"full authentication (needs n>={MIN_NEW_PICKS_FOR_FULL})."
                )
                _activate_in_config(c, weight=PROVISIONAL_WEIGHT)
                summary["provisional_activated"] = summary.get("provisional_activated", 0) + 1
                changed = True
            # else: already PROVISIONAL_ACTIVE and still holding up -- keep
            # accumulating, no status change needed this cycle.
        else:
            # provisional_bar_met but NOT hit_rate_ok
            if c.status == STATUS_PROVISIONAL_ACTIVE:
                # Evidence turned negative after being provisionally trusted -- revert.
                c.status = STATUS_REJECTED
                c.status_reason = (
                    f"Provisional evidence turned negative before reaching full "
                    f"authentication: hit_rate={round(hit_rate, 4)} on n={len(would_select_new)}."
                )
                _deactivate_in_config(direction)
                summary["rejected"] += 1
                changed = True
            # else: still SHADOW_ACTIVE with a weak signal -- let it keep
            # accumulating rather than reject outright (same fail-safe as above).

    if changed:
        _save_candidates(candidates)
    return summary


def _activate_in_config(candidate: KSLShadowCandidate, weight: float = DEFAULT_WEIGHT) -> None:
    parts = candidate.feature_id.split("|")
    direction = parts[1] if len(parts) > 1 else "UP"
    miss_reason = parts[2] if len(parts) > 2 else None
    config = _load_active_config()
    config[direction] = {
        "candidate_id": candidate.candidate_id,
        "feature_id": candidate.feature_id,
        "miss_reason": miss_reason,
        "weight": max(0.0, min(weight, MAX_WEIGHT)),
        "activated_at": candidate.live_activated_at,
        "baseline_oos_dir_acc": candidate.oos_dir_acc,
    }
    _save_active_config(config)


# ─────────────────────────────────────────────────────────────────────────────
# Stage B3 — auto-rollback monitor (daily, EOD-loop wired)
# ─────────────────────────────────────────────────────────────────────────────

def check_rollback() -> Dict[str, Any]:
    """Monitor ACTIVE and PROVISIONAL_ACTIVE adjustments for post-activation
    degradation; auto-revert. PROVISIONAL_ACTIVE uses a proportionally lower
    sample floor (MIN_OBS_FOR_ROLLBACK_CHECK_PROVISIONAL) since its smaller
    weight carries smaller downside risk."""
    summary = {"checked": 0, "rolled_back": 0}
    candidates = _load_candidates()
    monitored = [c for c in candidates
                 if c.status in (STATUS_ACTIVE, STATUS_PROVISIONAL_ACTIVE) and c.live_activated_at]
    if not monitored:
        return summary

    changed = False
    for c in monitored:
        summary["checked"] += 1
        parts = c.feature_id.split("|")
        direction = parts[1] if len(parts) > 1 else "UP"
        activation_date = c.live_activated_at[:10]
        window = _load_raw_shadow_records(since_date=activation_date)
        window = [r for r in window if r.get("direction") == direction and r.get("selected_final_5")]
        min_obs = MIN_OBS_FOR_ROLLBACK_CHECK if c.status == STATUS_ACTIVE else MIN_OBS_FOR_ROLLBACK_CHECK_PROVISIONAL
        if len(window) < min_obs:
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


def get_active_adjustments_status() -> Dict[str, Any]:
    """
    Read-only accessor (Phase 7 "Sandy" supervisor): current shadow
    candidates (feature_id/status/status_reason/created_at) plus the
    currently ACTIVE per-direction adjustments. Never mutates any state.
    Never raises.
    """
    try:
        candidates = _load_candidates()
        active_config = _load_active_config()
        return {
            "candidates": [
                {
                    "feature_id":    c.feature_id,
                    "status":        c.status,
                    "status_reason": c.status_reason,
                    "created_at":    c.created_at,
                }
                for c in candidates
            ],
            "active_config": active_config,
        }
    except Exception as exc:
        print(f"[RAE-001] get_active_adjustments_status failed: {exc}")
        return {"candidates": [], "active_config": {}}


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

    DTA-RSL-SCALE-FIX-001: c2_score is blended via its PERCENTILE RANK
    within the day's pool, not its raw value — c2_score's raw scale
    varies arbitrarily day to day (confirmed on real data: adjacent-rank
    gaps ranging from ~0.03 to >2.0), so a fixed 0.10-0.15 additive weight
    on the raw score was structurally almost never large enough to change
    which 5 symbols rank highest. Same percentile-rank technique already
    proven in final_trading_architecture_shadow_001.py's
    select_c2_top_n_v2 (Model C). Confirmed live: would_select_new was 0
    across all 23 shadow-tracked days under the old raw-score formula.
    """
    try:
        config = _load_active_config()
        active_entry = config.get(direction)
        weight = active_entry["weight"] if active_entry else DEFAULT_WEIGHT
        weight = max(0.0, min(weight, MAX_WEIGHT))

        from opportunity_engine.mover_discovery_v3 import _rank_pct

        scored = [r for r in recs if r.get("c2_score") is not None]
        c2_ranks = _rank_pct([float(r["c2_score"]) for r in scored]) if scored else []

        for r, c2_rank in zip(scored, c2_ranks):
            v3 = float(r.get("v3_score") or 0.0)
            adjusted = c2_rank + weight * v3
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
