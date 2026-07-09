"""iios/investment/company/company_exceptions.py
Exception hierarchy for the Company Intelligence Engine.
All codes carry the CI- prefix.
"""
from __future__ import annotations


class CompanyIntelligenceError(Exception):
    """Root exception — CI-000."""

    code = "CI-000"

    def __init__(
        self,
        message: str = "Company intelligence error",
        code: str | None = None,
    ) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Company (CI-010) ──────────────────────────────────────────────────────────

class CompanyError(CompanyIntelligenceError):
    code = "CI-010"


class CompanyNotFoundError(CompanyError):
    code = "CI-011"

    def __init__(self, message: str = "", *, company_id: str = "") -> None:
        self.company_id = company_id
        super().__init__(message or f"Company not found: {company_id!r}")


class CompanyAlreadyExistsError(CompanyError):
    code = "CI-012"

    def __init__(self, message: str = "", *, company_id: str = "") -> None:
        self.company_id = company_id
        super().__init__(message or f"Company already exists: {company_id!r}")


# ── Profile (CI-020) ──────────────────────────────────────────────────────────

class ProfileError(CompanyIntelligenceError):
    code = "CI-020"


class ProfileNotFoundError(ProfileError):
    code = "CI-021"

    def __init__(self, company_id: str = "") -> None:
        super().__init__(f"Company profile not found: {company_id!r}")


class ProfileInvalidError(ProfileError):
    code = "CI-022"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid company profile: {detail}")


class ProfileStaleError(ProfileError):
    code = "CI-023"

    def __init__(self, message: str = "", age_sec: float = 0.0) -> None:
        self.age_sec = age_sec
        super().__init__(message or f"Company profile is stale (age={age_sec:.1f}s)")


# ── Financial (CI-030) ────────────────────────────────────────────────────────

class FinancialError(CompanyIntelligenceError):
    code = "CI-030"


class FinancialDataMissingError(FinancialError):
    code = "CI-031"

    def __init__(self, field: str = "") -> None:
        super().__init__(f"Financial data missing: {field!r}")


class FinancialDataInvalidError(FinancialError):
    code = "CI-032"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid financial data: {detail}")


class FinancialAnalysisFailedError(FinancialError):
    code = "CI-033"

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Financial analysis failed: {reason}")


# ── Fundamental (CI-040) ──────────────────────────────────────────────────────

class FundamentalError(CompanyIntelligenceError):
    code = "CI-040"


class FundamentalDataMissingError(FundamentalError):
    code = "CI-041"

    def __init__(self, field: str = "") -> None:
        super().__init__(f"Fundamental data missing: {field!r}")


class FundamentalDataInvalidError(FundamentalError):
    code = "CI-042"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid fundamental data: {detail}")


# ── Valuation (CI-050) ────────────────────────────────────────────────────────

class ValuationError(CompanyIntelligenceError):
    code = "CI-050"


class ValuationDataMissingError(ValuationError):
    code = "CI-051"

    def __init__(self, field: str = "") -> None:
        super().__init__(f"Valuation data missing: {field!r}")


class ValuationInvalidError(ValuationError):
    code = "CI-052"

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid valuation: {detail}")


# ── Ownership (CI-060) ────────────────────────────────────────────────────────

class OwnershipError(CompanyIntelligenceError):
    code = "CI-060"


class OwnershipDataMissingError(OwnershipError):
    code = "CI-061"

    def __init__(self, field: str = "") -> None:
        super().__init__(f"Ownership data missing: {field!r}")


# ── Governance (CI-070) ───────────────────────────────────────────────────────

class GovernanceError(CompanyIntelligenceError):
    code = "CI-070"


class GovernanceDataMissingError(GovernanceError):
    code = "CI-071"

    def __init__(self, field: str = "") -> None:
        super().__init__(f"Governance data missing: {field!r}")


# ── Engine Lifecycle (CI-080) ─────────────────────────────────────────────────

class CompanyEngineError(CompanyIntelligenceError):
    code = "CI-080"


class CompanyEngineNotInitializedError(CompanyEngineError):
    code = "CI-081"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Company Intelligence Engine is not initialized")


class CompanyEngineAlreadyRunningError(CompanyEngineError):
    code = "CI-082"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Company Intelligence Engine is already running")


# ── Registry (CI-090) ─────────────────────────────────────────────────────────

class CompanyRegistryError(CompanyIntelligenceError):
    code = "CI-090"


class CompanyRegistryItemNotFoundError(CompanyRegistryError):
    code = "CI-091"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item not found: {item_id!r}")


class CompanyRegistryItemAlreadyExistsError(CompanyRegistryError):
    code = "CI-092"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        self.item_id = item_id
        super().__init__(message or f"Registry item already exists: {item_id!r}")


class CompanyRegistryOverflowError(CompanyRegistryError):
    code = "CI-093"

    def __init__(self, message: str = "", *, capacity: int = 0, current: int = 0) -> None:
        self.capacity = capacity
        self.current  = current
        super().__init__(message or f"Registry capacity exceeded (max={capacity})")
