"""
knowledge_authority/knowledge_decision_pipeline.py
====================================================
KDA — Knowledge Decision Authority Pipeline

SINGLE ORCHESTRATION BOUNDARY for the complete Knowledge Intelligence loop.

Architecture:
  SCANNER SIGNAL
      ↓
  KLP OBSERVATION         (already wired via klp_evaluator)
      ↓
  HBE HISTORICAL EVIDENCE (lazy-loaded, once per day)
      ↓
  KFE MULTI-ANGLE FUSION  (lazy-loaded pool, once per day)
      ↓
  KDA KNOWLEDGE DECISION  (INTELLIGENCE AUTHORITY)
      ↓
  KDA LEDGER              (append-only, thread-safe)
      ↓
  [EOD] KDA OUTCOME ENGINE + COMPARATIVE + AUTHORITY REPORT

AUTHORITY CONTRACT:
  KDA is the intelligence authority for signal direction.
  When KDA returns KNOWLEDGE_BUY/SELL, the signal enters the production path
  regardless of StrategyLab's decision (StrategyLab is SHADOW/CONTEXT).
  Risk layers (CapitalRisk, RiskGuardian) remain independent safety veto.

SAFETY CONTRACT (never violated):
  broker_calls == 0
  orders == 0
  modifications == 0
  execution_authority == False  ← paper/live execution is controlled by OrderManager
  PAPER_TRADING state never read or set here

FAILURE ISOLATION:
  Any exception in the Knowledge pipeline returns KNOWLEDGE_PIPELINE_ERROR.
  The production trading cycle is never interrupted.

INTRADAY SCHEDULE:
  run_knowledge_shadow(signal, market_context, strategy_info)
  → called once per scanner signal; orchestrator uses kda_decision for routing

EOD SCHEDULE:
  run_eod_knowledge_update(trading_date)
  → called once, AFTER KLP-002 outcome fill
"""
from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Data directory (overridable for tests)
# ─────────────────────────────────────────────────────────────────────────────

_ROOT     = Path(__file__).parent.parent
_DATA_DIR = _ROOT / "data"

# ─────────────────────────────────────────────────────────────────────────────
# Direction normalisation helper
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_dir(signal: Any) -> str:
    d = getattr(signal, "direction", "BUY")
    if hasattr(d, "value"):
        d = d.value
    d = str(d).upper()
    return "SELL" if d in ("SELL", "SHORT", "BEAR") else "BUY"


# ─────────────────────────────────────────────────────────────────────────────
# Sector lookup (mirrors HBE and KFE maps)
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL_SECTOR: Dict[str, str] = {
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "BANKBARODA": "BANK", "INDUSINDBK": "BANK", "AUBANK": "BANK",
    "BANDHANBNK": "BANK", "FEDERALBNK": "BANK", "PNB": "BANK",
    "HDFCAMC": "FINSERVICES", "ANGELONE": "FINSERVICES", "BAJAJFINSV": "FINSERVICES",
    "BAJFINANCE": "FINSERVICES", "MUTHOOTFIN": "FINSERVICES",
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "TECHM": "IT", "HCLTECH": "IT",
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "BPCL": "ENERGY", "HPCL": "ENERGY",
    "ADANIGREEN": "ENERGY", "NTPC": "ENERGY", "POWERGRID": "ENERGY",
    "TATAPOWER": "ENERGY", "NHPC": "ENERGY", "COALINDIA": "ENERGY",
    "NMDC": "METALS",
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
    "EICHERMOT": "AUTO", "HEROMOTOCO": "AUTO", "ASHOKLEY": "AUTO",
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA",
    "LUPIN": "PHARMA", "DIVISLAB": "PHARMA", "BIOCON": "PHARMA", "ALKEM": "PHARMA",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG", "TATACONSUM": "FMCG",
    "TATASTEEL": "METALS", "JSWSTEEL": "METALS", "HINDALCO": "METALS",
    "VEDL": "METALS", "APLAPOLLO": "METALS",
    "PRESTIGE": "REALTY", "DLF": "REALTY", "LODHA": "REALTY",
    "BHARTIARTL": "TELECOM",
    "ASIANPAINT": "CONSUMER", "HAVELLS": "CONSUMER", "TITAN": "CONSUMER",
    "FORTIS": "HEALTHCARE", "HDFCLIFE": "INSURANCE",
    "NIFTY": "INDEX", "BANKNIFTY": "INDEX",
}


def _sector(symbol: str) -> str:
    return _SYMBOL_SECTOR.get(symbol.upper().strip(), "UNKNOWN")


# ─────────────────────────────────────────────────────────────────────────────
# NSE ticker for yfinance (mirrors klp_outcome_engine pattern)
# ─────────────────────────────────────────────────────────────────────────────

_GLOBAL_SYMBOL_MAP = {
    "NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK",
    "NIFTY50": "^NSEI", "NIFTYBANK": "^NSEBANK",
}


def _yf_ticker(symbol: str) -> str:
    s = symbol.upper().strip()
    if s in _GLOBAL_SYMBOL_MAP:
        return _GLOBAL_SYMBOL_MAP[s]
    return s if s.endswith(".NS") else f"{s}.NS"


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV fetch helper (post-decision bars only, no lookahead)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_post_decision_bars(
    symbol: str,
    decision_date: str,
    horizon: int = 20,
) -> List[Any]:
    """
    Fetch daily OHLCV bars starting from T+1 after decision_date.
    Returns list of OHLCVBar objects.  Returns [] on any error.
    No lookahead: bars[0].date > decision_date always.
    """
    from knowledge_authority.kda_outcome_models import OHLCVBar
    try:
        import yfinance as yf
        from datetime import timedelta
        d0 = date.fromisoformat(decision_date)
        start = (d0 + timedelta(days=1)).isoformat()
        end_dt = d0 + timedelta(days=horizon + 10)
        ticker = _yf_ticker(symbol)
        df = yf.download(ticker, start=start, end=end_dt.isoformat(),
                         progress=False, auto_adjust=True, timeout=8)
        if df is None or df.empty:
            return []
        import pandas as _pd
        if isinstance(df.columns, _pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.droplevel(level=-1)
            df = df.loc[:, ~df.columns.duplicated()]
        bars = []
        for idx, row in df.iterrows():
            bars.append(OHLCVBar(
                date=str(idx.date()),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
            ))
        # Extra safety: strip any bars from decision_date or earlier
        bars = [b for b in bars if b.date > decision_date]
        return bars
    except Exception as exc:
        log.debug("[KDP-OHLCVFetch] %s %s: %s", symbol, decision_date, exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Risk simulation (no execution — query only)
# ─────────────────────────────────────────────────────────────────────────────

_MIN_RR_SHADOW = 2.0    # mirrors risk_control/risk_manager_ai.py MIN_RR_RATIO
_MIN_CONF_SHADOW = 6.0  # mirrors debate threshold floor


def _simulate_risk(signal: Any, kda_record: Any) -> Dict[str, Any]:
    """
    Simulate whether this signal would pass basic risk rules.
    SHADOW ONLY — no actual order submission.
    broker_calls = 0, orders = 0.
    """
    entry = float(getattr(signal, "entry_price", 0.0) or 0.0)
    stop  = float(getattr(signal, "stop_loss",   0.0) or 0.0)
    tgt   = float(getattr(signal, "target_price", 0.0) or 0.0)
    conf  = float(getattr(signal, "confidence",   0.0) or 0.0)
    rr    = float(getattr(signal, "risk_reward_ratio", 0.0) or 0.0)

    # Recompute RR from prices if available
    if entry > 0 and stop > 0 and abs(entry - stop) > 0:
        rr = round(abs(tgt - entry) / abs(entry - stop), 3)

    rejection = None
    if rr > 0 and rr < _MIN_RR_SHADOW:
        rejection = f"R:R {rr:.2f} < {_MIN_RR_SHADOW:.1f}"
    elif conf > 0 and conf < _MIN_CONF_SHADOW:
        rejection = f"confidence {conf:.1f} < {_MIN_CONF_SHADOW:.1f}"

    return {
        "would_allow": rejection is None,
        "rejection_reason": rejection,
        "rr_simulated": rr,
        "confidence": conf,
        "position_size_if_allowed": None,  # portfolio state unavailable at this point
        "broker_calls": 0,
        "orders": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Source staleness record
# ─────────────────────────────────────────────────────────────────────────────

def _market_behavior_staleness(data_dir: Path) -> Dict[str, Any]:
    """Report staleness of market_behavior.db for KFE LEADER_OUTCOME angle."""
    mb = data_dir / "market_behavior.db"
    if not mb.exists():
        return {"available": False, "data_age_days": None, "last_updated": None,
                "stale": True, "staleness_label": "ABSENT"}
    import os
    mtime = os.path.getmtime(str(mb))
    last_dt = datetime.fromtimestamp(mtime)
    age_days = (datetime.now() - last_dt).days
    stale = age_days > 2  # Saturday DB is always used through Monday
    return {
        "available": True,
        "data_age_days": age_days,
        "last_updated": last_dt.strftime("%Y-%m-%d"),
        "stale": stale,
        "staleness_label": "CURRENT" if age_days <= 2 else f"STALE_{age_days}D",
    }


# ─────────────────────────────────────────────────────────────────────────────
# KnowledgeDecisionPipeline
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeDecisionPipeline:
    """
    KDA-003 — Single orchestration boundary for the shadow Knowledge Intelligence loop.

    INTRADAY:
        kdp.run_knowledge_shadow(signal, market_context, strategy_info)
        → HBE read → KFE decision-time view → KDA shadow decision → KDA ledger

    EOD:
        kdp.run_eod_knowledge_update(trading_date)
        → KDA outcomes → comparison → authority report → knowledge feedback

    SAFETY: never raises, never calls broker/OrderManager, never modifies
    production decisions. broker_calls = 0, orders = 0 always.
    """

    def __init__(
        self,
        data_dir:   Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self._data_dir   = Path(data_dir)   if data_dir   else _DATA_DIR
        self._output_dir = Path(output_dir) if output_dir else _DATA_DIR / "klp" / "kda"

        # KDA decision components (stateless — safe to hold as instance)
        from .knowledge_decision_authority import KnowledgeDecisionAuthority
        from .kda_ledger                   import KDALedger
        from .kda_outcome_engine           import KDAOutcomeEngine
        from .kda_comparative              import KDAComparativeAnalyzer
        from .kda_authority_report         import KDAAuthorityReporter

        self._kda        = KnowledgeDecisionAuthority()
        self._ledger     = KDALedger(base_dir=self._output_dir)
        self._outcome_e  = KDAOutcomeEngine()
        self._comp       = KDAComparativeAnalyzer()
        self._reporter   = KDAAuthorityReporter(base_dir=self._output_dir)

        # Evidence components (lazy-loaded once per trading day)
        self._hbe                = None   # HistoricalBehaviourEngine
        self._hbe_loaded_date:   Optional[str] = None
        self._kfe                = None   # KnowledgeFusionEngine
        self._kfe_pool:          Optional[List] = None
        self._kfe_loaded_date:   Optional[str] = None
        self._source_inventory:  List = []

        # Safety invariants — never changed
        self.broker_calls  = 0
        self.orders        = 0

        # Thread safety
        self._lock = threading.RLock()

        log.info("[KDP] KnowledgeDecisionPipeline initialised. data_dir=%s", self._data_dir)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API: intraday shadow decision
    # ─────────────────────────────────────────────────────────────────────────

    def run_knowledge_shadow(
        self,
        signal:          Any,
        market_context:  Dict[str, Any],
        strategy_info:   Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete shadow Knowledge pipeline for one scanner signal.

        Parameters
        ----------
        signal          TradeSignal from EquityScannerAI
        market_context  Dict with keys: regime, vix, pcr, breadth, etc.
        strategy_info   Dict with keys: strategy_pass (bool), strategy_name (str),
                        strategy_score (float), strategy_rejection_reason (str)

        Returns
        -------
        Dict with shadow_only=True, execution_authority=False, broker_calls=0.
        Never raises — returns KNOWLEDGE_PIPELINE_ERROR on any exception.
        """
        try:
            return self._shadow_impl(signal, market_context, strategy_info or {})
        except Exception as exc:
            sym = getattr(signal, "symbol", "?")
            log.debug("[KDP] Shadow pipeline error for %s: %s", sym, exc)
            return {
                "status": "KNOWLEDGE_PIPELINE_ERROR",
                "error": str(exc),
                "symbol": sym,
                "shadow_only": True,
                "execution_authority": False,
                "broker_calls": 0,
                "orders": 0,
            }

    # ─────────────────────────────────────────────────────────────────────────
    # Public API: EOD knowledge update
    # ─────────────────────────────────────────────────────────────────────────

    def run_eod_knowledge_update(
        self,
        trading_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        EOD update: fill KDA outcomes → compare → generate authority report.

        Parameters
        ----------
        trading_date  "YYYY-MM-DD" of today's trading session. Defaults to today.

        Returns
        -------
        Dict summary. Never raises — returns KNOWLEDGE_PIPELINE_ERROR on exception.
        """
        try:
            return self._eod_impl(trading_date or date.today().isoformat())
        except Exception as exc:
            log.debug("[KDP] EOD update error: %s", exc)
            return {
                "status": "KNOWLEDGE_PIPELINE_ERROR",
                "error": str(exc),
                "broker_calls": 0,
                "orders": 0,
            }

    # ─────────────────────────────────────────────────────────────────────────
    # Public API: force refresh evidence (call at EOD or on-demand)
    # ─────────────────────────────────────────────────────────────────────────

    def refresh_evidence_cache(self) -> Dict[str, Any]:
        """Force reload of HBE and KFE pools. Thread-safe."""
        try:
            with self._lock:
                self._hbe = None
                self._hbe_loaded_date = None
                self._kfe = None
                self._kfe_pool = None
                self._kfe_loaded_date = None
            hbe = self._get_or_load_hbe()
            kfe, pool = self._get_or_load_kfe()
            return {
                "status": "OK",
                "hbe_outcomes": hbe.get_outcome_count(),
                "kfe_pool_size": len(pool),
                "broker_calls": 0,
                "orders": 0,
            }
        except Exception as exc:
            return {"status": "KNOWLEDGE_PIPELINE_ERROR", "error": str(exc)}

    # ─────────────────────────────────────────────────────────────────────────
    # Intraday implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _shadow_impl(
        self,
        signal:        Any,
        market_ctx:    Dict[str, Any],
        strategy_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        sym       = str(getattr(signal, "symbol", "UNKNOWN")).upper().strip()
        direction = _normalise_dir(signal)
        today     = date.today().isoformat()

        # ── Step 1: Build observation dict ───────────────────────────────────
        obs = self._build_observation(signal, market_ctx)

        # ── Step 2: HBE — get behaviour profile (READ only) ──────────────────
        hbe = self._get_or_load_hbe()
        regime    = str(market_ctx.get("regime") or "").upper() or None
        entry_px  = float(getattr(signal, "entry_price", 0.0) or 0.0)
        atr_pct   = obs.get("atr_pct")
        conf_val  = obs.get("scanner_confidence")
        v1_score  = obs.get("candidate_score", 0.0)

        profile = hbe.get_behaviour_profile(
            symbol=sym,
            direction=direction,
            regime=regime,
            query_atr_pct=atr_pct,
            query_confidence=conf_val,
            v1_score=v1_score,
            query_entry=entry_px if entry_px > 0 else None,
        )
        behaviour = profile.metrics  # BehaviourMetrics — what KDA expects

        # ── Step 3: KFE — build fusion record + get multi-angle view ─────────
        kfe, pool = self._get_or_load_kfe()
        kfe_record = self._build_fusion_record(signal, market_ctx)
        angle_view = kfe.analyse_record(kfe_record, pool)

        # ── Step 4: Source staleness check ───────────────────────────────────
        staleness = _market_behavior_staleness(self._data_dir)
        if staleness["stale"]:
            log.debug(
                "[KDP] market_behavior.db is %s — LEADER_OUTCOME angle uses stale data",
                staleness["staleness_label"],
            )

        # ── Step 5: KDA evaluate (shadow mode) ───────────────────────────────
        # Ensure strategy_info has "status" key for _parse_strategy_context
        _strat_for_kda = dict(strategy_info)  # shallow copy — never mutate caller's dict
        if "status" not in _strat_for_kda:
            _sp = _strat_for_kda.get("strategy_pass")
            _strat_for_kda["status"] = (
                "PASS"   if _sp is True  else
                "REJECT" if _sp is False else
                str(_strat_for_kda.get("strategy_pass_status", "UNKNOWN")).upper()
            )
        kda_record = self._kda.evaluate(
            observation=obs,
            angle_view=angle_view,
            behaviour=behaviour,
            strategy_context=_strat_for_kda,
            market_context=market_ctx,
        )

        # ── Step 6: Simulate risk (no execution) ─────────────────────────────
        risk_sim = _simulate_risk(signal, kda_record)

        # ── Step 7: Persist to ledger ─────────────────────────────────────────
        recorded = self._ledger.record(kda_record)
        if not recorded:
            log.debug("[KDP] Duplicate KDA decision_id %s — not recorded again",
                      kda_record.decision_id)

        # ── Step 8: Return immutable shadow result ────────────────────────────
        dec_val = kda_record.decision.value if hasattr(kda_record.decision, "value") else str(kda_record.decision)
        aut_val = kda_record.authority.value if hasattr(kda_record.authority, "value") else str(kda_record.authority)
        ev_val  = kda_record.evidence_state.value if hasattr(kda_record.evidence_state, "value") else str(kda_record.evidence_state)

        log.info(
            "[KDA-SHADOW] %s %s | decision=%s authority=%s evidence=%s "
            "ess=%.1f hbe_level=%d kfe_angles=%d strategy_pass=%s risk_would_allow=%s",
            sym, direction, dec_val, aut_val, ev_val,
            float(kda_record.effective_sample_size or 0.0),
            int(behaviour.evidence_level),
            len(angle_view.angles),
            strategy_info.get("strategy_pass"),
            risk_sim["would_allow"],
        )

        return {
            "status": "OK",
            "shadow_only": True,
            "execution_authority": False,
            "broker_calls": 0,
            "orders": 0,
            "decision_id": kda_record.decision_id,
            "opportunity_id": kda_record.opportunity_id,
            "symbol": sym,
            "direction": direction,
            "trading_date": today,
            # KDA result
            "kda_decision": dec_val,
            "kda_authority": aut_val,
            "knowledge_authority_score": kda_record.knowledge_authority,
            "evidence_state": ev_val,
            "evidence_level": behaviour.evidence_level,
            "effective_sample_size": kda_record.effective_sample_size,
            "knowledge_target": kda_record.target,
            "knowledge_stop": kda_record.stop_loss,
            "expected_days_p50": kda_record.expected_days_p50,
            "supporting_angles": kda_record.supporting_angles,
            "contradicting_angles": kda_record.contradicting_angles,
            "fallback_used": kda_record.fallback_used,
            # Strategy comparison context
            "strategy_pass": strategy_info.get("strategy_pass"),
            "strategy_name": strategy_info.get("strategy_name"),
            "strategy_rejection_reason": strategy_info.get("strategy_rejection_reason"),
            # Risk simulation
            "risk_would_allow": risk_sim["would_allow"],
            "risk_rejection_reason": risk_sim["rejection_reason"],
            "rr_simulated": risk_sim["rr_simulated"],
            # Evidence metadata
            "hbe_evidence_level": behaviour.evidence_level,
            "hbe_ess": behaviour.effective_sample_size,
            "hbe_stability": behaviour.stability_status,
            "hbe_target_hit_prob": behaviour.target_hit_probability,
            "kfe_pool_size": len(pool),
            "kfe_angles_count": len(angle_view.angles),
            "kfe_overall_signal": angle_view.overall_signal,
            "market_behavior_staleness": staleness["staleness_label"],
            "recorded_to_ledger": recorded,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # EOD implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _eod_impl(self, trading_date: str) -> Dict[str, Any]:
        """Full EOD pipeline: outcomes → comparison → authority report → feedback."""

        # ── Step 1: Refresh HBE (picks up today's KLP-002 outcomes) ─────────
        hbe = self._reload_hbe()
        hbe_outcomes = hbe.get_outcome_count()
        log.info("[KDP-EOD] HBE refreshed. outcomes=%d", hbe_outcomes)

        # ── Step 2: Reload KFE pool (picks up new rejection records) ─────────
        kfe, pool = self._reload_kfe()
        log.info("[KDP-EOD] KFE pool reloaded. records=%d", len(pool))

        # ── Step 3: Load today's KDA decisions from ledger ───────────────────
        decisions = self._ledger.load_decisions(trading_date)
        if not decisions:
            log.info("[KDP-EOD] No KDA decisions found for %s. EOD update skipped.",
                     trading_date)
            return {
                "status": "OK",
                "trading_date": trading_date,
                "decisions_found": 0,
                "decisions_processed": 0,
                "outcomes_evaluated": 0,
                "comparisons_done": 0,
                "authority_report": None,
                "hbe_outcomes": hbe_outcomes,
                "kfe_pool_size": len(pool),
                "broker_calls": 0,
                "orders": 0,
            }

        log.info("[KDP-EOD] Processing %d KDA decisions for %s", len(decisions), trading_date)

        # ── Step 4: Evaluate KDA outcomes ────────────────────────────────────
        from .kda_models import KDADecisionRecord
        from .kda_outcome_models import KDAOutcomeRecord

        outcomes: List[KDAOutcomeRecord] = []
        outcomes_evaluated = 0

        for rec_dict in decisions:
            try:
                kda_rec = KDADecisionRecord.from_dict(rec_dict)
                sym = kda_rec.symbol or rec_dict.get("symbol", "?")
                bars = _fetch_post_decision_bars(sym, trading_date, horizon=20)
                if not bars:
                    log.debug("[KDP-EOD] No bars for %s — outcome deferred", sym)
                    continue
                entry_px = float(rec_dict.get("entry_price") or 0.0) or None
                outcome = self._outcome_e.evaluate(
                    decision=kda_rec,
                    bars=bars,
                    entry_price=entry_px,
                    trading_date=trading_date,
                )
                outcomes.append(outcome)
                outcomes_evaluated += 1
            except Exception as exc:
                log.debug("[KDP-EOD] Outcome evaluation error for %s: %s",
                          rec_dict.get("symbol", "?"), exc)

        # ── Step 5: Comparative analysis ─────────────────────────────────────
        comparison_records = []
        comparisons_done = 0

        from .kda_comparative import KDAComparativeAnalyzer as _Comp

        for rec_dict in decisions:
            try:
                kda_rec = KDADecisionRecord.from_dict(rec_dict)
                # strategy_status: derive from stored StrategyContext (serialised as nested dict)
                _strat_ctx_d = rec_dict.get("strategy_context") or {}
                _strat_status_raw = _strat_ctx_d.get("status", "") or ""
                strategy_status = (
                    "PASS"   if _strat_status_raw.upper() == "PASS"   else
                    "REJECT" if _strat_status_raw.upper() == "REJECT" else
                    None
                )
                # find matching outcome
                matching_out = next(
                    (o for o in outcomes if o.decision_id == kda_rec.decision_id), None
                )
                outcome_dict = matching_out.as_dict() if matching_out is not None else None
                # strategy_status: "PASS" / "REJECT" — derived from stored context
                strategy_status_str = (
                    "PASS" if str(strategy_status).upper() in ("PASS", "TRUE", "1")
                    else "REJECT" if strategy_status is not None
                    else None
                )
                comp = self._comp.compare(
                    kda_record=kda_rec,
                    strategy_status=strategy_status_str,
                    outcome=outcome_dict,
                    trading_date=trading_date,
                )
                comparison_records.append(comp)
                comparisons_done += 1
            except Exception as exc:
                log.debug("[KDP-EOD] Comparison error for %s: %s",
                          rec_dict.get("symbol", "?"), exc)

        # ── Step 6: Authority report ──────────────────────────────────────────
        authority_report = None
        try:
            report = self._reporter.generate_report(
                outcomes=outcomes,
                source_contributions=self._source_inventory or None,
            )
            self._reporter.save(report)
            authority_report = {
                "authority_status": report.authority_status,
                "direction_accuracy": report.direction_accuracy,
                "target_hit_rate": report.target_hit_rate,
                "total_decisions": report.total_decisions,
            }
            log.info(
                "[KDP-EOD] Authority report: status=%s accuracy=%.1f%% n=%d",
                report.authority_status,
                float(report.direction_accuracy or 0.0) * 100,
                report.total_decisions,
            )
        except Exception as exc:
            log.debug("[KDP-EOD] Authority report error: %s", exc)

        # ── Step 7: Knowledge feedback (HBE re-evaluation trigger) ───────────
        # The HBE will be reloaded on the NEXT intraday cycle to pick up new data.
        # No direct model weight overwriting — append-only evidence.
        with self._lock:
            self._hbe_loaded_date = None   # force reload next cycle
            self._kfe_loaded_date = None   # force reload next cycle

        if comparison_records:
            summary = _Comp.summarize(comparison_records)
            log.info(
                "[KDP-EOD] Comparison summary: kda_accuracy=%.1f%% "
                "overrules=%d/%d comparisons=%d",
                float(summary.get("kda_direction_accuracy", 0) or 0) * 100,
                summary.get("kda_successful_overrules", 0),
                summary.get("kda_overrule_total", 0),
                comparisons_done,
            )
        else:
            summary = {}

        return {
            "status": "OK",
            "trading_date": trading_date,
            "decisions_found": len(decisions),
            "decisions_processed": len(decisions),
            "outcomes_evaluated": outcomes_evaluated,
            "comparisons_done": comparisons_done,
            "authority_report": authority_report,
            "comparison_summary": summary,
            "hbe_outcomes": hbe_outcomes,
            "kfe_pool_size": len(pool),
            "knowledge_feedback_triggered": True,
            "broker_calls": 0,
            "orders": 0,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Evidence loading helpers (lazy, once per day)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_or_load_hbe(self) -> Any:
        today = date.today().isoformat()
        with self._lock:
            if self._hbe is None or self._hbe_loaded_date != today:
                return self._reload_hbe()
            return self._hbe

    def _reload_hbe(self) -> Any:
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        hbe = HistoricalBehaviourEngine(data_dir=self._data_dir / "klp")
        n = hbe.load_outcomes()
        with self._lock:
            self._hbe = hbe
            self._hbe_loaded_date = date.today().isoformat()
        log.info("[KDP] HBE loaded %d completed outcomes", n)
        return hbe

    def _get_or_load_kfe(self) -> Tuple[Any, List]:
        today = date.today().isoformat()
        with self._lock:
            if self._kfe is None or self._kfe_loaded_date != today:
                return self._reload_kfe()
            return self._kfe, self._kfe_pool

    def _reload_kfe(self) -> Tuple[Any, List]:
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import (
            KnowledgeFusionEngine,
        )
        kfe  = KnowledgeFusionEngine(data_dir=self._data_dir)
        pool = kfe.load_fusion_records()
        inv  = kfe.build_source_inventory()
        staleness = _market_behavior_staleness(self._data_dir)

        with self._lock:
            self._kfe            = kfe
            self._kfe_pool       = pool
            self._kfe_loaded_date = date.today().isoformat()
            self._source_inventory = [i.as_dict() for i in inv]

        log.info(
            "[KDP] KFE loaded %d fusion records, %d sources. "
            "market_behavior: %s",
            len(pool), len(inv), staleness["staleness_label"],
        )
        return kfe, pool

    # ─────────────────────────────────────────────────────────────────────────
    # Signal → observation dict conversion
    # ─────────────────────────────────────────────────────────────────────────

    def _build_observation(
        self,
        signal:     Any,
        market_ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        sym   = str(getattr(signal, "symbol", "UNKNOWN")).upper().strip()
        direction = _normalise_dir(signal)
        entry = float(getattr(signal, "entry_price", 0.0) or 0.0)
        atr   = float(getattr(signal, "atr", 0.0) or 0.0)
        return {
            "symbol": sym,
            "direction": direction,
            "entry_price": entry,
            "atr": atr,
            "atr_pct": round(atr / entry * 100, 4) if entry > 0 else 0.0,
            "scanner_confidence": float(getattr(signal, "confidence", 0.0) or 0.0),
            "candidate_score": float(getattr(signal, "candidate_score", 0.0) or 0.0),
            "v1_score": float(getattr(signal, "candidate_score", 0.0) or 0.0),
            "scanner_target": float(getattr(signal, "target_price", 0.0) or 0.0),
            "scanner_stop": float(getattr(signal, "stop_loss", 0.0) or 0.0),
            "risk_reward_ratio": float(getattr(signal, "risk_reward_ratio", 0.0) or 0.0),
            "expected_move_pct": float(getattr(signal, "expected_move_pct", 0.0) or 0.0),
            "setup_type": str(getattr(signal, "setup_type", "") or ""),
            "strategy_name": str(getattr(signal, "strategy_name", "") or ""),
            "obs_regime": str(market_ctx.get("regime") or ""),
            "obs_sector": _sector(sym),
            "opportunity_id": str(getattr(signal, "opportunity_id", "") or ""),
            "no_lookahead": True,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Signal → KFE fusion record conversion
    # ─────────────────────────────────────────────────────────────────────────

    def _build_fusion_record(
        self,
        signal:     Any,
        market_ctx: Dict[str, Any],
    ) -> Any:
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord
        sym       = str(getattr(signal, "symbol", "UNKNOWN")).upper().strip()
        direction = _normalise_dir(signal)
        entry     = float(getattr(signal, "entry_price", 0.0) or 0.0)
        atr       = float(getattr(signal, "atr", 0.0) or 0.0)

        return KnowledgeFusionRecord(
            fusion_id=f"SHADOW_{sym}_{date.today().isoformat()}_{direction}_{uuid.uuid4().hex[:6]}",
            trading_date=date.today().isoformat(),
            symbol=sym,
            direction=direction,
            sector=_sector(sym),
            scanner_confidence=float(getattr(signal, "confidence", 0.0) or 0.0),
            candidate_score=float(getattr(signal, "candidate_score", 0.0) or 0.0),
            knowledge_score=float(getattr(signal, "candidate_score", 0.0) or 0.0),
            atr_pct=round(atr / entry * 100, 4) if entry > 0 else None,
            regime=str(market_ctx.get("regime") or "").upper() or None,
            vix=market_ctx.get("vix"),
            pcr=market_ctx.get("pcr"),
            breadth=market_ctx.get("breadth"),
            decision_confidence=float(getattr(signal, "confidence", 0.0) or 0.0),
            final_decision="SCANNER_CANDIDATE",
            outcome_available=False,
            no_lookahead=True,
            source_ids=["SCANNER_SIGNAL"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Singleton access (mirrors other Knowledge components)
# ─────────────────────────────────────────────────────────────────────────────

_KDP_INSTANCE: Optional["KnowledgeDecisionPipeline"] = None
_KDP_LOCK = threading.Lock()


def get_knowledge_pipeline(
    data_dir:   Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> "KnowledgeDecisionPipeline":
    """Return the process-scoped singleton KnowledgeDecisionPipeline."""
    global _KDP_INSTANCE
    with _KDP_LOCK:
        if _KDP_INSTANCE is None:
            _KDP_INSTANCE = KnowledgeDecisionPipeline(
                data_dir=data_dir,
                output_dir=output_dir,
            )
    return _KDP_INSTANCE



