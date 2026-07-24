"""
knowledge_dispatcher.py — iios.knowledge.engine
-------------------------------------------------
Knowledge workflow dispatcher.

Delegates to:
  - M3: Knowledge Governance Policy Framework (when available)
  - M4: Knowledge Intelligence Framework (when available)

Both delegates are optional and injectable.  When not provided, the
dispatcher returns benign no-op results, maintaining the same interface.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DISPATCHER_SYSTEM_ID, KnowledgeWorkflowType

_log = get_logger(DISPATCHER_SYSTEM_ID)

# Type aliases for injectable downstream framework delegates
GovernanceDelegate   = Callable[[str, Dict[str, Any]], Dict[str, Any]]
IntelligenceDelegate = Callable[[str, Dict[str, Any]], Dict[str, Any]]


class KnowledgeDispatcher:
    """
    Routes knowledge workflows to downstream frameworks.

    The dispatcher performs NO reasoning, semantic search, embedding
    generation, or vector indexing.

    Parameters
    ----------
    governance_delegate :   Callable that invokes M3 Knowledge Governance.
                            Signature: (knowledge_id, context) -> result_dict
    intelligence_delegate : Callable that invokes M4 Knowledge Intelligence.
                            Signature: (knowledge_id, context) -> result_dict
    """

    def __init__(
        self,
        governance_delegate:   Optional[GovernanceDelegate]   = None,
        intelligence_delegate: Optional[IntelligenceDelegate] = None,
    ) -> None:
        self._governance_delegate   = governance_delegate
        self._intelligence_delegate = intelligence_delegate

    # ------------------------------------------------------------------
    # Dispatch entry point
    # ------------------------------------------------------------------

    def dispatch(
        self,
        knowledge_id:  str,
        subsystem_id:  str,
        workflow_type: KnowledgeWorkflowType,
        artifacts:     Dict[str, Any],
        context:       Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Dispatch a knowledge workflow to M3 and M4 frameworks.

        Returns a dict with keys ``governance_result`` and
        ``intelligence_result``.  Neither may raise — failures are
        captured in the result.
        """
        gov_result   = self._invoke_governance(knowledge_id, context, artifacts)
        intel_result = self._invoke_intelligence(knowledge_id, context, artifacts)

        return {
            "governance_result":   gov_result,
            "intelligence_result": intel_result,
            "dispatched_at":       time.time(),
        }

    def _invoke_governance(
        self,
        knowledge_id: str,
        context:      Dict[str, Any],
        artifacts:    Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke M3 Knowledge Governance Policy Framework."""
        if self._governance_delegate is None:
            return {"status": "not_configured", "knowledge_id": knowledge_id}
        try:
            return self._governance_delegate(knowledge_id, {**context, "artifacts": artifacts})
        except Exception as exc:  # noqa: BLE001
            _log.warning(f"Governance delegate error: knowledge_id={knowledge_id!r} error={exc!r}")
            return {"status": "error", "error": str(exc), "knowledge_id": knowledge_id}

    def _invoke_intelligence(
        self,
        knowledge_id: str,
        context:      Dict[str, Any],
        artifacts:    Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke M4 Knowledge Intelligence Framework."""
        if self._intelligence_delegate is None:
            return {"status": "not_configured", "knowledge_id": knowledge_id}
        try:
            return self._intelligence_delegate(knowledge_id, {**context, "artifacts": artifacts})
        except Exception as exc:  # noqa: BLE001
            _log.warning(f"Intelligence delegate error: knowledge_id={knowledge_id!r} error={exc!r}")
            return {"status": "error", "error": str(exc), "knowledge_id": knowledge_id}

    # ------------------------------------------------------------------
    # Delegate management
    # ------------------------------------------------------------------

    def set_governance_delegate(self, delegate: GovernanceDelegate) -> None:
        self._governance_delegate = delegate

    def set_intelligence_delegate(self, delegate: IntelligenceDelegate) -> None:
        self._intelligence_delegate = delegate

    def has_governance(self) -> bool:
        return self._governance_delegate is not None

    def has_intelligence(self) -> bool:
        return self._intelligence_delegate is not None
