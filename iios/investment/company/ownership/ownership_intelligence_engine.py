"""iios/investment/company/ownership/ownership_intelligence_engine.py
PRIMARY ENGINE — Institutional Ownership & Capital Allocation Intelligence Engine.

Consumes:
  • FinancialSnapshot         (iios.investment.company.financials)
  • EarningsSnapshot          (iios.investment.company.earnings)
  • BusinessQualitySnapshot   (iios.investment.company.business_quality)
  • ValuationSnapshot         (iios.investment.company.valuation)     [optional]
  • GrowthSnapshot            (iios.investment.company.growth)        [optional]
  • ManagementSnapshot        (iios.investment.company.governance)    [optional]

Accepts optional ownership-specific inputs:
  • ownership_data : Dict — shareholder composition data
  • insider_data   : Dict — insider transaction data
  • ownership_standard : str — "sebi" | "sec" | "fca" | "asx" | "generic"

Produces:
  • OwnershipSnapshot

Does NOT:
  • Parse raw exchange filings or shareholder disclosures
  • Make buy/sell/hold recommendations
  • Rank companies against each other
  • Allocate portfolio weights
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.company.ownership.ownership_snapshot import OwnershipSnapshot
from iios.investment.company.ownership.ownership_history import OwnershipHistory
from iios.investment.company.ownership.shareholder_registry import (
    build_shareholder_registry,
)
from iios.investment.company.ownership.shareholder_analysis import ShareholderAnalysisEngine
from iios.investment.company.ownership.insider_activity import InsiderActivityEngine
from iios.investment.company.ownership.capital_allocation_engine import (
    OwnershipCapitalAllocationEngine,
)
from iios.investment.company.ownership.value_creation import ShareholderValueEngine
from iios.investment.company.ownership.ownership_risk import OwnershipRiskEngine
from iios.investment.company.ownership.ownership_score import compute_ownership_score
from iios.investment.company.ownership.ownership_quality import compute_ownership_quality_score
from iios.investment.company.ownership.capital_allocation_score import compute_capital_allocation_score
from iios.investment.company.ownership.ownership_confidence import compute_ownership_confidence
from iios.investment.company.ownership.ownership_plugin import (
    OwnershipPlugin, OwnershipPluginRegistry,
)
from iios.investment.company.ownership.ownership_statistics import clamp


class OwnershipIntelligenceEngine:
    """
    Thread-safe Ownership & Capital Allocation Intelligence Engine.
    One instance should be used per IIOS deployment.
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._history  = OwnershipHistory()
        self._registry = OwnershipPluginRegistry()

        self._shareholder_engine  = ShareholderAnalysisEngine()
        self._insider_engine      = InsiderActivityEngine()
        self._capital_engine      = OwnershipCapitalAllocationEngine()
        self._value_engine        = ShareholderValueEngine()
        self._risk_engine         = OwnershipRiskEngine()

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest(
        self,
        ticker:               str,
        financial_snapshot:   Any,                          # FinancialSnapshot
        earnings_snapshot:    Any,                          # EarningsSnapshot
        business_quality:     Any,                          # BusinessQualitySnapshot
        valuation_snapshot:   Any = None,                   # Optional[ValuationSnapshot]
        growth_snapshot:      Any = None,                   # Optional[GrowthSnapshot]
        management_snapshot:  Any = None,                   # Optional[ManagementSnapshot]
        ownership_data:       Optional[Dict] = None,        # shareholder composition
        insider_data:         Optional[Dict] = None,        # insider transactions
        ownership_standard:   str = "generic",
    ) -> OwnershipSnapshot:
        """
        Compute and store an OwnershipSnapshot for the given ticker.
        Returns the snapshot (also accessible via get_snapshot()).
        """
        inputs = self._extract_inputs(
            ticker=ticker,
            financial_snapshot=financial_snapshot,
            earnings_snapshot=earnings_snapshot,
            business_quality=business_quality,
            valuation_snapshot=valuation_snapshot,
            growth_snapshot=growth_snapshot,
            management_snapshot=management_snapshot,
            ownership_data=ownership_data,
            insider_data=insider_data,
            ownership_standard=ownership_standard,
        )
        snapshot = self._build_snapshot(ticker, inputs, ownership_standard,
                                        management_snapshot, growth_snapshot)
        with self._lock:
            self._history.push(ticker, snapshot)
        return snapshot

    def get_snapshot(self, ticker: str) -> Optional[OwnershipSnapshot]:
        with self._lock:
            return self._history.get_latest(ticker)

    def get_ownership_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.overall_ownership_score if s else None

    def get_capital_allocation_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.capital_allocation.overall_capital_score if s else None

    def get_shareholder_value_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.shareholder_value.overall_value_score if s else None

    def get_insider_alignment_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.insider_activity.alignment_score if s else None

    def get_ownership_risk_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.ownership_risk.overall_risk_score if s else None

    def get_promoter_holding(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.shareholder_registry.promoter_pct if s else None

    def get_institutional_holding(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.shareholder_registry.institutional_pct if s else None

    def get_alerts(self, ticker: str) -> List[str]:
        s = self.get_snapshot(ticker)
        return s.ownership_risk.alerts if s else []

    def get_ownership_history(self, ticker: str, n: int = 10) -> List[OwnershipSnapshot]:
        with self._lock:
            return self._history.get_history(ticker, n)

    def known_tickers(self) -> List[str]:
        with self._lock:
            return self._history.all_tickers()

    def register_ownership_plugin(self, plugin: OwnershipPlugin) -> None:
        """Register a custom OwnershipPlugin for jurisdiction-specific analysis."""
        self._registry.register(plugin)

    # ── Internal: input extraction ────────────────────────────────────────────

    def _extract_inputs(
        self,
        ticker:              str,
        financial_snapshot:  Any,
        earnings_snapshot:   Any,
        business_quality:    Any,
        valuation_snapshot:  Any,
        growth_snapshot:     Any,
        management_snapshot: Any,
        ownership_data:      Optional[Dict],
        insider_data:        Optional[Dict],
        ownership_standard:  str,
    ) -> Dict[str, Any]:
        inp: Dict[str, Any] = {"ticker": ticker}

        # ── From FinancialSnapshot ─────────────────────────────────────────────
        inp["revenue"]      = getattr(financial_snapshot, "revenue", None)
        inp["total_equity"] = getattr(financial_snapshot, "total_equity", None)
        inp["total_assets"] = getattr(financial_snapshot, "total_assets", None)

        _cf = getattr(financial_snapshot, "cashflow_metrics", None)
        inp["fcf"]  = getattr(_cf, "free_cash_flow", None)
        inp["ocf"]  = getattr(_cf, "operating_cash_flow", None)
        inp["capex"] = getattr(_cf, "capex", None)

        _im = getattr(financial_snapshot, "income_metrics", None)
        inp["net_income"] = getattr(_im, "net_income", None)

        _bs = getattr(financial_snapshot, "balance_sheet_metrics", None)
        inp["total_debt"] = getattr(_bs, "total_debt", None)
        inp["cash"]       = getattr(_bs, "cash_and_equivalents", None)

        _ratios = getattr(financial_snapshot, "ratios", {}) or {}
        if isinstance(_ratios, dict):
            inp["dividend_per_share"]    = _ratios.get("dividend_per_share")
            inp["dividend_payout_ratio"] = _ratios.get("dividend_payout_ratio")
        else:
            inp["dividend_per_share"]    = None
            inp["dividend_payout_ratio"] = None

        # FCF margin
        rev = inp["revenue"]
        fcf = inp["fcf"]
        inp["fcf_margin"] = (fcf / rev) if (fcf is not None and rev and rev > 0) else None

        # ── From EarningsSnapshot ──────────────────────────────────────────────
        _trend = getattr(earnings_snapshot, "trend", None)
        inp["eps_cagr"]     = getattr(_trend, "cagr_eps", None)
        inp["revenue_cagr"] = getattr(_trend, "cagr_revenue", None)

        _prof = getattr(earnings_snapshot, "profitability", None)
        inp["avg_roic"]       = getattr(_prof, "avg_roic", None)
        inp["avg_roe"]        = getattr(_prof, "avg_roe", None)
        inp["net_margin"]     = getattr(_prof, "net_margin", None)
        inp["avg_net_margin"] = getattr(_prof, "avg_net_margin", None)
        inp["fcf_margin_earn"] = getattr(_prof, "fcf_margin", None)

        _qual = getattr(earnings_snapshot, "quality", None)
        inp["earnings_quality_score"] = getattr(_qual, "overall_score", None)
        inp["consistency_score"]      = getattr(_qual, "consistency_score", None)
        inp["avg_ocf_to_ni"]          = getattr(_qual, "avg_ocf_to_ni", None)

        inp["history_depth"] = getattr(earnings_snapshot, "history_depth", 0) or 0

        # ── From BusinessQualitySnapshot ───────────────────────────────────────
        _moat = getattr(business_quality, "moat", None)
        inp["moat_score"] = getattr(_moat, "moat_score", None)

        # ── From GrowthSnapshot (optional) ─────────────────────────────────────
        if growth_snapshot is not None:
            _sus = getattr(growth_snapshot, "sustainability", None)
            inp["sustainability_score"] = getattr(_sus, "sustainability_score", None)
        else:
            inp["sustainability_score"] = None

        # ── Ownership-specific inputs ──────────────────────────────────────────
        inp["ownership_data"]    = ownership_data or {}
        inp["insider_data"]      = insider_data or {}
        inp["ownership_standard"] = ownership_standard

        # Merge management-level governance fields into insider/board data
        if management_snapshot is not None:
            _exec = getattr(management_snapshot, "executive_team", None)
            _board_comp = getattr(management_snapshot, "board", None)
            if _exec is not None and not inp["insider_data"].get("ceo_ownership_pct"):
                # No explicit insider data → try management snapshot fields
                if "ceo_ownership_pct" not in inp["insider_data"]:
                    pass  # ManagementSnapshot doesn't carry CEO holding pct
            # Extract board independence for risk engine
            inp["board_independence_ratio"] = getattr(_board_comp, "independence_ratio", None)
            inp["is_family_controlled"]     = bool(getattr(_exec, "is_family_controlled", False))
            inp["ceo_chairman_same"]        = bool(getattr(_exec, "ceo_chairman_same", False))
        else:
            inp["board_independence_ratio"] = None
            inp["is_family_controlled"]     = False
            inp["ceo_chairman_same"]        = False

        # ESOP from insider_data
        v = inp["insider_data"].get("esop_outstanding_pct")
        inp["esop_outstanding_pct"] = float(v) if v is not None else None

        return inp

    # ── Internal: snapshot assembly ───────────────────────────────────────────

    def _build_snapshot(
        self,
        ticker:              str,
        inp:                 Dict[str, Any],
        standard:            str,
        management_snapshot: Any,
        growth_snapshot:     Any,
    ) -> OwnershipSnapshot:

        # ── Shareholder registry ──────────────────────────────────────────────
        registry = build_shareholder_registry(
            ticker=ticker,
            ownership_data=inp.get("ownership_data"),
            jurisdiction=inp.get("ownership_standard", "generic"),
        )

        # ── Plugin inputs ──────────────────────────────────────────────────────
        plugin_inputs = {**inp, "registry": registry}
        plugin_results = self._registry.run_all(plugin_inputs)
        ownership_adjustments: Dict[str, float] = {}
        extra_alerts: List[str] = []
        for pr in plugin_results:
            for k, v in (pr.get("ownership_adjustments") or {}).items():
                ownership_adjustments[k] = ownership_adjustments.get(k, 0.0) + v
            extra_alerts.extend(pr.get("alerts") or [])

        # ── Shareholder analysis ───────────────────────────────────────────────
        ownership_structure = self._shareholder_engine.compute(
            registry=registry,
            management_snapshot=management_snapshot,
        )
        # Apply plugin adjustments
        if "overall" in ownership_adjustments:
            ownership_structure.overall_structure_score = clamp(
                ownership_structure.overall_structure_score
                + ownership_adjustments["overall"]
            )

        # ── Insider activity ───────────────────────────────────────────────────
        insider_activity = self._insider_engine.compute(
            insider_data=inp.get("insider_data"),
            management_snapshot=management_snapshot,
        )

        # ── Capital allocation ─────────────────────────────────────────────────
        capital_allocation = self._capital_engine.compute(
            avg_roic=inp.get("avg_roic"),
            avg_roe=inp.get("avg_roe"),
            fcf_margin=inp.get("fcf_margin") or inp.get("fcf_margin_earn"),
            fcf=inp.get("fcf"),
            net_income=inp.get("net_income"),
            avg_ocf_to_ni=inp.get("avg_ocf_to_ni"),
            payout_ratio=inp.get("dividend_payout_ratio"),
            div_per_share=inp.get("dividend_per_share"),
            eps_cagr=inp.get("eps_cagr"),
            revenue_cagr=inp.get("revenue_cagr"),
            capex=inp.get("capex"),
            revenue=inp.get("revenue"),
            total_assets=inp.get("total_assets"),
            total_equity=inp.get("total_equity"),
            total_debt=inp.get("total_debt"),
            cash=inp.get("cash"),
            management_snapshot=management_snapshot,
        )

        # ── Shareholder value ─────────────────────────────────────────────────
        shareholder_value = self._value_engine.compute(
            avg_roic=inp.get("avg_roic"),
            avg_roe=inp.get("avg_roe"),
            fcf_margin=inp.get("fcf_margin") or inp.get("fcf_margin_earn"),
            fcf=inp.get("fcf"),
            total_equity=inp.get("total_equity"),
            total_debt=inp.get("total_debt"),
            payout_ratio=inp.get("dividend_payout_ratio"),
            avg_ocf_to_ni=inp.get("avg_ocf_to_ni"),
            div_per_share=inp.get("dividend_per_share"),
            eps_cagr=inp.get("eps_cagr"),
            revenue_cagr=inp.get("revenue_cagr"),
            net_margin=inp.get("net_margin"),
            avg_net_margin=inp.get("avg_net_margin"),
            consistency_score=inp.get("consistency_score"),
            sustainability_score=inp.get("sustainability_score"),
            management_snapshot=management_snapshot,
            growth_snapshot=growth_snapshot,
        )

        # ── Ownership risk ────────────────────────────────────────────────────
        ownership_risk = self._risk_engine.compute(
            registry=registry,
            insider_activity=insider_activity,
            management_snapshot=management_snapshot,
            is_family_controlled=inp.get("is_family_controlled", False),
            ceo_chairman_same=inp.get("ceo_chairman_same", False),
            board_independence_ratio=inp.get("board_independence_ratio"),
            esop_outstanding_pct=inp.get("esop_outstanding_pct"),
        )
        ownership_risk.alerts.extend(extra_alerts)

        # ── Composite scores ───────────────────────────────────────────────────
        ownership_quality_score = compute_ownership_quality_score(
            promoter_stability_score=ownership_structure.promoter_stability_score,
            institutional_quality_score=ownership_structure.institutional_quality_score,
            insider_alignment_score=insider_activity.alignment_score,
            distribution_quality_score=ownership_structure.distribution_quality_score,
        )

        capital_allocation_score_val = compute_capital_allocation_score(
            dividend_policy_score=capital_allocation.dividend_policy_score,
            buyback_quality_score=capital_allocation.buyback_quality_score,
            reinvestment_score=capital_allocation.reinvestment_score,
            debt_management_score=capital_allocation.debt_management_score,
            capex_efficiency_score=capital_allocation.capex_efficiency_score,
        )

        ownership_score = compute_ownership_score(
            ownership_quality_score=ownership_quality_score,
            capital_allocation_score=capital_allocation_score_val,
            shareholder_value_score=shareholder_value.overall_value_score,
            insider_alignment_score=insider_activity.alignment_score,
            ownership_risk_score=ownership_risk.overall_risk_score,
        )

        # ── Confidence ────────────────────────────────────────────────────────
        confidence = compute_ownership_confidence(
            has_ownership_data=bool(inp.get("ownership_data")),
            has_insider_data=bool(inp.get("insider_data")),
            has_financial_data=inp.get("avg_roic") is not None,
            has_promoter_data=registry.promoter_pct is not None,
            has_institutional_data=registry.institutional_pct is not None,
            has_management_data=management_snapshot is not None,
            history_depth=inp.get("history_depth", 0),
            ownership_standard=standard,
        )

        # ── Data sources ───────────────────────────────────────────────────────
        data_sources = ["earnings_snapshot", "business_quality"]
        if inp.get("avg_roic") is not None:
            data_sources.append("financial_snapshot")
        if inp.get("ownership_data"):
            data_sources.append("ownership_data")
        if inp.get("insider_data"):
            data_sources.append("insider_data")
        if management_snapshot is not None:
            data_sources.append("management_snapshot")
        if growth_snapshot is not None:
            data_sources.append("growth_snapshot")

        return OwnershipSnapshot(
            ticker=ticker,
            shareholder_registry=registry,
            ownership_structure=ownership_structure,
            insider_activity=insider_activity,
            capital_allocation=capital_allocation,
            shareholder_value=shareholder_value,
            ownership_risk=ownership_risk,
            ownership_score=ownership_score,
            confidence=confidence,
            ownership_standard=standard,
            data_sources=data_sources,
        )
