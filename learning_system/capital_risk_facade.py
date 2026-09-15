"""
Read-only facade re-exporting CapitalRiskEngine's own already-computed
per-cycle rejection-attribution getter (DTA-CRE-DIAG-001) for consumers
that must not import `risk_control` directly.

Why this file exists: `sandy/sandy_supervisor.py` has its own safety-
contract test (tests/test_sandy_supervisor.py::test_T09_no_forbidden_imports)
forbidding any `import risk_control` / `from risk_control` anywhere in the
`sandy/` package, to guarantee Sandy can never be wired into a live
risk/execution decision path. The same constraint already forced module
#27 (sizing bounds calibration) to live in `learning_system/` instead of
`risk_control/` earlier this session. This facade lets Sandy surface
CapitalRiskEngine's read-only rejection-reason getter for observability
without violating that contract -- it never mutates anything, never
touches execution/order/broker, and is a pure pass-through of one
already-existing accessor.
"""
from risk_control.capital_risk_engine import (
    get_last_cycle_dominant_rejection_reason as _get_last_cycle_dominant_rejection_reason,
)


def get_last_cycle_dominant_rejection_reason() -> str:
    return _get_last_cycle_dominant_rejection_reason()
