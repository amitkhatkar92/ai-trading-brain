"""iios/investment/strategy/core/institutional_base_strategy.py
Abstract base class for every institutional IIOS strategy.

Implements the Template Method pattern with a 13-step standardised
execution pipeline. No trading logic lives here — only the contract.

Named InstitutionalBaseStrategy to avoid collision with the existing
lightweight BaseStrategy (core/base_strategy.py) used by the strategy
intelligence / evaluation subsystem.
"""
from __future__ import annotations

import abc
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .strategy_configuration import StrategyConfiguration
from .strategy_context import StrategyContext
from .strategy_descriptor import StrategyDescriptor
from .strategy_state import StrategyState, validate_transition


logger = logging.getLogger(__name__)


# ── Domain value objects ──────────────────────────────────────────────────────

class StrategyError(Exception):
    """Base exception for institutional strategy runtime errors."""


class SignalGenerationError(StrategyError):
    """Raised when signal generation fails fatally."""


class RiskValidationError(StrategyError):
    """Raised when risk validation rejects the plan entirely."""


class Signal:
    """Lightweight signal record produced by an institutional strategy."""

    __slots__ = (
        "signal_id", "strategy_id", "ticker", "direction",
        "confidence", "score", "metadata", "generated_at",
    )

    def __init__(
        self,
        strategy_id: str,
        ticker: str,
        direction: str,       # "long" | "short" | "neutral"
        confidence: float,    # 0.0–1.0
        score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.signal_id = f"sig-{uuid.uuid4().hex[:10]}"
        self.strategy_id = strategy_id
        self.ticker = ticker
        self.direction = direction
        self.confidence = max(0.0, min(1.0, confidence))
        self.score = score
        self.metadata = metadata or {}
        self.generated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "ticker": self.ticker,
            "direction": self.direction,
            "confidence": self.confidence,
            "score": self.score,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
        }


class Candidate:
    """A symbol under consideration before signal generation."""

    __slots__ = ("ticker", "scores", "notes", "rank")

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.scores: Dict[str, float] = {}
        self.notes: List[str] = []
        self.rank: int = 0

    def add_score(self, dimension: str, value: float) -> None:
        self.scores[dimension] = value

    def total_score(self) -> float:
        return sum(self.scores.values())


class ExecutionPlan:
    """Output of execution_plan() — consumed by the execution layer."""

    __slots__ = (
        "plan_id", "strategy_id", "signals",
        "position_sizes", "risk_notes", "created_at",
    )

    def __init__(self, strategy_id: str, signals: List[Signal]) -> None:
        self.plan_id = f"plan-{uuid.uuid4().hex[:10]}"
        self.strategy_id = strategy_id
        self.signals = signals
        self.position_sizes: Dict[str, float] = {}
        self.risk_notes: List[str] = []
        self.created_at = datetime.now(timezone.utc)

    def add_position_size(self, ticker: str, size: float) -> None:
        self.position_sizes[ticker] = size

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "strategy_id": self.strategy_id,
            "signal_count": len(self.signals),
            "signals": [s.to_dict() for s in self.signals],
            "position_sizes": self.position_sizes,
            "risk_notes": self.risk_notes,
            "created_at": self.created_at.isoformat(),
        }


# ── Abstract base ─────────────────────────────────────────────────────────────

class InstitutionalBaseStrategy(abc.ABC):
    """
    Abstract base class for all institutional IIOS strategies.

    Subclasses must implement all abstract methods. The framework orchestrates
    them via execute() in the guaranteed 13-step pipeline order:

        initialize → load_configuration → validate_inputs → prepare →
        analyze_market → generate_candidates → evaluate_candidates →
        generate_signals → validate_signals → position_sizing →
        risk_validation → execution_plan → post_execution → shutdown

    No strategy-specific trading logic may live in this class.
    """

    def __init__(self, descriptor: StrategyDescriptor) -> None:
        self._descriptor = descriptor
        self._config: Optional[StrategyConfiguration] = None
        self._state: StrategyState = StrategyState.REGISTERED
        self._lock = threading.RLock()
        self._logger = logging.getLogger(
            f"iios.strategy.{descriptor.strategy_id}"
        )
        self._execution_count: int = 0
        self._signal_count: int = 0
        self._last_executed: Optional[datetime] = None

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def strategy_id(self) -> str:
        return self._descriptor.strategy_id

    @property
    def descriptor(self) -> StrategyDescriptor:
        return self._descriptor

    @property
    def configuration(self) -> Optional[StrategyConfiguration]:
        return self._config

    @property
    def state(self) -> StrategyState:
        with self._lock:
            return self._state

    @property
    def execution_count(self) -> int:
        with self._lock:
            return self._execution_count

    @property
    def signal_count(self) -> int:
        with self._lock:
            return self._signal_count

    @property
    def last_executed(self) -> Optional[datetime]:
        with self._lock:
            return self._last_executed

    # ── State machine ─────────────────────────────────────────────────────────

    def _transition(self, target: StrategyState) -> None:
        with self._lock:
            if not validate_transition(self._state, target):
                raise StrategyError(
                    f"[{self.strategy_id}] Invalid transition: "
                    f"{self._state.value} → {target.value}"
                )
            self._state = target
            self._logger.debug("State → %s", target.value)

    # ── Abstract pipeline steps ───────────────────────────────────────────────

    @abc.abstractmethod
    def initialize(self) -> None:
        """One-time setup: connect data sources, warm caches, allocate resources."""

    @abc.abstractmethod
    def load_configuration(self, config: StrategyConfiguration) -> None:
        """Accept and internalise a configuration snapshot."""

    @abc.abstractmethod
    def validate_inputs(self, context: StrategyContext) -> bool:
        """
        Validate execution context before the evaluation cycle.
        Return False to skip this cycle gracefully (not an error).
        """

    @abc.abstractmethod
    def prepare(self, context: StrategyContext) -> None:
        """Fetch supplementary data, compute indicators needed for analysis."""

    @abc.abstractmethod
    def analyze_market(self, context: StrategyContext) -> Dict[str, Any]:
        """
        Analyse the market environment.
        Returns a free-form dict of analysis results (regime, breadth, etc.).
        """

    @abc.abstractmethod
    def generate_candidates(
        self, context: StrategyContext, analysis: Dict[str, Any]
    ) -> List[Candidate]:
        """
        Screen the symbol universe for candidates.
        No signals yet — only shortlisting. May return an empty list.
        """

    @abc.abstractmethod
    def evaluate_candidates(
        self,
        candidates: List[Candidate],
        context: StrategyContext,
        analysis: Dict[str, Any],
    ) -> List[Candidate]:
        """Score and rank each candidate. Return sorted list (best first)."""

    @abc.abstractmethod
    def generate_signals(
        self,
        candidates: List[Candidate],
        context: StrategyContext,
        analysis: Dict[str, Any],
    ) -> List[Signal]:
        """Convert evaluated candidates into raw Signal objects."""

    @abc.abstractmethod
    def validate_signals(
        self, signals: List[Signal], context: StrategyContext
    ) -> List[Signal]:
        """
        Apply signal-level validation (deduplication, cooldown, etc.).
        Return only validated signals.
        """

    @abc.abstractmethod
    def position_sizing(
        self, signals: List[Signal], context: StrategyContext
    ) -> Dict[str, float]:
        """
        Compute position sizes for each signal.
        Returns {ticker: fraction_of_capital}.
        """

    @abc.abstractmethod
    def risk_validation(
        self,
        signals: List[Signal],
        sizes: Dict[str, float],
        context: StrategyContext,
    ) -> List[Signal]:
        """
        Apply strategy-level risk rules.
        Raise RiskValidationError to abort the entire plan.
        Return only risk-approved signals.
        """

    @abc.abstractmethod
    def execution_plan(
        self,
        signals: List[Signal],
        sizes: Dict[str, float],
        context: StrategyContext,
    ) -> ExecutionPlan:
        """Build the final ExecutionPlan from approved signals and sizes."""

    @abc.abstractmethod
    def post_execution(
        self, plan: ExecutionPlan, context: StrategyContext
    ) -> None:
        """Called after the plan is handed off to the execution layer."""

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Release resources; called during graceful strategy unload."""

    # ── Template method (orchestrated pipeline) ───────────────────────────────

    def execute(self, context: StrategyContext) -> Optional[ExecutionPlan]:
        """
        Run the 13-step execution pipeline.
        Returns an ExecutionPlan, or None if the cycle is skipped.
        Transitions state: READY/PAUSED → RUNNING → READY (or FAILED).
        """
        # Atomic check-and-set: prevents TOCTOU races in concurrent calls.
        with self._lock:
            if self._state not in (StrategyState.READY, StrategyState.PAUSED):
                raise StrategyError(
                    f"[{self.strategy_id}] Cannot execute in state "
                    f"{self._state.value}."
                )
            if not validate_transition(self._state, StrategyState.RUNNING):
                raise StrategyError(
                    f"[{self.strategy_id}] Invalid transition: "
                    f"{self._state.value} → running"
                )
            self._state = StrategyState.RUNNING
            self._logger.debug("State → running")

        self._logger.info(
            "Execution cycle starting (session=%s)", context.session_id
        )

        pipeline_started = True  # we are now RUNNING
        try:
            if not self.validate_inputs(context):
                self._logger.info("Inputs invalid — skipping cycle.")
                self._transition(StrategyState.READY)
                return None

            self.prepare(context)
            analysis = self.analyze_market(context)
            candidates = self.generate_candidates(context, analysis)
            if not candidates:
                self._logger.info("No candidates — skipping cycle.")
                self._transition(StrategyState.READY)
                return None

            candidates = self.evaluate_candidates(candidates, context, analysis)
            signals = self.generate_signals(candidates, context, analysis)
            signals = self.validate_signals(signals, context)
            if not signals:
                self._logger.info("No signals survived validation.")
                self._transition(StrategyState.READY)
                return None

            sizes = self.position_sizing(signals, context)
            signals = self.risk_validation(signals, sizes, context)
            if not signals:
                self._logger.info("All signals rejected by risk.")
                self._transition(StrategyState.READY)
                return None

            plan = self.execution_plan(signals, sizes, context)
            self.post_execution(plan, context)

            with self._lock:
                self._execution_count += 1
                self._signal_count += len(signals)
                self._last_executed = datetime.now(timezone.utc)

            self._transition(StrategyState.READY)
            self._logger.info(
                "Cycle complete — %d signals → plan %s",
                len(signals), plan.plan_id,
            )
            return plan

        except RiskValidationError:
            self._logger.warning("Risk validation aborted the cycle.")
            self._transition(StrategyState.READY)
            return None

        except Exception as exc:
            self._logger.exception(
                "Unhandled error in execution pipeline: %s", exc
            )
            try:
                self._transition(StrategyState.FAILED)
            except StrategyError:
                pass
            raise

    # ── Lifecycle convenience ─────────────────────────────────────────────────

    def load(self, config: StrategyConfiguration) -> None:
        """Load configuration; transitions REGISTERED → LOADED."""
        self._transition(StrategyState.LOADED)
        self._config = config
        self.load_configuration(config)

    def init(self) -> None:
        """Initialise resources; transitions LOADED → INITIALIZED."""
        self._transition(StrategyState.INITIALIZED)
        self.initialize()

    def ready(self) -> None:
        """Mark strategy as ready; transitions INITIALIZED → READY."""
        self._transition(StrategyState.READY)

    def pause(self) -> None:
        """Pause; transitions RUNNING → PAUSED."""
        self._transition(StrategyState.PAUSED)

    def resume(self) -> None:
        """Resume; transitions PAUSED → RUNNING."""
        self._transition(StrategyState.RUNNING)

    def complete(self) -> None:
        """Mark completed; transitions READY/RUNNING/PAUSED → COMPLETED."""
        self._transition(StrategyState.COMPLETED)

    def fail(self, reason: str = "") -> None:
        """Mark failed."""
        self._logger.error("Strategy marked failed: %s", reason)
        try:
            self._transition(StrategyState.FAILED)
        except StrategyError:
            pass

    def archive(self) -> None:
        """Archive and shut down."""
        self._transition(StrategyState.ARCHIVED)
        self.shutdown()

    # ── Representation ─────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.strategy_id!r} "
            f"state={self._state.value!r}>"
        )

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "strategy_id": self.strategy_id,
                "class": self.__class__.__name__,
                "state": self._state.value,
                "execution_count": self._execution_count,
                "signal_count": self._signal_count,
                "last_executed": (
                    self._last_executed.isoformat()
                    if self._last_executed else None
                ),
                "descriptor": self._descriptor.to_dict(),
            }
