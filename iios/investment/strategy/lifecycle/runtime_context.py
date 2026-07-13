"""iios/investment/strategy/lifecycle/runtime_context.py
Per-cycle runtime context injected into the execution engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class RuntimeContext:
    """
    Immutable execution context for a single runtime cycle.

    Created at the start of each scheduling round and threaded through
    the full execution pipeline.  All optional intelligence references
    are injected by the orchestrator — strategies remain independently
    testable when None.
    """

    cycle_id: str = field(
        default_factory=lambda: f"cyc-{uuid.uuid4().hex[:10]}"
    )
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    deadline: Optional[datetime] = None

    # Upstream intelligence snapshots (injected by orchestrator)
    market_intelligence: Optional[Any] = None
    company_intelligence: Optional[Any] = None

    # Execution mode flags
    is_live: bool = False
    is_paper: bool = True
    is_backtest: bool = False

    # Arbitrary extension metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """True if the cycle deadline has passed."""
        if self.deadline is None:
            return False
        return datetime.now(timezone.utc) > self.deadline

    def elapsed_ms(self) -> float:
        """Milliseconds elapsed since this cycle started."""
        delta = datetime.now(timezone.utc) - self.started_at
        return delta.total_seconds() * 1_000

    def get_meta(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)
