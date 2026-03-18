"""
Fail-Safe Risk Guardian
========================
Last hard gate before any order reaches the broker.

Public API::
    from risk_guardian import FailSafeRiskGuardian, GuardianDecision

    guardian = FailSafeRiskGuardian(total_capital=1_000_000)
    decision = guardian.evaluate(signals, snapshot, portfolio)
"""

from .risk_guardian import FailSafeRiskGuardian, GuardianDecision

__all__ = ["FailSafeRiskGuardian", "GuardianDecision"]
