"""
autonomous_research/hypothesis_lifecycle_bridge.py
=====================================================
DTA-ARS-HYPOTHESIS-LIFECYCLE-001 -- automated PROPOSED->CONFIRMED/REJECTED
lifecycle for scientific_director/SFR_AUTO origin hypotheses, mirroring
the fully-automated KSL_AUTO path (RAE-001's sync_hypothesis_confirmation()).

Root cause this closes (found 2026-10-27): these hypotheses had NO
automated advancement mechanism at all -- not even past PROPOSED.
Tracing why revealed 2 real, pre-existing, never-triggered bugs (both
already fixed, separately, in study_planner.py / research_coordinator.py):
  1. StudyPlanner never linked a gap-derived StudyPlan back to its single
     related hypothesis (source_hypothesis_id was always None on the real
     live path), so ResearchCoordinator's own hypothesis-specific
     validation/evidence-integration stages always skipped.
  2. ResearchCoordinator's evidence-integration stage constructed an
     EvidenceReference with field names/enum member that don't exist on
     the real model -- dead code on every real (non-dry-run) invocation.

This module is the final piece: reuses EvidenceValidator.validate_hypothesis()
(an existing, already-built, 10-gate quality-score engine) as the sole
verdict source -- invents zero new statistics.

Cold-start safeguard (the reason this wasn't a 10-line bridge): a brand
new hypothesis's FIRST validation always returns FAILED purely because
zero evidence exists yet (reproduced directly) -- ValidationOutcome has
no distinct "insufficient data" state. A FAILED outcome is therefore
only treated as a genuine REJECTED verdict once at least
MIN_SAMPLE_FOR_REJECTION real evidence items have accumulated; below
that it is correctly "keep waiting", same philosophy as every other
near-zero-evidence module in this ecosystem.

VALIDATED -> CONFIRMED requires an independent reconfirmation: a second
validate_hypothesis() call, run only after both (a) >= MIN_RECONFIRMATION_
DAYS have elapsed since the first VALIDATED verdict, and (b) genuinely
NEW evidence has been attached since then (evidence_count grew) --
mirrors the same "reconfirm on new, held-out evidence" pattern already
used by RAE-001/KDE-IDR/HKAP-IDR bridges elsewhere in this repo.

KSL_AUTO-origin hypotheses are explicitly excluded -- already covered by
a separate, independent mechanism (RAE-001's own shadow-then-live
candidate lifecycle via sync_hypothesis_confirmation()).

Safety: read/write-scoped entirely to the ARS hypothesis registry and
its own tiny JSON state file. Never touches execution_engine/order_manager/
risk_control/dhan_feed/broker. Never raises.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from utils import get_logger

log = get_logger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATE_PATH  = os.path.join(_ROOT, "data", "ars", "hypothesis_lifecycle_state.json")

_EXCLUDED_ORIGINS = {"KSL_AUTO"}

# Same floor as DTA-REALISTIC-THRESHOLDS-001's "normal" sample-size convention --
# below this, a FAILED validation outcome means "insufficient evidence", not a
# genuine rejection.
MIN_SAMPLE_FOR_REJECTION = 10

# Cooldown before a VALIDATED hypothesis is eligible for reconfirmation --
# mirrors the bounded-wait pattern used throughout this repo's other bridges.
MIN_RECONFIRMATION_DAYS = 14

_ACTOR = "ARS-LIFECYCLE-BRIDGE"


def sync_hypothesis_lifecycle() -> Dict[str, Any]:
    """
    Fully automated entry point. Never raises.

    Returns a summary dict: checked / advanced_to_running / validated /
    rejected / confirmed / reconfirm_rejected / errors.
    """
    try:
        return _sync_impl()
    except Exception as exc:
        log.debug("[ARSLifecycleBridge] sync_hypothesis_lifecycle failed: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _sync_impl() -> Dict[str, Any]:
    from .knowledge_provider import KnowledgeProvider
    from .hypothesis_registry import HypothesisRegistry
    from .hypothesis_models import HypothesisStatus
    from .evidence_validator import EvidenceValidator
    from .evidence_validator_models import ValidationOutcome

    summary = {
        "checked": 0, "advanced_to_running": 0, "validated": 0,
        "rejected": 0, "confirmed": 0, "reconfirm_rejected": 0, "errors": 0,
    }

    kp  = KnowledgeProvider()
    reg = HypothesisRegistry(knowledge_provider=kp)
    ev  = EvidenceValidator(knowledge_provider=kp, hypothesis_registry=reg)
    state = _load_state()

    open_hyps = [h for h in reg.list_open() if h.origin not in _EXCLUDED_ORIGINS]

    for h in open_hyps:
        summary["checked"] += 1
        hyp_id = h.hypothesis_id
        evidence_count = len(h.supporting_evidence)

        try:
            if h.status == HypothesisStatus.PROPOSED:
                if evidence_count < 1:
                    continue  # no completed research yet -- nothing to advance
                # A completed RC run attaching real evidence implies this
                # hypothesis was already approved/planned/run in practice --
                # walk the pipeline-progress chain in one pass (each step is
                # a valid VALID_TRANSITIONS hop, not a judgement call).
                reg.update_status(hyp_id, HypothesisStatus.UNDER_REVIEW, actor=_ACTOR,
                                   reason="Real evidence attached by a completed ResearchCoordinator run.")
                reg.update_status(hyp_id, HypothesisStatus.APPROVED, actor=_ACTOR,
                                   reason="Study plan execution confirms this was approved.")
                reg.update_status(hyp_id, HypothesisStatus.PLANNED, actor=_ACTOR,
                                   reason="Study plan execution confirms this was planned.")
                reg.update_status(hyp_id, HypothesisStatus.RUNNING, actor=_ACTOR,
                                   reason="Study plan execution confirms research ran.")
                summary["advanced_to_running"] += 1
                h = reg.get(hyp_id)

            if h.status == HypothesisStatus.RUNNING:
                result = ev.validate_hypothesis(hyp_id)
                outcome = result.outcome
                if outcome in (ValidationOutcome.PASSED, ValidationOutcome.PASSED_WITH_OBSERVATIONS):
                    reg.update_status(hyp_id, HypothesisStatus.VALIDATED, actor=_ACTOR,
                                       reason=f"EvidenceValidator outcome={outcome.value} "
                                              f"(score={result.quality_score.total:.2f}).")
                    state[hyp_id] = {
                        "validated_at": _now_iso(),
                        "evidence_count_at_validation": evidence_count,
                    }
                    summary["validated"] += 1
                elif outcome == ValidationOutcome.FAILED:
                    if evidence_count >= MIN_SAMPLE_FOR_REJECTION:
                        reg.update_status(hyp_id, HypothesisStatus.REJECTED, actor=_ACTOR,
                                           reason=f"EvidenceValidator outcome=FAILED with "
                                                  f"{evidence_count} evidence items "
                                                  f"(>= floor of {MIN_SAMPLE_FOR_REJECTION}).")
                        summary["rejected"] += 1
                    # else: insufficient evidence to conclude yet -- stays RUNNING,
                    # re-evaluated on a future cycle as more evidence accumulates.

            elif h.status == HypothesisStatus.VALIDATED:
                st = state.get(hyp_id)
                if st is None:
                    # Predates this bridge (e.g. created before today, or by the
                    # one-off H-CRITICAL-001 script) -- seed state, don't act on
                    # the very first observation.
                    state[hyp_id] = {
                        "validated_at": _now_iso(),
                        "evidence_count_at_validation": evidence_count,
                    }
                    continue

                validated_at = _parse_dt(st.get("validated_at"))
                days_since = (datetime.now(timezone.utc) - validated_at).days if validated_at else 0
                has_new_evidence = evidence_count > st.get("evidence_count_at_validation", 0)

                if days_since >= MIN_RECONFIRMATION_DAYS and has_new_evidence:
                    result = ev.validate_hypothesis(hyp_id)
                    if result.outcome in (ValidationOutcome.PASSED, ValidationOutcome.PASSED_WITH_OBSERVATIONS):
                        reg.update_status(hyp_id, HypothesisStatus.CONFIRMED, actor=_ACTOR,
                                           reason=f"Independently reconfirmed on new evidence "
                                                  f"({evidence_count} items, {days_since}d later): "
                                                  f"outcome={result.outcome.value}.")
                        summary["confirmed"] += 1
                        state.pop(hyp_id, None)
                    else:
                        reg.update_status(hyp_id, HypothesisStatus.REJECTED, actor=_ACTOR,
                                           reason=f"Reconfirmation on new evidence contradicted the "
                                                  f"original finding: outcome={result.outcome.value}.")
                        summary["reconfirm_rejected"] += 1
                        state.pop(hyp_id, None)
                # else: not yet due for reconfirmation -- leave VALIDATED, no action.
        except Exception as exc:
            summary["errors"] += 1
            log.debug("[ARSLifecycleBridge] update failed for %s (non-fatal): %s", hyp_id, exc)

    _save_state(state)
    return summary


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(s: Any):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _load_state() -> Dict[str, Any]:
    try:
        if os.path.exists(_STATE_PATH):
            with open(_STATE_PATH, "r") as f:
                return json.load(f)
    except Exception as exc:
        log.debug("[ARSLifecycleBridge] state load failed (starting fresh): %s", exc)
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        tmp_path = _STATE_PATH + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, _STATE_PATH)
    except Exception as exc:
        log.debug("[ARSLifecycleBridge] state save failed (non-fatal): %s", exc)
