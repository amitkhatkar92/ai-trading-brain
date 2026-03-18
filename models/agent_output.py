"""
Agent Output Models
Standardised output structures for every AI agent in the system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AgentOutput:
    """
    Universal return type for every agent's .analyse() / .run() call.
    Keeps inter-agent communication consistent.
    """
    agent_name: str
    status: str                            # "ok" | "warning" | "error" | "skipped"
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0               # 0–10
    timestamp: datetime = field(default_factory=datetime.now)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        return self.status == "ok"

    def __str__(self) -> str:
        return (
            f"[{self.agent_name}] status={self.status} "
            f"confidence={self.confidence:.1f} | {self.summary}"
        )


@dataclass
class DebateVote:
    """A single agent's vote in the Multi-Agent Debate System (Layer 6)."""
    agent_name: str
    vote: str                              # "approve" | "reject" | "reduce_size" | "hedge"
    score: float                           # 0–10 conviction
    reasoning: str
    suggested_position_modifier: float = 1.0   # 1.0 = full size, 0.5 = half size, 0 = skip


@dataclass
class DecisionResult:
    """
    Final output produced by Decision AI (Layer 7).
    Consumed directly by the Execution Engine.
    """
    approved: bool
    confidence_score: float                # Weighted average of all agent scores
    votes: List[DebateVote] = field(default_factory=list)
    position_size_modifier: float = 1.0   # Scaling factor for position size
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        decision = "APPROVED" if self.approved else "REJECTED"
        return (
            f"[Decision] {decision} | Score: {self.confidence_score:.1f}/10 | "
            f"Size modifier: {self.position_size_modifier:.0%} | {self.reasoning}"
        )
