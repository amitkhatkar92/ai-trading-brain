"""
iios/decisions/workflow/decision_factory.py
============================================
DecisionFactory — builds Decision objects from evaluated candidates.
"""
from __future__ import annotations

import uuid
from typing import Any

from ..decision_constants import (
    DecisionStatus,
    DecisionType,
    DECISION_AUTO_SELECTOR_ID,
)
from ..models.decision import Decision
from ..models.decision_candidate import DecisionCandidate
from ..models.decision_metadata import DecisionMetadata
from ..models.decision_request import DecisionRequest


class DecisionFactory:
    """
    Constructs fully-populated Decision objects.
    Stateless — all context comes from method arguments.
    """

    def build(
        self,
        request:            DecisionRequest,
        ranked_candidates:  list[DecisionCandidate],
        selected:           DecisionCandidate | None,
        metadata:           DecisionMetadata | None = None,
        warnings:           list[str] | None = None,
        errors:             list[str] | None = None,
    ) -> Decision:
        """
        Construct a Decision from the workflow output.

        Parameters
        ----------
        request           : The originating DecisionRequest.
        ranked_candidates : All evaluated candidates in rank order.
        selected          : The winning candidate (or None for failed decisions).
        metadata          : Provenance metadata (auto-built if None).
        warnings          : Non-blocking warnings from the workflow.
        errors            : Blocking errors (if any).
        """
        meta = metadata or self._build_metadata(request)

        alternatives = [c for c in ranked_candidates if not c.selected]

        # Policy summary
        policy_summary = self._summarise_policies(ranked_candidates)

        decision = Decision(
            request_id            = request.request_id,
            decision_type         = (
                selected.option.option_type if selected else
                request.decision_type or DecisionType.GENERIC
            ),
            status                = DecisionStatus.COMPLETED if selected else DecisionStatus.FAILED,
            priority              = request.priority,
            selected_candidate_id = selected.candidate_id if selected else "",
            confidence            = selected.option.confidence if selected else 0.0,
            risk_score            = selected.option.risk_score if selected else 1.0,
            rationale             = self._build_rationale(selected, ranked_candidates),
            candidates            = list(ranked_candidates),
            policy_summary        = policy_summary,
            alternatives          = alternatives[:5],   # top-5 alternatives
            warnings              = list(warnings or []),
            errors                = list(errors or []),
            metadata              = meta,
        )

        if selected:
            decision.complete()
        else:
            decision.fail("No candidate passed all mandatory policies")

        return decision

    # -- Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_metadata(request: DecisionRequest) -> DecisionMetadata:
        intel_ids = [
            p.get("id") or p.get("product_id", "")
            for p in request.intelligence_payload
            if isinstance(p, dict)
        ]
        return DecisionMetadata(
            source_id        = request.source_id,
            intelligence_ids = intel_ids,
            constraints      = dict(request.constraints),
        )

    @staticmethod
    def _build_rationale(
        selected:   DecisionCandidate | None,
        all_cands:  list[DecisionCandidate],
    ) -> str:
        if selected is None:
            return "No candidate met all mandatory policy requirements."
        others = len([c for c in all_cands if not c.selected])
        return (
            f"Selected {selected.option.name!r} "
            f"(type={selected.option.option_type.value}, "
            f"confidence={selected.option.confidence:.3f}, "
            f"score={selected.composite_score:.3f}) "
            f"from {len(all_cands)} candidate(s); "
            f"{others} alternative(s) considered."
        )

    @staticmethod
    def _summarise_policies(candidates: list[DecisionCandidate]) -> dict[str, Any]:
        if not candidates:
            return {}
        all_results = [pr for c in candidates for pr in c.policy_results]
        by_policy: dict[str, list[str]] = {}
        for pr in all_results:
            by_policy.setdefault(pr.policy_name, []).append(pr.outcome.value)
        return {
            name: {
                "pass":    outcomes.count("pass"),
                "fail":    outcomes.count("fail"),
                "abstain": outcomes.count("abstain"),
            }
            for name, outcomes in by_policy.items()
        }
