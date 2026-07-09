"""iios/investment/company/company_manager.py
Orchestrates profile management and analysis for all tracked companies.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import (
    DEFAULT_HISTORY_SIZE,
    CompanyStage,
    FinancialHealth,
    GovernanceQuality,
    GrowthProfile,
    OwnershipConcentration,
    SectorClassification,
    ValuationStatus,
)
from iios.investment.company.company_exceptions import (
    CompanyNotFoundError,
)
from iios.investment.company.company_factory import CompanyFactory
from iios.investment.company.company_registry import CompanyRegistry, get_company_registry
from iios.investment.company.financials.financial_engine import FinancialEngine
from iios.investment.company.fundamentals.fundamental_engine import FundamentalEngine
from iios.investment.company.models.company_health import CompanyHealth
from iios.investment.company.models.company_intelligence import CompanyIntelligence
from iios.investment.company.models.company_signal import (
    CompanySignal,
    CompanySignalStrength,
    CompanySignalType,
)
from iios.investment.company.profile.company_history import CompanyHistory
from iios.investment.company.profile.company_profile import CompanyProfile
from iios.investment.company.profile.company_snapshot import CompanySnapshot


@dataclass
class CompanyStatistics:
    companies_tracked:   int   = 0
    analyses_total:      int   = 0
    analyses_successful: int   = 0
    analyses_failed:     int   = 0
    avg_duration_ms:     float = 0.0
    uptime_sec:          float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "companies_tracked":   self.companies_tracked,
            "analyses_total":      self.analyses_total,
            "analyses_successful": self.analyses_successful,
            "analyses_failed":     self.analyses_failed,
            "avg_duration_ms":     round(self.avg_duration_ms, 2),
            "uptime_sec":          round(self.uptime_sec, 2),
        }


class CompanyManager:
    """
    Manages per-company profiles and runs full analysis pipelines.

    Thread-safe; designed as a long-lived singleton.
    """

    def __init__(
        self,
        financial_engine:  FinancialEngine  | None = None,
        fundamental_engine: FundamentalEngine | None = None,
        registry:          CompanyRegistry   | None = None,
        history:           CompanyHistory    | None = None,
        max_history:       int               = DEFAULT_HISTORY_SIZE,
    ) -> None:
        self._lock              = threading.RLock()
        self._financial         = financial_engine  or FinancialEngine()
        self._fundamental       = fundamental_engine or FundamentalEngine()
        self._registry          = registry          or get_company_registry()
        self._history_store:    CompanyHistory      = history or CompanyHistory()
        self._profiles:         dict[str, CompanyProfile]     = {}
        self._latest:           dict[str, CompanyIntelligence] = {}
        self._recent:           deque[CompanyIntelligence]    = deque(maxlen=max_history)
        self._stats             = CompanyStatistics()
        self._started_at        = time.time()
        self._total_duration_ms = 0.0

    # ── registration ─────────────────────────────────────────────────────────

    def register_company(
        self,
        company_id: str,
        ticker:     str          = "",
        name:       str          = "",
        sector:     SectorClassification = SectorClassification.UNKNOWN,
        exchange:   str          = "",
    ) -> CompanyProfile:
        with self._lock:
            if not self._registry.is_registered(company_id):
                self._registry.register_company(
                    company_id=company_id, ticker=ticker,
                    name=name, sector=sector, exchange=exchange,
                )
            if company_id not in self._profiles:
                identity = CompanyFactory.make_identity(
                    company_id=company_id, ticker=ticker, name=name,
                    exchange=exchange, sector=sector,
                )
                profile = CompanyFactory.make_profile(identity)
                self._profiles[company_id] = profile
            return self._profiles[company_id]

    def get_profile(self, company_id: str) -> CompanyProfile:
        with self._lock:
            if company_id not in self._profiles:
                raise CompanyNotFoundError(
                    f"Company profile not found: {company_id}",
                    company_id=company_id,
                )  # noqa: E501
            return self._profiles[company_id]

    # ── analysis ─────────────────────────────────────────────────────────────

    def analyze(
        self,
        company_id:            str,
        income_data:           dict[str, Any]       | None = None,
        balance_data:          dict[str, Any]       | None = None,
        cashflow_data:         dict[str, Any]       | None = None,
        valuation_data:        dict[str, Any]       | None = None,
        ownership_data:        dict[str, Any]       | None = None,
        governance_data:       dict[str, Any]       | None = None,
        corporate_actions_data: list[dict[str, Any]] | None = None,
        ticker:                str                  = "",
        request_id:            str                  = "",
        **metadata: Any,
    ) -> CompanyIntelligence:
        t0 = time.time()
        self._stats.analyses_total += 1

        # Auto-register if unknown
        self.register_company(company_id, ticker=ticker)

        profile = self._profiles[company_id]

        # Update profile data stores
        if income_data or balance_data or cashflow_data:
            profile.update_financials(
                income_data   or {},
                balance_data  or {},
                cashflow_data or {},
            )
        if ownership_data:
            profile.update_ownership(ownership_data)
        if governance_data:
            profile.update_governance(governance_data)

        # Run sub-engines
        fin = self._financial.analyze(
            profile.income_data,
            profile.balance_data,
            profile.cashflow_data,
        )
        fund = self._fundamental.analyze(
            company_id             = company_id,
            valuation_data         = valuation_data or {},
            ownership_data         = profile.ownership_data,
            governance_data        = profile.governance_data,
            corporate_actions_raw  = corporate_actions_data or [],
        )

        # Build CompanyHealth model
        health = CompanyHealth(
            financial_score  = fin.health_score,
            governance_score = fund.governance.governance_score,
            growth_score     = fin.growth_score,
            quality_score    = fin.quality.earnings_quality_score,
            valuation_score  = fund.valuation.valuation_score,
        )
        # Composite overall: fin 35% + governance 20% + growth 20% + quality 15% + valuation 10%
        health.overall_score = round(
            fin.health_score             * 0.35
            + fund.governance.governance_score * 0.20
            + fin.growth_score               * 0.20
            + fin.quality.earnings_quality_score * 0.15
            + fund.valuation.valuation_score  * 0.10,
            2,
        )
        health._rebuild_labels()

        # Compile CompanyIntelligence
        intel = CompanyIntelligence(
            company_id                   = company_id,
            ticker                       = ticker or profile.identity.ticker,
            request_id                   = request_id,
            sector                       = profile.identity.sector,
            stage                        = profile.company_meta.stage,
            financial_health             = fin.health,
            growth_profile               = fin.growth_profile,
            valuation_status             = fund.valuation.status,
            ownership_concentration      = fund.ownership.concentration,
            governance_quality           = fund.governance.quality,
            health_score                 = health.overall_score,
            financial_strength_score     = fin.health_score,
            governance_score             = fund.governance.governance_score,
            growth_potential_score       = fin.growth_score,
            business_quality_score       = fin.quality.earnings_quality_score,
            investment_attractiveness_score = fund.attractiveness_score,
            risk_profile_score           = fund.risk_score,
            health                       = health,
            confidence                   = min(1.0, 0.5 + len(profile.income_data) * 0.02),
            metadata                     = dict(metadata),
        )

        # Generate signals
        self._generate_signals(intel, fin, fund)

        # Record duration
        duration_ms = (time.time() - t0) * 1_000
        intel.duration_ms = round(duration_ms, 2)

        # Build snapshot
        snapshot = CompanySnapshot(
            company_id        = company_id,
            health            = fin.health,
            valuation_status  = fund.valuation.status,
            growth_profile    = fin.growth_profile,
            stage             = profile.company_meta.stage,
            pe_ratio          = fund.valuation.pe,
            pb_ratio          = fund.valuation.pb,
            ev_ebitda         = fund.valuation.ev_ebitda,
            promoter_holding  = fund.ownership.promoter_holding,
            institutional_holding = fund.ownership.institutional_holding,
            promoter_pledge_pct = fund.ownership.promoter_pledge_pct,
        )
        profile.update_snapshot(snapshot)
        self._history_store.add(company_id, snapshot)

        # Update stats
        with self._lock:
            self._latest[company_id] = intel
            self._recent.append(intel)
            self._stats.analyses_successful += 1
            self._stats.companies_tracked = len(self._profiles)
            self._total_duration_ms += duration_ms
            total = self._stats.analyses_successful + self._stats.analyses_failed
            if total > 0:
                self._stats.avg_duration_ms = self._total_duration_ms / total

        return intel

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_latest(self, company_id: str) -> CompanyIntelligence:
        with self._lock:
            if company_id not in self._latest:
                raise CompanyNotFoundError(
                    f"No intelligence found for: {company_id}",
                    company_id=company_id,
                )  # noqa: E501
            return self._latest[company_id]

    def recent(self, n: int = 10) -> list[CompanyIntelligence]:
        with self._lock:
            items = list(self._recent)
            return items[-n:] if len(items) >= n else items

    def summary(self, company_id: str) -> CompanySnapshot:
        snap = self._history_store.get_latest(company_id)
        if snap is None:
            raise CompanyNotFoundError(
                f"No snapshot found for: {company_id}",
                company_id=company_id,
            )
        return snap

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats.to_dict()

    def stats_object(self) -> CompanyStatistics:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _generate_signals(
        intel: CompanyIntelligence,
        fin:   Any,
        fund:  Any,
    ) -> None:
        # Financial signals
        if fin.health_score >= 75:
            intel.add_signal(CompanySignal(
                company_id  = intel.company_id,
                signal_type = CompanySignalType.FINANCIAL,
                label       = "strong_financials",
                description = "Financial health score is high",
                strength    = CompanySignalStrength.STRONG,
                confidence  = 0.8,
                direction   = "positive",
                value       = fin.health_score,
            ))
        elif fin.health_score < 35:
            intel.add_signal(CompanySignal(
                company_id  = intel.company_id,
                signal_type = CompanySignalType.FINANCIAL,
                label       = "weak_financials",
                description = "Financial health score is low",
                strength    = CompanySignalStrength.STRONG,
                confidence  = 0.8,
                direction   = "negative",
                value       = fin.health_score,
            ))

        # Valuation signals
        if fund.valuation.valuation_score >= 75:
            intel.add_opportunity("Company appears undervalued vs peers")
        elif fund.valuation.valuation_score < 25:
            intel.add_risk("Company appears significantly overvalued")

        # Ownership signals
        if fund.ownership.high_pledge:
            intel.add_risk(
                f"High promoter pledge ({fund.ownership.promoter_pledge_pct:.1f}%)"
            )

        # Governance signals
        if fund.governance.quality in (GovernanceQuality.POOR, GovernanceQuality.VERY_POOR):
            intel.add_risk("Governance quality is below acceptable threshold")

        # Growth signals
        if fin.growth_profile == GrowthProfile.HIGH_GROWTH:
            intel.add_opportunity("High revenue growth momentum")
        elif fin.growth_profile == GrowthProfile.DECLINING:
            intel.add_risk("Revenue trend is declining")

        # Observations
        intel.add_observation(f"Financial health: {fin.health.value}")
        intel.add_observation(f"Growth profile: {fin.growth_profile.value}")
        intel.add_observation(f"Valuation: {fund.valuation.status.value}")


# ── module-level singleton ────────────────────────────────────────────────────

_manager_lock:     threading.Lock           = threading.Lock()
_manager_instance: CompanyManager | None    = None


def get_company_manager() -> CompanyManager:
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = CompanyManager()
        return _manager_instance


def reset_company_manager() -> None:
    global _manager_instance
    with _manager_lock:
        _manager_instance = None
