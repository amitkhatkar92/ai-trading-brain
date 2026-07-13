"""iios/investment/company/governance/management_governance_engine.py
PRIMARY ENGINE — Institutional Management & Governance Intelligence Engine.

Consumes from:
  • FinancialSnapshot   (iios.investment.company.financials)
  • EarningsSnapshot    (iios.investment.company.earnings)
  • BusinessQualitySnapshot (iios.investment.company.business_quality)
  • ValuationSnapshot   (iios.investment.company.valuation) [optional]
  • GrowthSnapshot      (iios.investment.company.growth)   [optional]

Accepts optional governance-specific inputs:
  • board_info      : Dict — board composition and committee structure
  • executive_info  : Dict — executive team profile
  • governance_events : List[str] — incident / award strings

Produces:
  • ManagementSnapshot

Does NOT:
  • Fetch or parse raw corporate filings
  • Make buy/sell/hold recommendations
  • Rank companies against each other
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.company.governance.management_snapshot import ManagementSnapshot
from iios.investment.company.governance.management_profile import ManagementIntelligenceScore
from iios.investment.company.governance.leadership_history import LeadershipHistory
from iios.investment.company.governance.executive_profile import (
    ExecutiveTeamProfile, build_executive_team,
)
from iios.investment.company.governance.board_profile import (
    BoardComposition, CommitteeStructure,
    build_board_composition, build_committee_structure,
)
from iios.investment.company.governance.governance_events import classify_events
from iios.investment.company.governance.management_quality import ManagementQualityEngine
from iios.investment.company.governance.governance_engine import GovernanceAnalysisEngine
from iios.investment.company.governance.capital_allocation import CapitalAllocationEngine
from iios.investment.company.governance.transparency_engine import TransparencyEngine
from iios.investment.company.governance.governance_risk import GovernanceRiskEngine
from iios.investment.company.governance.management_score import compute_management_score
from iios.investment.company.governance.leadership_confidence import compute_leadership_confidence
from iios.investment.company.governance.governance_plugin import (
    GovernancePlugin, GovernancePluginRegistry,
)
from iios.investment.company.governance.management_statistics import clamp


class ManagementGovernanceEngine:
    """
    Thread-safe Management & Governance Intelligence Engine.
    One instance should exist per IIOS deployment (singleton encouraged).
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._history = LeadershipHistory()
        self._registry = GovernancePluginRegistry()

        self._mgmt_engine         = ManagementQualityEngine()
        self._governance_engine   = GovernanceAnalysisEngine()
        self._capital_engine      = CapitalAllocationEngine()
        self._transparency_engine = TransparencyEngine()
        self._risk_engine         = GovernanceRiskEngine()

    # ── Public API ───────────────────────────────────────────────────────────────

    def ingest(
        self,
        ticker:              str,
        financial_snapshot:  Any,                      # FinancialSnapshot
        earnings_snapshot:   Any,                      # EarningsSnapshot
        business_quality:    Any,                      # BusinessQualitySnapshot
        valuation_snapshot:  Any = None,               # Optional[ValuationSnapshot]
        growth_snapshot:     Any = None,               # Optional[GrowthSnapshot]
        board_info:          Optional[Dict] = None,    # board composition & committee data
        executive_info:      Optional[Dict] = None,    # executive team data
        governance_events:   Optional[List[str]] = None,  # incident/award strings
        governance_standard: str = "generic",
    ) -> ManagementSnapshot:
        """
        Compute and store a ManagementSnapshot for the given ticker.
        Returns the snapshot (also accessible via get_snapshot()).
        """
        inputs = self._extract_inputs(
            ticker=ticker,
            financial_snapshot=financial_snapshot,
            earnings_snapshot=earnings_snapshot,
            business_quality=business_quality,
            valuation_snapshot=valuation_snapshot,
            growth_snapshot=growth_snapshot,
            board_info=board_info,
            executive_info=executive_info,
            governance_events=governance_events,
            governance_standard=governance_standard,
        )

        snapshot = self._build_snapshot(ticker, inputs, governance_standard)

        with self._lock:
            self._history.push(ticker, snapshot)

        return snapshot

    def get_snapshot(self, ticker: str) -> Optional[ManagementSnapshot]:
        with self._lock:
            return self._history.get_latest(ticker)

    def get_management_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.management_score.overall_score if s else None

    def get_governance_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.governance.overall_governance_score if s else None

    def get_capital_allocation_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.capital_allocation.overall_capital_score if s else None

    def get_transparency_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.transparency.overall_transparency_score if s else None

    def get_key_person_risk(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.governance_risk.key_person_risk_score if s else None

    def get_governance_risk_score(self, ticker: str) -> Optional[float]:
        s = self.get_snapshot(ticker)
        return s.governance_risk.overall_risk_score if s else None

    def get_alerts(self, ticker: str) -> List[str]:
        s = self.get_snapshot(ticker)
        return s.governance_risk.alerts if s else []

    def known_tickers(self) -> List[str]:
        with self._lock:
            return self._history.all_tickers()

    def register_governance_plugin(self, plugin: GovernancePlugin) -> None:
        """Register a custom GovernancePlugin."""
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
        board_info:          Optional[Dict],
        executive_info:      Optional[Dict],
        governance_events:   Optional[List[str]],
        governance_standard: str,
    ) -> Dict[str, Any]:
        inp: Dict[str, Any] = {"ticker": ticker}

        # ── From FinancialSnapshot ────────────────────────────────────────────
        inp["current_revenue"] = getattr(financial_snapshot, "revenue", None)
        _cf = getattr(financial_snapshot, "cashflow_metrics", None)
        inp["current_fcf"]  = getattr(_cf, "free_cash_flow", None)
        inp["current_ocf"]  = getattr(_cf, "operating_cash_flow", None)
        _im = getattr(financial_snapshot, "income_metrics", None)
        inp["net_income"]   = getattr(_im, "net_income", None)
        _bs = getattr(financial_snapshot, "balance_sheet_metrics", None)
        inp["total_debt"]   = getattr(_bs, "total_debt", None)
        inp["total_equity"] = getattr(financial_snapshot, "total_equity", None)
        _ratios = getattr(financial_snapshot, "ratios", {}) or {}
        if isinstance(_ratios, dict):
            inp["dividend_per_share"]    = _ratios.get("dividend_per_share")
            inp["dividend_payout_ratio"] = _ratios.get("dividend_payout_ratio")
        else:
            inp["dividend_per_share"]    = None
            inp["dividend_payout_ratio"] = None

        # Debt/Equity ratio
        if inp["total_debt"] is not None and inp["total_equity"] and inp["total_equity"] != 0:
            inp["debt_to_equity"] = inp["total_debt"] / inp["total_equity"]
        else:
            inp["debt_to_equity"] = None

        # FCF margin
        rev = inp["current_revenue"]
        fcf = inp["current_fcf"]
        inp["fcf_margin"] = (fcf / rev) if (fcf is not None and rev and rev > 0) else None

        # ── From EarningsSnapshot ─────────────────────────────────────────────
        _trend = getattr(earnings_snapshot, "trend", None)
        inp["eps_cagr"]          = getattr(_trend, "cagr_eps", None)
        inp["revenue_cagr"]      = getattr(_trend, "cagr_revenue", None)

        _prof = getattr(earnings_snapshot, "profitability", None)
        inp["avg_roic"]         = getattr(_prof, "avg_roic", None)
        inp["avg_roe"]          = getattr(_prof, "avg_roe", None)
        inp["net_margin"]       = getattr(_prof, "net_margin", None)
        inp["avg_net_margin"]   = getattr(_prof, "avg_net_margin", None)
        inp["fcf_margin_earn"]  = getattr(_prof, "fcf_margin", None)   # from earnings

        _qual = getattr(earnings_snapshot, "quality", None)
        inp["earnings_quality_score"] = getattr(_qual, "overall_score", None)
        inp["consistency_score"]      = getattr(_qual, "consistency_score", None)
        inp["avg_ocf_to_ni"]          = getattr(_qual, "avg_ocf_to_ni", None)
        inp["avg_accruals_ratio"]     = getattr(_qual, "avg_accruals_ratio", None)

        _risk = getattr(earnings_snapshot, "risk", None)
        inp["earnings_stability_score"] = getattr(_risk, "earnings_stability_score", None)
        inp["is_cyclical"]              = getattr(_risk, "is_cyclical", None)

        inp["history_depth"] = getattr(earnings_snapshot, "history_depth", 0) or 0

        # ── From BusinessQualitySnapshot ──────────────────────────────────────
        _moat = getattr(business_quality, "moat", None)
        inp["moat_score"]         = getattr(_moat, "moat_score", None)
        inp["bq_avg_roic"]        = getattr(_moat, "avg_roic", None)
        inp["moat_types"]         = getattr(_moat, "detected_moat_types", None) or []

        _ops = getattr(business_quality, "operational", None)
        inp["operational_quality_score"] = getattr(_ops, "operational_quality_score", None)

        _res = getattr(business_quality, "resilience", None)
        inp["resilience_score"] = getattr(_res, "resilience_score", None)

        # ── From GrowthSnapshot (optional) ─────────────────────────────────────
        if growth_snapshot is not None:
            _gs = getattr(growth_snapshot, "growth_score", None)
            inp["growth_overall_score"] = getattr(_gs, "overall_score", None)
            _sus = getattr(growth_snapshot, "sustainability", None)
            inp["sustainability_score"] = getattr(_sus, "sustainability_score", None)
        else:
            inp["growth_overall_score"] = None
            inp["sustainability_score"] = None

        # ── Governance-specific inputs ─────────────────────────────────────────
        inp["board_info"]          = board_info or {}
        inp["executive_info"]      = executive_info or {}
        inp["governance_events"]   = governance_events or []
        inp["governance_standard"] = governance_standard

        # ── Restatement count ──────────────────────────────────────────────────
        inp["restatement_count"] = int(inp["board_info"].get("reporting_restatements") or 0)
        inp["regulatory_actions"] = inp["board_info"].get("regulatory_actions") or []

        return inp

    # ── Internal: snapshot assembly ───────────────────────────────────────────

    def _build_snapshot(
        self,
        ticker:   str,
        inp:      Dict[str, Any],
        standard: str,
    ) -> ManagementSnapshot:

        # ── Build structural profiles ─────────────────────────────────────────
        board      = build_board_composition(inp.get("board_info"))
        committees = build_committee_structure(inp.get("board_info"))
        exec_team  = build_executive_team(inp.get("executive_info"))
        event_log  = classify_events(inp.get("governance_events"))

        # ── Merge executive_info fields into exec_team from board_info fallback ─
        if exec_team.ceo_tenure_years is None:
            exec_team.ceo_tenure_years = inp["board_info"].get("ceo_tenure_years")
        if exec_team.cfo_tenure_years is None:
            exec_team.cfo_tenure_years = inp["board_info"].get("cfo_tenure_years")
        if not exec_team.is_founder_led:
            exec_team.is_founder_led = bool(inp["board_info"].get("ceo_is_founder", False))
        if not exec_team.ceo_chairman_same:
            exec_team.ceo_chairman_same = bool(inp["board_info"].get("ceo_chairman_same", False))
        if exec_team.promoter_holding_pct is None:
            exec_team.promoter_holding_pct = inp["board_info"].get("promoter_holding_pct")
        if not exec_team.is_family_controlled:
            exec_team.is_family_controlled = bool(inp["board_info"].get("is_family_controlled", False))
        if exec_team.leadership_changes_3y == 0:
            exec_team.leadership_changes_3y = int(
                inp["executive_info"].get("leadership_changes_3y") or 0
            )

        # ── Plugin evaluation ─────────────────────────────────────────────────
        plugin_inputs = {**inp, "board": board, "committees": committees,
                         "executive_team": exec_team, "event_log": event_log}
        plugin_results = self._registry.run_all(plugin_inputs)

        # Aggregate plugin governance adjustments
        gov_adjustments: Dict[str, float] = {}
        extra_alerts: List[str] = []
        for pr in plugin_results:
            for k, v in (pr.get("governance_adjustments") or {}).items():
                gov_adjustments[k] = gov_adjustments.get(k, 0.0) + v
            extra_alerts.extend(pr.get("alerts") or [])

        # ── Management quality ────────────────────────────────────────────────
        mgmt_quality = self._mgmt_engine.compute(
            ceo_tenure_years=exec_team.ceo_tenure_years,
            leadership_changes_3y=exec_team.leadership_changes_3y,
            ceo_chairman_same=exec_team.ceo_chairman_same,
            is_founder_led=exec_team.is_founder_led,
            earnings_stability_score=inp.get("earnings_stability_score"),
            consistency_score=inp.get("consistency_score"),
            operational_quality_score=inp.get("operational_quality_score"),
            avg_roic=inp.get("avg_roic") or inp.get("bq_avg_roic"),
            moat_score=inp.get("moat_score"),
            growth_score=inp.get("growth_overall_score"),
            resilience_score=inp.get("resilience_score"),
            sustainability_score=inp.get("sustainability_score"),
            earnings_quality_score=inp.get("earnings_quality_score"),
            avg_ocf_to_ni=inp.get("avg_ocf_to_ni"),
            restatement_count=inp.get("restatement_count", 0),
            governance_incidents=event_log.high_severity_count,
            eps_cagr=inp.get("eps_cagr"),
            debt_to_equity=inp.get("debt_to_equity"),
            payout_ratio=inp.get("dividend_payout_ratio"),
        )

        # ── Governance ────────────────────────────────────────────────────────
        governance_profile = self._governance_engine.compute(
            board=board,
            committees=committees,
            event_log=event_log,
            ceo_chairman_same=exec_team.ceo_chairman_same,
            is_family_controlled=exec_team.is_family_controlled,
            promoter_holding_pct=exec_team.promoter_holding_pct,
            governance_standard=standard,
        )
        # Apply plugin governance adjustments
        if "overall" in gov_adjustments:
            governance_profile.overall_governance_score = clamp(
                governance_profile.overall_governance_score + gov_adjustments["overall"],
                0, 100,
            )

        # ── Capital allocation ────────────────────────────────────────────────
        capital_profile = self._capital_engine.compute(
            avg_roic=inp.get("avg_roic") or inp.get("bq_avg_roic"),
            avg_roe=inp.get("avg_roe"),
            fcf_margin=inp.get("fcf_margin") or inp.get("fcf_margin_earn"),
            avg_ocf_to_ni=inp.get("avg_ocf_to_ni"),
            dividend_payout_ratio=inp.get("dividend_payout_ratio"),
            dividend_per_share=inp.get("dividend_per_share"),
            debt_to_equity=inp.get("debt_to_equity"),
            avg_net_margin=inp.get("avg_net_margin"),
            net_margin=inp.get("net_margin"),
            eps_cagr=inp.get("eps_cagr"),
            revenue_cagr=inp.get("revenue_cagr"),
            sustainability=inp.get("sustainability_score"),
        )

        # ── Transparency ──────────────────────────────────────────────────────
        transparency_profile = self._transparency_engine.compute(
            earnings_quality_score=inp.get("earnings_quality_score"),
            consistency_score=inp.get("consistency_score"),
            avg_accruals_ratio=inp.get("avg_accruals_ratio"),
            avg_ocf_to_ni=inp.get("avg_ocf_to_ni"),
            restatement_count=inp.get("restatement_count", 0),
            event_log=event_log,
            regulatory_actions=inp.get("regulatory_actions"),
            governance_standard=standard,
        )

        # ── Governance risk ───────────────────────────────────────────────────
        governance_risk = self._risk_engine.compute(
            ceo_tenure_years=exec_team.ceo_tenure_years,
            cfo_tenure_years=exec_team.cfo_tenure_years,
            is_founder_led=exec_team.is_founder_led,
            executive_team_size=exec_team.executive_team_size,
            leadership_changes_3y=exec_team.leadership_changes_3y,
            has_nomination_committee=committees.has_nomination_committee,
            avg_director_tenure=board.avg_director_tenure_years,
            independence_ratio=board.independence_ratio,
            ceo_chairman_same=exec_team.ceo_chairman_same,
            is_family_controlled=exec_team.is_family_controlled,
            event_log=event_log,
            regulatory_actions=inp.get("regulatory_actions"),
            restatement_count=inp.get("restatement_count", 0),
        )
        governance_risk.alerts.extend(extra_alerts)

        # ── Management Intelligence Score ─────────────────────────────────────
        management_score = compute_management_score(
            management_quality_score=mgmt_quality.overall_quality_score,
            governance_score=governance_profile.overall_governance_score,
            capital_allocation_score=capital_profile.overall_capital_score,
            transparency_score=transparency_profile.overall_transparency_score,
            governance_risk_score=governance_risk.overall_risk_score,
        )

        # ── Confidence ────────────────────────────────────────────────────────
        confidence = compute_leadership_confidence(
            has_board_data=bool(inp.get("board_info")),
            has_executive_data=bool(inp.get("executive_info")),
            has_earnings_quality=inp.get("earnings_quality_score") is not None,
            has_financial_data=inp.get("avg_roic") is not None,
            history_depth=inp.get("history_depth", 0),
            has_incidents_data=bool(inp.get("governance_events") is not None),
            governance_standard=standard,
        )

        # ── Data sources ──────────────────────────────────────────────────────
        data_sources = ["earnings_snapshot", "business_quality"]
        if inp.get("avg_roic") is not None:
            data_sources.append("financial_snapshot")
        if inp.get("board_info"):
            data_sources.append("board_info")
        if inp.get("executive_info"):
            data_sources.append("executive_info")
        if inp.get("governance_events"):
            data_sources.append("governance_events")

        return ManagementSnapshot(
            ticker=ticker,
            executive_team=exec_team,
            board=board,
            committees=committees,
            management_quality=mgmt_quality,
            governance=governance_profile,
            capital_allocation=capital_profile,
            transparency=transparency_profile,
            governance_risk=governance_risk,
            management_score=management_score,
            confidence=confidence,
            governance_standard=standard,
            data_sources=data_sources,
        )
