"""
iios/decisions/policies/decision_policy.py
==========================================
Abstract DecisionPolicy and built-in concrete implementations.

All investment-specific policies are out of scope here.
Future modules add policies by subclassing DecisionPolicy —
the framework requires NO modification.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..decision_constants import MIN_CONFIDENCE_THRESHOLD, PolicyOutcome
from ..models.decision_candidate import DecisionCandidate
from ..models.decision_request import DecisionRequest


class DecisionPolicy(ABC):
    """
    Abstract base for Decision Engine policies.

    Each concrete policy implements ``apply()`` and exposes a ``name``.
    Policies are stateless and side-effect free.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def mandatory(self) -> bool:
        """If True, a FAIL causes the candidate to be disqualified."""
        return True

    @abstractmethod
    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        """
        Returns
        -------
        (outcome, reason)
        """
        ...


# ── Built-in generic policies ─────────────────────────────────────────────────

class MinConfidencePolicy(DecisionPolicy):
    """Fails any candidate whose option confidence is below the threshold."""

    def __init__(self, threshold: float = MIN_CONFIDENCE_THRESHOLD) -> None:
        self._threshold = threshold

    @property
    def name(self) -> str:
        return f"min_confidence:{self._threshold:.2f}"

    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        conf   = candidate.option.confidence
        passed = conf >= self._threshold
        reason = (
            f"confidence {conf:.3f} {'≥' if passed else '<'} threshold {self._threshold:.2f}"
        )
        return (PolicyOutcome.PASS if passed else PolicyOutcome.FAIL), reason


class MaxRiskPolicy(DecisionPolicy):
    """Fails any candidate whose option risk_score exceeds the maximum."""

    def __init__(self, max_risk: float = 0.9) -> None:
        self._max_risk = max_risk

    @property
    def name(self) -> str:
        return f"max_risk:{self._max_risk:.2f}"

    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        risk   = candidate.option.risk_score
        passed = risk <= self._max_risk
        reason = f"risk {risk:.3f} {'≤' if passed else '>'} max {self._max_risk:.2f}"
        return (PolicyOutcome.PASS if passed else PolicyOutcome.FAIL), reason


class RequireEvidencePolicy(DecisionPolicy):
    """Fails any candidate whose option carries no evidence."""

    @property
    def name(self) -> str:
        return "require_evidence"

    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        has_evidence = len(candidate.option.evidence) > 0
        reason       = "evidence present" if has_evidence else "no evidence supplied"
        return (PolicyOutcome.PASS if has_evidence else PolicyOutcome.FAIL), reason


class MinCandidatesPolicy(DecisionPolicy):
    """
    Abstains per-candidate (applied at request level instead).
    Returns PASS so candidates are never blocked by this policy;
    the workflow checks candidate count separately.
    """

    def __init__(self, minimum: int = 1) -> None:
        self._minimum = minimum

    @property
    def name(self) -> str:
        return f"min_candidates:{self._minimum}"

    @property
    def mandatory(self) -> bool:
        return False  # informational only

    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        # Per-candidate policy is not meaningful here — always abstain
        return PolicyOutcome.ABSTAIN, "per-candidate abstain (count checked at workflow level)"


class NotExpiredRequestPolicy(DecisionPolicy):
    """Fails any candidate from an expired request."""

    @property
    def name(self) -> str:
        return "not_expired_request"

    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        expired = request.is_expired()
        reason  = "request is expired" if expired else "request is within TTL"
        return (PolicyOutcome.FAIL if expired else PolicyOutcome.PASS), reason


class AllowlistTypePolicy(DecisionPolicy):
    """Only allows candidates whose option_type is in the allowlist."""

    def __init__(self, allowed_types: list[str]) -> None:
        self._allowed: frozenset[str] = frozenset(allowed_types)

    @property
    def name(self) -> str:
        return f"type_allowlist:[{','.join(sorted(self._allowed))}]"

    def apply(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> tuple[PolicyOutcome, str]:
        t      = candidate.option.option_type.value
        passed = t in self._allowed
        reason = f"type {t!r} {'in' if passed else 'not in'} allowlist"
        return (PolicyOutcome.PASS if passed else PolicyOutcome.FAIL), reason
