"""iios/investment/investment_exceptions.py"""
from __future__ import annotations


class InvestmentEngineError(Exception):
    """Base exception for the Investment Intelligence Engine."""

    code: str = "II-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


# ── Investment ────────────────────────────────────────────────────────────────
class InvestmentError(InvestmentEngineError):         code = "II-010"
class InvestmentNotFoundError(InvestmentError):
    code = "II-011"
    def __init__(self, result_id: str = "") -> None:
        super().__init__(f"Investment result not found: {result_id!r}")

class InvestmentAlreadyExistsError(InvestmentError):
    code = "II-012"
    def __init__(self, result_id: str = "") -> None:
        super().__init__(f"Investment result already exists: {result_id!r}")

class InvestmentFailedError(InvestmentError):         code = "II-013"

# ── Workflow ──────────────────────────────────────────────────────────────────
class WorkflowError(InvestmentEngineError):           code = "II-020"
class WorkflowNotFoundError(WorkflowError):
    code = "II-021"
    def __init__(self, workflow_id: str = "") -> None:
        super().__init__(f"Workflow not found: {workflow_id!r}")

class WorkflowAlreadyExistsError(WorkflowError):
    code = "II-022"
    def __init__(self, workflow_id: str = "") -> None:
        super().__init__(f"Workflow already exists: {workflow_id!r}")

class WorkflowExecutionError(WorkflowError):          code = "II-023"
class WorkflowCancelledError(WorkflowError):          code = "II-024"

# ── Registry ──────────────────────────────────────────────────────────────────
class RegistryError(InvestmentEngineError):           code = "II-030"
class RegistryItemNotFoundError(RegistryError):
    code = "II-031"
    def __init__(self, item_id: str = "") -> None:
        super().__init__(f"Registry item not found: {item_id!r}")

class RegistryItemAlreadyExistsError(RegistryError):
    code = "II-032"
    def __init__(self, item_id: str = "") -> None:
        super().__init__(f"Registry item already exists: {item_id!r}")

class RegistryOverflowError(RegistryError):
    code = "II-033"
    def __init__(self, limit: int) -> None:
        super().__init__(f"Registry capacity limit {limit} reached")

# ── Analysis ──────────────────────────────────────────────────────────────────
class AnalysisError(InvestmentEngineError):           code = "II-040"
class AnalysisFailedError(AnalysisError):             code = "II-041"
class AnalysisTimeoutError(AnalysisError):            code = "II-042"
class AnalysisInvalidError(AnalysisError):            code = "II-043"

# ── Engine Lifecycle ──────────────────────────────────────────────────────────
class EngineLifecycleError(InvestmentEngineError):    code = "II-050"
class EngineNotInitializedError(EngineLifecycleError):
    code = "II-051"
    def __init__(self) -> None:
        super().__init__(
            "InvestmentIntelligenceEngine is not initialized. Call initialize() first."
        )

class EngineAlreadyRunningError(EngineLifecycleError):
    code = "II-052"
    def __init__(self) -> None:
        super().__init__("InvestmentIntelligenceEngine is already running.")

# ── Session ───────────────────────────────────────────────────────────────────
class SessionError(InvestmentEngineError):            code = "II-060"
class SessionNotFoundError(SessionError):
    code = "II-061"
    def __init__(self, session_id: str = "") -> None:
        super().__init__(f"Investment session not found: {session_id!r}")

class SessionExpiredError(SessionError):
    code = "II-062"
    def __init__(self, session_id: str = "") -> None:
        super().__init__(f"Investment session expired: {session_id!r}")

# ── Asset Class ───────────────────────────────────────────────────────────────
class AssetClassError(InvestmentEngineError):         code = "II-070"
class AssetClassNotSupportedError(AssetClassError):
    code = "II-071"
    def __init__(self, asset_class: str = "") -> None:
        super().__init__(f"Asset class not supported: {asset_class!r}")

class AssetClassInvalidError(AssetClassError):        code = "II-072"

# ── Domain Engine ─────────────────────────────────────────────────────────────
class DomainEngineError(InvestmentEngineError):       code = "II-080"
class DomainEngineNotFoundError(DomainEngineError):
    code = "II-081"
    def __init__(self, intelligence_type: str = "") -> None:
        super().__init__(f"Domain engine not found for type: {intelligence_type!r}")

class DomainEngineAlreadyRegisteredError(DomainEngineError):
    code = "II-082"
    def __init__(self, intelligence_type: str = "") -> None:
        super().__init__(f"Domain engine already registered for: {intelligence_type!r}")

# ── Request Validation ────────────────────────────────────────────────────────
class RequestValidationError(InvestmentEngineError):
    code = "II-090"
    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Investment request invalid: {reason}")
