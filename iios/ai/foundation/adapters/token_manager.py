"""
token_manager.py — iios.ai.foundation.adapters
===============================================
:class:`TokenManager` — context window budget management.

Provides token counting, budget enforcement, and truncation strategies
for all AI Platform modules.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .constants import DEFAULT_TOKEN_BUDGET, DEFAULT_MAX_OUTPUT_TOKENS, SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Budget snapshot (immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TokenBudgetSnapshot:
    """
    Point-in-time record of a token budget allocation.

    Fields
    ------
    budget_id :      Identifier for this budget context.
    total_budget :   Maximum tokens allowed (context window).
    max_output :     Maximum output tokens reserved.
    prompt_used :    Tokens consumed by the prompt so far.
    available :      Remaining tokens for additional context.
    utilisation :    Prompt utilisation ratio (0.0–1.0).
    is_exceeded :    ``True`` iff the budget is over-allocated.
    """
    budget_id:    str
    total_budget: int
    max_output:   int
    prompt_used:  int
    available:    int
    utilisation:  float
    is_exceeded:  bool
    schema:       str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget_id":    self.budget_id,
            "total_budget": self.total_budget,
            "max_output":   self.max_output,
            "prompt_used":  self.prompt_used,
            "available":    self.available,
            "utilisation":  round(self.utilisation, 4),
            "is_exceeded":  self.is_exceeded,
        }


# ---------------------------------------------------------------------------
# Token manager
# ---------------------------------------------------------------------------

class TokenManager:
    """
    Thread-safe token budget manager for one AI operation context.

    Responsibilities
    ----------------
    * Track accumulated prompt token usage.
    * Enforce the hard context-window budget.
    * Provide truncation utilities for budget-aware context assembly.
    * Emit a structured :class:`TokenBudgetSnapshot` for observability.

    Usage example::

        mgr = TokenManager(budget=8_192, max_output=2_048)
        mgr.add("system", token_count=120)
        mgr.add("user_query", token_count=80)
        mgr.add("retrieved_context", token_count=3_000)

        snap = mgr.snapshot("req-001")
        if snap.is_exceeded:
            # apply truncation
            ...

        remaining = mgr.available()
    """

    def __init__(
        self,
        budget:     int = DEFAULT_TOKEN_BUDGET,
        max_output: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> None:
        if budget <= 0:
            raise ValueError(f"Token budget must be positive; got {budget}.")
        if max_output <= 0:
            raise ValueError(f"max_output must be positive; got {max_output}.")
        if max_output >= budget:
            raise ValueError(
                f"max_output ({max_output}) must be less than total budget ({budget})."
            )
        self._budget:     int                            = budget
        self._max_output: int                            = max_output
        self._lock:       threading.Lock                 = threading.Lock()
        self._allocations: List[Tuple[str, int]]         = []  # (label, tokens)
        self._total_used:  int                           = 0

    # ── Budget accounting ─────────────────────────────────────────────────────

    def add(self, label: str, token_count: int) -> None:
        """
        Record an allocation of ``token_count`` prompt tokens labelled ``label``.

        Does NOT raise on over-budget — call :meth:`check` to validate.
        """
        if token_count < 0:
            raise ValueError(f"token_count must be non-negative; got {token_count}.")
        with self._lock:
            self._allocations.append((label, token_count))
            self._total_used += token_count

    def remove(self, label: str) -> None:
        """Remove the first allocation matching ``label`` (LIFO-safe)."""
        with self._lock:
            for i, (lbl, cnt) in enumerate(self._allocations):
                if lbl == label:
                    self._allocations.pop(i)
                    self._total_used -= cnt
                    return

    def reset(self) -> None:
        """Clear all allocations."""
        with self._lock:
            self._allocations.clear()
            self._total_used = 0

    # ── Budget queries ────────────────────────────────────────────────────────

    @property
    def total_budget(self) -> int:
        return self._budget

    @property
    def max_output(self) -> int:
        return self._max_output

    def prompt_budget(self) -> int:
        """Maximum tokens available for the prompt (budget minus max_output)."""
        return self._budget - self._max_output

    def used(self) -> int:
        """Tokens consumed by all registered allocations."""
        with self._lock:
            return self._total_used

    def available(self) -> int:
        """Remaining prompt tokens (may be negative if over-budget)."""
        return self.prompt_budget() - self.used()

    def is_exceeded(self) -> bool:
        """Return ``True`` iff the prompt budget is over-allocated."""
        return self.available() < 0

    def utilisation(self) -> float:
        """Ratio of prompt tokens used to prompt budget (0.0–1.0+)."""
        pb = self.prompt_budget()
        if pb <= 0:
            return 1.0
        return min(self.used() / pb, 1.0)

    def snapshot(self, budget_id: str = "") -> TokenBudgetSnapshot:
        """Return an immutable snapshot of the current budget state."""
        used = self.used()
        avail = self.prompt_budget() - used
        return TokenBudgetSnapshot(
            budget_id    = budget_id,
            total_budget = self._budget,
            max_output   = self._max_output,
            prompt_used  = used,
            available    = max(avail, 0),
            utilisation  = self.utilisation(),
            is_exceeded  = avail < 0,
        )

    # ── Truncation utilities ──────────────────────────────────────────────────

    def truncate_to_fit(
        self,
        text:          str,
        token_counter: Any,      # callable: (str) → int
        reserve:       int = 0,
    ) -> str:
        """
        Truncate ``text`` to fit within the available prompt budget.

        Parameters
        ----------
        text :          Text to truncate.
        token_counter : A callable ``(str) -> int`` that counts tokens.
        reserve :       Additional tokens to reserve (e.g. for separators).

        Returns
        -------
        str
            Text that fits within the available budget.
        """
        available_tokens = max(0, self.available() - reserve)
        if available_tokens <= 0:
            return ""

        token_count = token_counter(text)
        if token_count <= available_tokens:
            return text

        # Binary-search for the largest prefix that fits
        lo, hi = 0, len(text)
        while lo < hi:
            mid    = (lo + hi + 1) // 2
            prefix = text[:mid]
            if token_counter(prefix) <= available_tokens:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo]

    def __repr__(self) -> str:
        return (
            f"<TokenManager budget={self._budget} "
            f"used={self.used()} available={self.available()}>"
        )
