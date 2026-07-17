"""iios/execution/risk/lifecycle/execution_risk_factory.py
==================================================
RiskFactory — creates ExecutionRisk instances with validated identifiers
and sensible defaults.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import uuid
from typing import Optional

from .constants import ACTOR_FACTORY, FACTORY_SYSTEM_ID, RiskCategory, VERSION
from .exceptions import RiskValidationError
from .execution_risk import ExecutionRisk
from .execution_risk_event import RiskEvent, make_risk_created
from .execution_risk_validation import RiskValidator


class RiskFactory:
    """
    Stateless factory for ``ExecutionRisk`` objects.

    Validates inputs before construction.  Never stores state itself.
    """

    def __init__(self) -> None:
        self._validator = RiskValidator()

    # ── Primary constructor ───────────────────────────────────────────────────

    def create(
        self,
        risk_category:  RiskCategory,
        *,
        risk_id:        Optional[str]   = None,
        execution_id:   str             = "",
        workflow_id:    str             = "",
        order_id:       str             = "",
        position_id:    str             = "",
        portfolio_id:   str             = "",
        strategy_id:    str             = "",
        decision_id:    str             = "",
        correlation_id: str             = "",
        expiry_time:    Optional[float] = None,
        max_history:    int             = 500,
    ) -> ExecutionRisk:
        """
        Create and return a new ``ExecutionRisk`` in the ``CREATED`` state.

        Parameters
        ----------
        risk_category:  The category of risk being evaluated.
        risk_id:        Optional override; a UUID4 is generated if omitted.
        expiry_time:    Unix timestamp when this evaluation expires.
        """
        if risk_category is None:
            raise RiskValidationError("risk_category must be provided")

        rid = risk_id or str(uuid.uuid4())

        return ExecutionRisk(
            risk_id=rid,
            execution_id=execution_id,
            workflow_id=workflow_id,
            order_id=order_id,
            position_id=position_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            decision_id=decision_id,
            risk_category=risk_category,
            correlation_id=correlation_id,
            expiry_time=expiry_time,
            max_history=max_history,
        )

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def create_exposure_risk(self, **kwargs) -> ExecutionRisk:
        """Create an EXPOSURE category risk evaluation."""
        return self.create(RiskCategory.EXPOSURE, **kwargs)

    def create_margin_risk(self, **kwargs) -> ExecutionRisk:
        """Create a MARGIN category risk evaluation."""
        return self.create(RiskCategory.MARGIN, **kwargs)

    def create_liquidity_risk(self, **kwargs) -> ExecutionRisk:
        """Create a LIQUIDITY category risk evaluation."""
        return self.create(RiskCategory.LIQUIDITY, **kwargs)

    def create_compliance_risk(self, **kwargs) -> ExecutionRisk:
        """Create a COMPLIANCE category risk evaluation."""
        return self.create(RiskCategory.COMPLIANCE, **kwargs)

    def create_order_size_risk(self, **kwargs) -> ExecutionRisk:
        """Create an ORDER_SIZE category risk evaluation."""
        return self.create(RiskCategory.ORDER_SIZE, **kwargs)

    def create_concentration_risk(self, **kwargs) -> ExecutionRisk:
        """Create a CONCENTRATION category risk evaluation."""
        return self.create(RiskCategory.CONCENTRATION, **kwargs)

    def create_price_risk(self, **kwargs) -> ExecutionRisk:
        """Create a PRICE category risk evaluation."""
        return self.create(RiskCategory.PRICE, **kwargs)

    def create_execution_risk(self, **kwargs) -> ExecutionRisk:
        """Create an EXECUTION category risk evaluation."""
        return self.create(RiskCategory.EXECUTION, **kwargs)

    def create_operational_risk(self, **kwargs) -> ExecutionRisk:
        """Create an OPERATIONAL category risk evaluation."""
        return self.create(RiskCategory.OPERATIONAL, **kwargs)

    # ── Event ─────────────────────────────────────────────────────────────────

    def make_created_event(self, risk: ExecutionRisk) -> RiskEvent:
        """Return the RISK_CREATED domain event for *risk*."""
        return make_risk_created(
            risk_id=risk.risk_id,
            execution_id=risk.execution_id,
            portfolio_id=risk.portfolio_id,
            strategy_id=risk.strategy_id,
            actor=ACTOR_FACTORY,
        )
