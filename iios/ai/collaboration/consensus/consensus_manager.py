"""
consensus_manager.py -- iios.ai.collaboration.consensus
=========================================================
:class:`ConsensusManager` — runs consensus strategies against debate positions.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..debate.debate_position import DebatePosition
from ..exceptions.collaboration_exceptions import (
    AIConsensusFailedError,
)
from .consensus_result   import ConsensusResult
from .consensus_strategy import (
    ConfidenceThresholdStrategy,
    ConsensusStrategy,
    MajorityVoteStrategy,
    UnanimousStrategy,
    WeightedVoteStrategy,
)

_BUILT_IN: Dict[str, ConsensusStrategy] = {
    "majority":   MajorityVoteStrategy(),
    "weighted":   WeightedVoteStrategy(),
    "unanimous":  UnanimousStrategy(),
    "confidence": ConfidenceThresholdStrategy(),
}


class ConsensusManager:
    """
    Runs registered :class:`ConsensusStrategy` objects against a list of
    :class:`DebatePosition` objects and returns a :class:`ConsensusResult`.

    Built-in strategy names: ``"majority"``, ``"weighted"``, ``"unanimous"``,
    ``"confidence"``.
    Custom strategies may be registered at runtime.
    """

    def __init__(self) -> None:
        self._strategies: Dict[str, ConsensusStrategy] = dict(_BUILT_IN)

    def register_strategy(self, strategy: ConsensusStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def list_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    def calculate(
        self,
        session_id:    str,
        positions:     List[DebatePosition],
        strategy_name: str               = "majority",
        weights:       Optional[Dict[str, float]] = None,
    ) -> ConsensusResult:
        """
        Run *strategy_name* against *positions*.

        Raises :class:`AIConsensusFailedError` if the strategy name is unknown.
        """
        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            raise AIConsensusFailedError(
                f"Unknown consensus strategy '{strategy_name}'. "
                f"Available: {sorted(self._strategies)}."
            )
        return strategy.calculate(
            session_id = session_id,
            positions  = positions,
            weights    = weights or {},
        )
