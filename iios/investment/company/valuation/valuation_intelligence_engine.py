"""iios/investment/company/valuation/valuation_intelligence_engine.py
Primary Valuation Intelligence Engine — IIOS layer integration point.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationResult, ValuationStatus, ValuationBand,
    ValuationModelPlugin, ValuationPluginRegistry,
)
from iios.investment.company.valuation.valuation_assumptions import ValuationAssumptions
from iios.investment.company.valuation.valuation_snapshot import (
    ValuationSnapshot, ValuationIntelligenceScore, ScenarioResult,
)
from iios.investment.company.valuation.valuation_history import ValuationHistory
from iios.investment.company.valuation.assumption_manager import AssumptionManager
from iios.investment.company.valuation.fair_value_estimate import (
    FairValueEstimate, ValuationRange,
)
from iios.investment.company.valuation.margin_of_safety import MarginOfSafetyEngine
from iios.investment.company.valuation.valuation_range import build_valuation_range
from iios.investment.company.valuation.valuation_statistics import weighted_average, clamp
from iios.investment.company.valuation.dcf_engine import DCFEngine
from iios.investment.company.valuation.dividend_discount_model import DividendDiscountModel
from iios.investment.company.valuation.residual_income_model import ResidualIncomeModel
from iios.investment.company.valuation.asset_based_model import AssetBasedModel
from iios.investment.company.valuation.relative_valuation import RelativeValuationEngine
from iios.investment.company.valuation.peer_valuation import PeerValuationEngine
from iios.investment.company.valuation.industry_benchmark import get_sector_benchmarks
from iios.investment.company.valuation.scenario_engine import ScenarioEngine
from iios.investment.company.valuation.valuation_confidence import compute_valuation_confidence
from iios.investment.company.valuation.valuation_quality import (
    ValuationQuality, assess_valuation_quality,
)
from iios.investment.company.valuation.valuation_score import compute_valuation_score


class ValuationIntelligenceEngine:
    """
    Primary engine for IIOS valuation intelligence.

    Consumes: FinancialSnapshot, EarningsSnapshot, BusinessQualitySnapshot
    Produces:  ValuationSnapshot

    Thread-safe. Does NOT make buy/sell/hold recommendations.
    Does NOT fetch market prices — caller must provide market_price and shares_outstanding.
    """

    def __init__(self) -> None:
        self._lock         = threading.RLock()
        self._history      = ValuationHistory(max_snapshots=20)
        self._asm          = AssumptionManager()
        self._plugins      = ValuationPluginRegistry()
        self._mos_engine   = MarginOfSafetyEngine()
        self._scenario_eng = ScenarioEngine()
        self._dcf          = DCFEngine()
        self._ddm          = DividendDiscountModel()
        self._rim          = ResidualIncomeModel()
        self._asset        = AssetBasedModel()
        self._relative     = RelativeValuationEngine()
        self._peer         = PeerValuationEngine()

    # ── Public API ─────────────────────────────────────────────────────────────

    def ingest(
        self,
        ticker:              str,
        financial_snapshot:  Any,   # FinancialSnapshot
        earnings_snapshot:   Any,   # EarningsSnapshot
        business_quality:    Any,   # BusinessQualitySnapshot
        market_price:        Optional[float],
        shares_outstanding:  Optional[float],
        assumptions:         Optional[ValuationAssumptions] = None,
        peer_snapshots:      Optional[List[Any]] = None,  # List[ValuationSnapshot]
        sector:              Optional[str] = None,
    ) -> ValuationSnapshot:
        with self._lock:
            if assumptions is None:
                assumptions = self._load_or_default(ticker)
            else:
                self._asm.store(ticker, assumptions, source="override")

            snap = self._run(
                ticker, financial_snapshot, earnings_snapshot,
                business_quality, market_price, shares_outstanding,
                assumptions, peer_snapshots or [], sector,
            )
            self._history.push(ticker, snap)
            return snap

    def get_snapshot(self, ticker: str) -> Optional[ValuationSnapshot]:
        return self._history.get_latest(ticker)

    def get_fair_value(self, ticker: str) -> Optional[float]:
        snap = self._history.get_latest(ticker)
        return snap.intrinsic_value if snap else None

    def get_mos(self, ticker: str) -> Optional[float]:
        snap = self._history.get_latest(ticker)
        return snap.margin_of_safety_pct if snap else None

    def get_valuation_band(self, ticker: str) -> ValuationBand:
        snap = self._history.get_latest(ticker)
        return snap.valuation_band if snap else ValuationBand.UNKNOWN

    def get_scenarios(
        self, ticker: str
    ) -> Tuple[Optional[ScenarioResult], Optional[ScenarioResult], Optional[ScenarioResult]]:
        snap = self._history.get_latest(ticker)
        if snap:
            return snap.bull_case, snap.base_case, snap.bear_case
        return None, None, None

    def known_tickers(self) -> List[str]:
        return self._history.all_tickers()

    def register_plugin(self, plugin: ValuationModelPlugin) -> None:
        self._plugins.register(plugin)

    # ── Internal orchestration ─────────────────────────────────────────────────

    def _run(
        self,
        ticker:             str,
        fs:                 Any,
        es:                 Any,
        bqs:                Any,
        market_price:       Optional[float],
        shares:             Optional[float],
        assumptions:        ValuationAssumptions,
        peer_snapshots:     List[Any],
        sector:             Optional[str],
    ) -> ValuationSnapshot:
        # ── Extract inputs from snapshots ─────────────────────────────────────
        inputs = self._extract_inputs(fs, es, bqs, market_price, shares, assumptions, sector)

        # ── Run models ────────────────────────────────────────────────────────
        dcf_result      = self._run_dcf(assumptions, inputs)
        ddm_result      = self._run_ddm(assumptions, inputs)
        rim_result      = self._run_rim(assumptions, inputs)
        asset_result    = self._run_asset(inputs, shares)
        relative_result = self._run_relative(assumptions, inputs, peer_snapshots, sector)

        all_model_results = [dcf_result, ddm_result, rim_result, asset_result, relative_result]

        # ── Plugin results ────────────────────────────────────────────────────
        plugin_results: Dict[str, ValuationResult] = {}
        for plugin in self._plugins.get_plugins():
            try:
                pr = plugin.estimate(
                    ticker             = ticker,
                    financial_snapshot = fs,
                    earnings_snapshot  = es,
                    business_quality   = bqs,
                    assumptions        = assumptions,
                    market_price       = market_price,
                    shares_outstanding = shares,
                )
                if pr:
                    plugin_results[plugin.name] = pr
                    all_model_results.append(pr)
            except Exception:
                pass  # plugin failures are silent

        # ── Blend into fair value ─────────────────────────────────────────────
        fair_value = self._blend(all_model_results, assumptions.model_weights, assumptions.currency)

        # ── Margin of safety ──────────────────────────────────────────────────
        mos = self._mos_engine.compute(fair_value, market_price) if fair_value else None

        # ── Scenarios ─────────────────────────────────────────────────────────
        bull, base, bear = self._scenario_eng.run(
            base_assumptions   = assumptions.dcf,
            fcf_base           = inputs.get("fcf_base"),
            net_debt           = inputs.get("net_debt"),
            shares_outstanding = shares,
            market_price       = market_price,
        )

        # ── Quality / score ───────────────────────────────────────────────────
        quality = assess_valuation_quality(
            dcf_result      = dcf_result,
            relative_result = relative_result,
            rim_result      = rim_result,
            ddm_result      = ddm_result,
            history_depth   = inputs.get("history_depth", 0),
            fcf_base        = inputs.get("fcf_base"),
        )
        confidence = compute_valuation_confidence(
            model_results         = all_model_results,
            history_depth         = quality.history_depth,
            fcf_stability         = inputs.get("fcf_stability", 0.5),
            assumptions_calibrated= self._asm.was_calibrated(ticker),
        )
        val_score = compute_valuation_score(
            quality              = quality,
            overall_confidence   = confidence,
            model_results        = all_model_results,
            assumptions_calibrated= self._asm.was_calibrated(ticker),
        )

        market_cap = None
        if market_price and shares:
            market_cap = market_price * shares

        return ValuationSnapshot(
            ticker              = ticker,
            market_price        = market_price,
            shares_outstanding  = shares,
            market_cap          = market_cap,
            dcf_result          = dcf_result,
            ddm_result          = ddm_result,
            rim_result          = rim_result,
            asset_result        = asset_result,
            relative_result     = relative_result,
            fair_value          = fair_value,
            mos                 = mos,
            bull_case           = bull,
            base_case           = base,
            bear_case           = bear,
            valuation_score     = val_score,
            plugin_results      = plugin_results,
            assumptions_summary = assumptions.to_dict(),
        )

    # ── Model runners ──────────────────────────────────────────────────────────

    def _run_dcf(
        self, assumptions: ValuationAssumptions, inputs: Dict[str, Any]
    ) -> Optional[ValuationResult]:
        try:
            fcf_base = inputs.get("fcf_base")
            if assumptions.dcf.fcf_base_override is not None:
                fcf_base = assumptions.dcf.fcf_base_override
            return self._dcf.estimate(
                assumptions        = assumptions.dcf,
                fcf_base           = fcf_base,
                net_debt           = inputs.get("net_debt"),
                shares_outstanding = inputs.get("shares"),
                confidence_inputs  = inputs.get("data_confidence", 0.6),
            )
        except Exception:
            return ValuationResult(
                model_type=ValuationModelType.DCF,
                status=ValuationStatus.ERROR,
            )

    def _run_ddm(
        self, assumptions: ValuationAssumptions, inputs: Dict[str, Any]
    ) -> Optional[ValuationResult]:
        try:
            return self._ddm.estimate(
                assumptions        = assumptions.ddm,
                dividend_per_share = inputs.get("dividend_per_share"),
                payout_ratio       = inputs.get("payout_ratio"),
                earnings_per_share = inputs.get("eps"),
                confidence_inputs  = inputs.get("data_confidence", 0.55),
            )
        except Exception:
            return ValuationResult(
                model_type=ValuationModelType.DDM,
                status=ValuationStatus.ERROR,
            )

    def _run_rim(
        self, assumptions: ValuationAssumptions, inputs: Dict[str, Any]
    ) -> Optional[ValuationResult]:
        try:
            return self._rim.estimate(
                assumptions           = assumptions.rim,
                book_value_per_share  = inputs.get("book_value_per_share"),
                roe                   = inputs.get("roe"),
                confidence_inputs     = inputs.get("data_confidence", 0.55),
            )
        except Exception:
            return ValuationResult(
                model_type=ValuationModelType.RESIDUAL_INCOME,
                status=ValuationStatus.ERROR,
            )

    def _run_asset(
        self, inputs: Dict[str, Any], shares: Optional[float]
    ) -> Optional[ValuationResult]:
        try:
            return self._asset.estimate(
                total_assets       = inputs.get("total_assets"),
                total_liabilities  = inputs.get("total_liabilities"),
                shares_outstanding = shares,
                confidence_inputs  = inputs.get("data_confidence", 0.50),
            )
        except Exception:
            return ValuationResult(
                model_type=ValuationModelType.ASSET_BASED,
                status=ValuationStatus.ERROR,
            )

    def _run_relative(
        self,
        assumptions:    ValuationAssumptions,
        inputs:         Dict[str, Any],
        peer_snapshots: List[Any],
        sector:         Optional[str],
    ) -> Optional[ValuationResult]:
        try:
            rel_assumptions = assumptions.relative
            # Override with peer or sector targets if no explicit targets set
            if not any([
                rel_assumptions.target_pe,
                rel_assumptions.target_ev_ebitda,
                rel_assumptions.target_pb,
            ]):
                if peer_snapshots:
                    peer_multiples = self._peer.derive_peer_multiples(peer_snapshots)
                    from iios.investment.company.valuation.valuation_assumptions import (
                        RelativeValuationAssumptions,
                    )
                    rel_assumptions = RelativeValuationAssumptions(
                        target_pe        = peer_multiples.get("target_pe"),
                        target_ev_ebitda = peer_multiples.get("target_ev_ebitda"),
                        target_pb        = peer_multiples.get("target_pb"),
                        target_pfcf      = peer_multiples.get("target_pfcf"),
                        target_ev_sales  = peer_multiples.get("target_ev_sales"),
                    )
                elif sector:
                    benchmarks = get_sector_benchmarks(sector)
                    from iios.investment.company.valuation.valuation_assumptions import (
                        RelativeValuationAssumptions,
                    )
                    rel_assumptions = RelativeValuationAssumptions(
                        target_pe        = benchmarks.get("median_pe"),
                        target_ev_ebitda = benchmarks.get("median_ev_ebitda"),
                        target_pb        = benchmarks.get("median_pb"),
                        target_pfcf      = benchmarks.get("median_pfcf"),
                        target_ev_sales  = benchmarks.get("median_ev_sales"),
                    )

            return self._relative.estimate(
                assumptions           = rel_assumptions,
                earnings_per_share    = inputs.get("eps"),
                book_value_per_share  = inputs.get("book_value_per_share"),
                fcf_per_share         = inputs.get("fcf_per_share"),
                revenue_per_share     = inputs.get("revenue_per_share"),
                ebitda_per_share      = inputs.get("ebitda_per_share"),
                net_debt_per_share    = inputs.get("net_debt_per_share"),
                historical_pe         = inputs.get("historical_pe"),
                historical_pb         = inputs.get("historical_pb"),
                historical_ev_ebitda  = inputs.get("historical_ev_ebitda"),
                confidence_inputs     = inputs.get("data_confidence", 0.55),
            )
        except Exception:
            return ValuationResult(
                model_type=ValuationModelType.RELATIVE_PE,
                status=ValuationStatus.ERROR,
            )

    # ── Blending ───────────────────────────────────────────────────────────────

    @staticmethod
    def _blend(
        results:  List[Optional[ValuationResult]],
        weights:  Dict[str, float],
        currency: str = "INR",
    ) -> Optional[FairValueEstimate]:
        _MODEL_KEY = {
            ValuationModelType.DCF:             "dcf",
            ValuationModelType.DDM:             "ddm",
            ValuationModelType.RESIDUAL_INCOME: "residual_income",
            ValuationModelType.ASSET_BASED:     "asset_based",
            ValuationModelType.RELATIVE_PE:     "relative",
            ValuationModelType.RELATIVE_EV_EBITDA: "relative",
            ValuationModelType.RELATIVE_PB:     "relative",
            ValuationModelType.RELATIVE_EV_SALES: "relative",
            ValuationModelType.RELATIVE_PFCF:   "relative",
            ValuationModelType.BLENDED:         "blended",
            ValuationModelType.PLUGIN:          "dcf",   # plugin carries its own weight
        }
        valid: Dict[str, float] = {}
        weight_used: Dict[str, float] = {}
        contributing: List[str] = []

        for r in results:
            if r is None:
                continue
            if r.status != ValuationStatus.COMPUTED:
                continue
            if not r.intrinsic_value or r.intrinsic_value <= 0:
                continue
            key = _MODEL_KEY.get(r.model_type, "dcf")
            # Use model-level confidence as partial weight adjustment
            base_w  = weights.get(key, 0.0)
            adj_w   = base_w * r.confidence
            if adj_w > 0:
                if key in valid:
                    # Average same-key models (e.g. multiple relative sub-methods)
                    valid[key]       = (valid[key] + r.intrinsic_value) / 2.0
                    weight_used[key] = max(weight_used[key], adj_w)
                else:
                    valid[key]       = r.intrinsic_value
                    weight_used[key] = adj_w
                    contributing.append(r.model_type.value)

        if not valid:
            return None

        blended = weighted_average(valid, weight_used)

        val_range = build_valuation_range(results)
        if val_range is None:
            val_range = ValuationRange(
                low  = blended * 0.80,
                mid  = blended,
                high = blended * 1.20,
            )

        # Confidence: average of contributing model confidences
        avg_conf = sum(
            r.confidence for r in results
            if r and r.status == ValuationStatus.COMPUTED and r.intrinsic_value
        ) / max(1, len([r for r in results if r and r.status == ValuationStatus.COMPUTED]))

        return FairValueEstimate(
            intrinsic_value     = blended,
            value_range         = val_range,
            method              = "blended",
            model_weights_used  = {k: round(v, 4) for k, v in weight_used.items()},
            contributing_models = contributing,
            confidence          = clamp(avg_conf, 0, 1.0),
            currency            = currency,
            explanation         = [
                f"Blended from {len(contributing)} model(s): {', '.join(contributing)}",
                f"Intrinsic value: {blended:.2f} {currency}",
            ],
        )

    # ── Input extraction ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_inputs(
        fs:           Any,
        es:           Any,
        bqs:          Any,
        market_price: Optional[float],
        shares:       Optional[float],
        assumptions:  ValuationAssumptions,
        sector:       Optional[str],
    ) -> Dict[str, Any]:
        """
        Extract all financial inputs needed by models from the three snapshots.
        Returns a flat dict — never raises.
        """
        inputs: Dict[str, Any] = {"shares": shares, "sector": sector}

        def _r(obj: Any, key: str, default: Any = None) -> Any:
            """Safe dict/attr get from FinancialSnapshot.ratios or attributes."""
            if obj is None:
                return default
            if hasattr(obj, "ratios") and isinstance(obj.ratios, dict):
                v = obj.ratios.get(key)
                if v is not None:
                    return v
            return getattr(obj, key, default)

        # ── FinancialSnapshot ─────────────────────────────────────────────────
        total_assets      = getattr(fs, "total_assets", None) or _r(fs, "total_assets")
        total_equity      = getattr(fs, "total_equity", None) or _r(fs, "total_equity")
        revenue           = getattr(fs, "revenue", None)      or _r(fs, "revenue")

        inputs["total_assets"]       = total_assets
        inputs["total_equity"]       = total_equity
        inputs["revenue"]            = revenue

        # Total liabilities (assets - equity)
        if total_assets and total_equity:
            inputs["total_liabilities"] = total_assets - total_equity

        # Cash flow metrics
        cf = getattr(fs, "cashflow_metrics", None)
        fcf      = getattr(cf, "free_cash_flow", None) if cf else None
        capex    = getattr(cf, "capex", None)           if cf else None
        ocf      = getattr(cf, "operating_cash_flow", None) if cf else None
        ebitda   = _r(fs, "ebitda")

        inputs["fcf_base"]  = fcf
        inputs["ocf"]       = ocf
        inputs["capex"]     = capex
        inputs["ebitda"]    = ebitda

        # Income metrics
        im = getattr(fs, "income_metrics", None)
        inputs["net_income"] = getattr(im, "net_income", None) if im else None

        # BS metrics
        bsm = getattr(fs, "balance_sheet_metrics", None)
        total_debt = getattr(bsm, "total_debt", None) if bsm else None
        cash       = getattr(bsm, "cash_and_equivalents", None) if bsm else None
        inputs["total_debt"] = total_debt
        inputs["cash"]       = cash

        # Net debt
        if assumptions.net_debt_override is not None:
            inputs["net_debt"] = assumptions.net_debt_override
        elif total_debt is not None and cash is not None:
            inputs["net_debt"] = total_debt - cash
        elif total_debt is not None:
            inputs["net_debt"] = total_debt
        else:
            inputs["net_debt"] = None

        # ── Per-share derivations ─────────────────────────────────────────────
        if shares and shares > 0:
            inputs["fcf_per_share"]     = fcf / shares     if fcf     else None
            inputs["revenue_per_share"] = revenue / shares  if revenue else None
            inputs["ebitda_per_share"]  = ebitda / shares   if ebitda  else None
            net_debt_val = inputs.get("net_debt")
            inputs["net_debt_per_share"] = net_debt_val / shares if net_debt_val else None
            if total_equity and total_equity > 0:
                inputs["book_value_per_share"] = total_equity / shares

        # ── EarningsSnapshot ──────────────────────────────────────────────────
        history_depth = getattr(es, "history_depth", 0)
        inputs["history_depth"] = history_depth

        prof = getattr(es, "profitability", None)
        inputs["roe"]        = getattr(prof, "roe",  None) if prof else None
        inputs["roic"]       = getattr(prof, "roic", None) if prof else None
        inputs["net_margin"] = getattr(prof, "net_margin", None) if prof else None

        risk = getattr(es, "risk", None)
        if risk:
            fcf_vol = getattr(risk, "margin_volatility", None)
            inputs["fcf_stability"] = max(0.0, 1.0 - (fcf_vol or 0.5)) if fcf_vol is not None else 0.5

        trend = getattr(es, "trend", None)
        inputs["eps_growth"] = getattr(trend, "cagr_eps", None) if trend else None

        # EPS from net_income / shares
        ni = inputs.get("net_income")
        if ni and shares and shares > 0:
            inputs["eps"] = ni / shares
        else:
            inputs["eps"] = None

        # Dividend — look for ratios["dividend_per_share"]
        inputs["dividend_per_share"] = _r(fs, "dividend_per_share")
        inputs["payout_ratio"]       = _r(fs, "dividend_payout_ratio")

        # Historical PE/PB for relative valuation
        # (Ideally sourced from the ValuationHistory, but not available here)
        inputs["historical_pe"]       = None
        inputs["historical_pb"]       = None
        inputs["historical_ev_ebitda"] = None

        # Data confidence from earnings quality
        quality = getattr(es, "quality", None)
        inputs["data_confidence"] = clamp(
            (getattr(quality, "overall_score", 50) / 100.0) * 0.7 + 0.2, 0.1, 0.9
        ) if quality else 0.5

        return inputs

    # ── Assumption management ─────────────────────────────────────────────────

    def _load_or_default(self, ticker: str) -> ValuationAssumptions:
        cached = self._asm.get_latest(ticker)
        if cached:
            return cached
        defaults = ValuationAssumptions()
        self._asm.store(ticker, defaults, source="default")
        return defaults
