"""
Capital Risk Engine — Meta-Control Layer
==========================================
Controls dynamic capital exposure and enforces institutional-grade
position sizing.

Pipeline position:
    Strategy Lab
        ↓
    Capital Risk Engine   ← THIS MODULE
        ↓
    Risk Control

Key functions
─────────────
1. Market-condition-based portfolio exposure limits
   • Bull Trend  → deploy up to 80% of capital
   • Range       → 50%
   • Bear        → 30%
   • Volatile    → 40%  (need room for hedges)

2. VIX override ceiling (hard limit regardless of regime)
   • VIX > 35  → 10%  (crash mode)
   • VIX > 28  → 25%
   • VIX > 22  → 40%
   • VIX > 18  → 65%

3. Drawdown-based exposure reduction
   • >10% DD → 25% of normal    (halt recovery mode)
   • > 7% DD → 50% of normal
   • > 4% DD → 75% of normal

4. Per-strategy capital bucket allocation

5. Institutional position sizing formula:
       Position Size = Risk Amount / Stop Loss Distance
   where Risk Amount = Strategy Budget × MAX_RISK_PER_TRADE_PCT
"""

from __future__ import annotations

import json as _json
import os as _os
from datetime import datetime as _dt
from typing import Dict, List, Optional, Tuple

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal
from models.portfolio    import Portfolio
from config import TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT
from utils import get_logger

log = get_logger(__name__)

# ── Daily EXPOSURE_CAP rejection accumulator (reset at midnight) ───────────
_EXPOSURE_REJECTIONS_TODAY: List[dict] = []
_EXPOSURE_REJECTIONS_DATE: str = ""
# ── Per-cycle EXPOSURE_CAP rejection accumulator (reset each allocate call) ─
_EXPOSURE_REJECTIONS_LAST_CYCLE: List[dict] = []

def _reset_exposure_accumulator() -> None:
    """Reset daily accumulator if date has changed."""
    global _EXPOSURE_REJECTIONS_TODAY, _EXPOSURE_REJECTIONS_DATE
    today = _dt.now().strftime("%Y-%m-%d")
    if _EXPOSURE_REJECTIONS_DATE != today:
        _EXPOSURE_REJECTIONS_TODAY = []
        _EXPOSURE_REJECTIONS_DATE = today

def get_daily_exposure_rejections() -> List[dict]:
    """Return today's EXPOSURE_CAP rejection records (non-destructive read)."""
    _reset_exposure_accumulator()
    return list(_EXPOSURE_REJECTIONS_TODAY)

def get_last_cycle_exposure_rejections() -> List[dict]:
    """Return the most recent cycle's heat-rejected signal records (non-destructive read)."""
    return list(_EXPOSURE_REJECTIONS_LAST_CYCLE)

# ── Regime → max deployment fraction ──────────────────────────────────────
_EXPOSURE_MAP: Dict[str, float] = {
    RegimeLabel.BULL_TREND.value:   0.80,
    RegimeLabel.RANGE_MARKET.value: 0.50,
    RegimeLabel.BEAR_MARKET.value:  0.30,
    RegimeLabel.VOLATILE.value:     0.40,
}

# ── VIX ceiling overrides (evaluated top-to-bottom; first match wins) ──────
_VIX_CEILINGS: List[Tuple[float, float]] = [
    (35.0, 0.10),   # Crash
    (28.0, 0.25),   # Extreme panic
    (22.0, 0.40),   # High fear
    (18.0, 0.65),   # Elevated
    ( 0.0, 1.00),   # Normal — no restriction
]

# ── Drawdown reducers (evaluated top-to-bottom; first match wins) ──────────
_DRAWDOWN_REDUCERS: List[Tuple[float, float]] = [
    (0.10, 0.25),   # >10% DD → 25% of deployable
    (0.07, 0.50),   # > 7% DD → 50%
    (0.04, 0.75),   # > 4% DD → 75%
    (0.00, 1.00),   # No drawdown → full deployment
]

# ── Per-strategy capital share (fraction of deployable capital) ────────────
# These represent the maximum slice per strategy type.
_STRATEGY_SHARE: Dict[str, float] = {
    "Breakout_Volume":          0.28,
    "Momentum_Retest":          0.18,
    "Trend_Pullback":           0.18,  # pullback-in-trend; same role as Momentum_Retest
    "Mean_Reversion":           0.22,
    "Bull_Call_Spread":         0.12,
    "Iron_Condor_Range":        0.18,
    "Hedging_Model":            0.10,
    "Short_Straddle_IV_Spike":  0.14,
    "Long_Straddle_Pre_Event":  0.08,
    "Futures_Basis_Arb":        0.14,
    "ETF_NAV_Arb":              0.12,
    "Equity_Breakout":          0.28,  # volatile-regime breakout; same profile as Breakout_Volume
    "Equity_Retest":            0.18,  # volatile-regime retest; same profile as Momentum_Retest
}
_DEFAULT_SHARE = 0.10   # fallback for genuinely unknown / unmapped strategies

# ── Evolved strategy → base strategy resolution ────────────────────────────
# Loaded lazily from data/evolved_strategies.json on first call.
# Maps variant name → base_strategy name (e.g. EDG_MOMENT_95_EE0000 → Breakout_Volume).
_EVOLVED_BASE_MAP: Dict[str, str] = {}
_EVOLVED_BASE_MAP_LOADED: bool = False
_EVOLVED_STRATEGIES_PATH: str = _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)),
    "..", "data", "evolved_strategies.json",
)


def _load_evolved_base_map() -> None:
    """Populate _EVOLVED_BASE_MAP once from evolved_strategies.json."""
    global _EVOLVED_BASE_MAP, _EVOLVED_BASE_MAP_LOADED
    if _EVOLVED_BASE_MAP_LOADED:
        return
    try:
        with open(_EVOLVED_STRATEGIES_PATH, "r", encoding="utf-8") as _f:
            _evolved = _json.load(_f)
        _EVOLVED_BASE_MAP = {
            name: params["base_strategy"]
            for name, params in _evolved.items()
            if params.get("approved") and params.get("base_strategy")
        }
        log.info(
            "[CREStrategyBaseMap] Loaded %d base-strategy mappings from evolved_strategies.json",
            len(_EVOLVED_BASE_MAP),
        )
    except FileNotFoundError:
        log.debug("[CREStrategyBaseMap] evolved_strategies.json not found — base map empty.")
    except Exception as _exc:
        log.warning("[CREStrategyBaseMap] Could not load evolved base map: %s", _exc)
    finally:
        _EVOLVED_BASE_MAP_LOADED = True

# ── Maximum number of simultaneous positions (capital-tier scaled) ─────────
# Imported from config so the pilot ₹10k limit (3) is enforced automatically.
try:
    from config import MAX_POSITIONS as _MAX_POSITIONS
except Exception:
    _MAX_POSITIONS = 8  # fallback if config import fails


class CapitalRiskEngine:
    """
    Institutional-grade dynamic capital allocation engine.

    Determines how much capital to deploy per cycle, allocates that
    capital across active strategies, and sizes each position using
    the risk-per-trade formula before the signal reaches Risk Control.
    """

    def __init__(self):
        log.info(f"[CapitalRiskEngine] Initialised. Total capital=\u20b9{TOTAL_CAPITAL:,.0f}")

    # ─────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────

    @staticmethod
    def _opportunity_profile_metadata(sig: TradeSignal) -> dict:
        """Return observational scanner/KDA fields for CRE diagnostics."""
        return {
            "scanner_score": getattr(sig, "scanner_score", 0.0),
            "kda_conviction": getattr(sig, "kda_conviction", None),
            "knowledge_authority_score": getattr(sig, "knowledge_authority_score", None),
            "kda_evidence_state": getattr(sig, "kda_evidence_state", None),
            "kda_target": getattr(sig, "kda_target", None),
            "kda_stop": getattr(sig, "kda_stop", None),
            "kda_horizon_p50": getattr(sig, "kda_horizon_p50", None),
        }

    def allocate(
        self,
        signals: List[TradeSignal],
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio] = None,
    ) -> List[TradeSignal]:
        """
        Apply dynamic capital allocation to strategy-assigned signals.

        Steps:
          1. Compute total deployable capital (regime + VIX + drawdown)
          2. Allocate per-strategy budget
          3. Size each position using institutional formula
          4. Enforce total exposure cap  (max _MAX_POSITIONS live)

        Returns signals with updated ``quantity``; signals that cannot
        be sized (zero budget, stop too tight, exposure cap) are dropped.
        """
        deployable = self._compute_deployable_capital(snapshot, portfolio)
        self._print_allocation_report(signals, snapshot, portfolio, deployable)

        result: List[TradeSignal] = []
        allocated_total = 0.0

        # ── [CREPositionCountAudit] — reconcile open position count ────
        try:
            _pf_positions = list(portfolio.positions.values()) if portfolio else []
            _pf_open      = len(_pf_positions)
            _pf_quarantine = sum(
                1 for p in _pf_positions
                if getattr(p, "governance_state", "") in ("QUARANTINED", "QUARANTINE")
                or getattr(p, "quarantined", False)
            )
            _pf_pending   = sum(
                1 for p in _pf_positions
                if getattr(p, "status", "") in ("PENDING", "SUBMITTED", "PARTIALLY_FILLED")
            )
            _pf_counted   = _pf_open   # CRE counts this-cycle result[], not portfolio
            _cre_available = max(0, _MAX_POSITIONS - _pf_open)
            log.info(
                "[CREPositionCountAudit] max_positions=%d "
                "positions_open=%d positions_quarantined=%d positions_pending=%d "
                "positions_counted_by_cre=0 positions_counted_by_order_manager=%d "
                "available_slots=%d cap_triggered=False rejected_due_to_cap=0 "
                "counting_method=this_cycle_result_len",
                _MAX_POSITIONS,
                _pf_open, _pf_quarantine, _pf_pending,
                _pf_counted, _cre_available,
            )
        except Exception as _pca_exc:
            log.debug("[CREPositionCountAudit] skipped: %s", _pca_exc)

        # ── [CapitalRiskDecision] rejection counters ────────────────────
        _crd_budget_rejected   = 0
        _crd_risk_rejected     = 0
        _crd_heat_rejected     = 0  # exposure cap
        _crd_sizing_rejected   = 0  # qty=0 from tight SL
        _crd_other_rejected    = 0
        _crd_signals_in        = len(signals)

        # ── Reset per-cycle accumulator ─────────────────────────────────
        global _EXPOSURE_REJECTIONS_LAST_CYCLE
        _EXPOSURE_REJECTIONS_LAST_CYCLE = []

        # ── Quality sort: rank signals by combined score BEFORE cap fires ──
        # Ensures MAX_POSITIONS cap discards weakest signals, not last-arrived.
        # Formula mirrors SmartExecution._combined_score (conf×0.55 + RR_norm×0.45).
        # conf is on 0–10 scale here; normalise to 0–1 before weighting.
        def _cre_quality_score(s: TradeSignal) -> float:
            _kda_directional = (
                getattr(s, "kda_decision", None) in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
                and getattr(s, "authorization_source", None) in ("KDA", "BOTH")
            )
            _kda_conviction = getattr(s, "kda_conviction", None)
            if _kda_directional and _kda_conviction is not None:
                _c = float(_kda_conviction) / 10.0
            elif _kda_directional:
                _c = 0.0
                log.debug(
                    "[CREQualitySort] KDA conviction unavailable for %s; "
                    "using neutral intelligence score.",
                    getattr(s, "symbol", "UNKNOWN"),
                )
            else:
                _c = float(getattr(s, "confidence", 0.0)) / 10.0
            _r = float(getattr(s, "risk_reward_ratio", 0.0))
            return _c * 0.55 + min(_r / 5.0, 1.0) * 0.45

        signals = sorted(signals, key=_cre_quality_score, reverse=True)

        try:
            _qs_top = signals[0] if signals else None
            log.info(
                "[CREQualitySort] signals_in=%d top_symbol=%s top_conf=%.2f top_rr=%.2f",
                len(signals),
                _qs_top.symbol if _qs_top else "NONE",
                float(getattr(_qs_top, "confidence", 0.0)) if _qs_top else 0.0,
                float(getattr(_qs_top, "risk_reward_ratio", 0.0)) if _qs_top else 0.0,
            )
        except Exception as _qs_exc:
            log.debug("[CREQualitySort] telemetry skipped: %s", _qs_exc)

        def _ec_record(sig, reason: str) -> dict:
            """Build a rejection record dict for a signal."""
            try:
                _n: dict = {}
                try:
                    _n = _json.loads(sig.notes or "{}")
                except Exception:
                    pass
                _rr = sig.risk_reward_ratio
                _sc = sig.confidence
                _cv = _n.get("conviction_score") or _sc / 10
                _se = _n.get("sector") or _n.get("sector_name") or "UNKNOWN"
                _rg = _n.get("regime") or "unknown"
                _rs = abs(sig.entry_price - sig.stop_loss)
                _rt = abs(sig.target_price - sig.entry_price)
                _rm = round(_rt / _rs, 2) if _rs > 0 else 0.0
                from config import MIN_CONFIDENCE_SCORE as _MCS
                return {
                    "symbol":                  sig.symbol,
                    "strategy":                sig.strategy_name,
                    "score":                   _sc,
                    "legacy_confidence":       _sc,
                    "conviction":              _cv,
                    "sector":                  _se,
                    "regime":                  _rg,
                    "R_multiple":              _rm,
                    "entry":                   sig.entry_price,
                    "stop":                    sig.stop_loss,
                    "target":                  sig.target_price,
                    "rr":                      _rr,
                    "would_pass_risk_control": (_sc >= _MCS and _rr >= 2.0),
                    "would_pass_simulation":   (_sc >= 6.0 and _rr >= 1.5),
                    "would_pass_debate":       (_sc >= 6.5),
                    "rejection_reason":        reason,
                    **self._opportunity_profile_metadata(sig),
                }
            except Exception:
                return {"symbol": getattr(sig, "symbol", "?"), "rejection_reason": reason,
                        "score": 0.0, "entry": 0.0, "stop": 0.0, "target": 0.0,
                        "rr": 0.0, "strategy": "", "conviction": 0.0, "sector": "?",
                        "regime": "?", "R_multiple": 0.0,
                        "would_pass_risk_control": False,
                        "would_pass_simulation": False,
                        "would_pass_debate": False}

        for _sig_idx, sig in enumerate(signals):
            if len(result) >= _MAX_POSITIONS:
                log.info("[CRE] Max position limit (%d) reached — remaining signals skipped.",
                         _MAX_POSITIONS)
                # ── [CRECapDecision] per-signal + final [CREPositionCountAudit] ──
                _cap_remaining = signals[_sig_idx:]
                _cap_rejected  = 0
                for _rem_sig in _cap_remaining:
                    _crd_heat_rejected += 1
                    _cap_rejected += 1
                    try:
                        _cap_rank = _sig_idx + (_cap_rejected)
                        _cap_qs   = round(_cre_quality_score(_rem_sig), 4)
                        log.info(
                            "[CRECapDecision] symbol=%s positions_counted=%d "
                            "max_positions=%d cap_triggered=True "
                            "reason=MAX_POSITIONS_CAP cap_rank=%d quality_score=%.4f",
                            _rem_sig.symbol, len(result), _MAX_POSITIONS,
                            _cap_rank, _cap_qs,
                        )
                        _rec = _ec_record(_rem_sig, "MAX_POSITIONS_CAP")
                        _EXPOSURE_REJECTIONS_TODAY.append(_rec)
                        _EXPOSURE_REJECTIONS_LAST_CYCLE.append(_rec)
                        log.info(
                            "[ExposureCapDecision] symbol=%s strategy=%s "
                            "score=%.2f conviction=%.2f sector=%s regime=%s "
                            "entry=%.2f stop=%.2f target=%.2f R_multiple=%.2f "
                            "would_pass_risk_control=%s would_pass_simulation=%s "
                            "would_pass_debate=%s",
                            _rec["symbol"], _rec["strategy"],
                            _rec["score"], _rec["conviction"],
                            _rec["sector"], _rec["regime"],
                            _rec["entry"], _rec["stop"], _rec["target"], _rec["R_multiple"],
                            _rec["would_pass_risk_control"],
                            _rec["would_pass_simulation"],
                            _rec["would_pass_debate"],
                        )
                    except Exception as _rem_exc:
                        log.debug("[CRECapDecision] remaining signal error: %s", _rem_exc)
                # Final [CREPositionCountAudit] with cap_triggered=True
                try:
                    _pf2 = list(portfolio.positions.values()) if portfolio else []
                    _pf2_open = len(_pf2)
                    log.info(
                        "[CREPositionCountAudit] max_positions=%d "
                        "positions_open=%d positions_quarantined=%d positions_pending=%d "
                        "positions_counted_by_cre=%d positions_counted_by_order_manager=%d "
                        "available_slots=%d cap_triggered=True rejected_due_to_cap=%d "
                        "counting_method=this_cycle_result_len",
                        _MAX_POSITIONS,
                        _pf2_open,
                        sum(1 for p in _pf2 if getattr(p, "governance_state", "") in ("QUARANTINED", "QUARANTINE") or getattr(p, "quarantined", False)),
                        sum(1 for p in _pf2 if getattr(p, "status", "") in ("PENDING", "SUBMITTED", "PARTIALLY_FILLED")),
                        len(result), _pf2_open,
                        max(0, _MAX_POSITIONS - len(result)),
                        _cap_rejected,
                    )
                except Exception as _pca2_exc:
                    log.debug("[CREPositionCountAudit] final skipped: %s", _pca2_exc)
                break

            # DTA-CRE-KDA-SURVIVAL-001: KDA_AUTHORITY is a pooled authority
            # label, not a trading style — the per-strategy diversification
            # share doesn't meaningfully apply to it (see audit). Existing
            # MAX_POSITIONS and exposure-cap checks below already protect
            # the portfolio independent of strategy_name, so KDA-authoritative
            # candidates are feasibility-checked against the full deployable
            # pool instead of an arbitrary strategy-family budget share.
            _kda_authoritative = (
                getattr(sig, "kda_decision", None) in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
                and getattr(sig, "authorization_source", None) in ("KDA", "BOTH")
                and getattr(sig, "kda_evidence_state", None) in ("VALIDATED", "DECISION_ELIGIBLE")
            )
            if _kda_authoritative:
                budget = deployable
            else:
                budget = self._strategy_budget(sig.strategy_name, deployable)
            qty    = self._size_position(sig, budget)

            if qty <= 0:
                sl_dist    = abs(sig.entry_price - sig.stop_loss)
                risk_amt   = budget * MAX_RISK_PER_TRADE_PCT
                _rej_reason = "ZERO_BUDGET" if budget < 1.0 else (
                    "SL_TOO_TIGHT" if sl_dist < 0.001 else
                    "ENTRY_ZERO" if sig.entry_price <= 0 else
                    "QTY_ZERO"
                )
                if _rej_reason == "ZERO_BUDGET":
                    _crd_budget_rejected += 1
                elif _rej_reason in ("SL_TOO_TIGHT", "QTY_ZERO", "ENTRY_ZERO"):
                    _crd_sizing_rejected += 1
                else:
                    _crd_other_rejected += 1
                log.info(
                    "[CapitalRiskDecision] symbol=%s strategy=%s "
                    "entry=%.2f allocated_budget=%.0f required_budget=%.0f "
                    "available_budget=%.0f position_size=%d risk_amount=%.0f "
                    "heat_usage=%.1f%% rejection_reason=%s",
                    sig.symbol, sig.strategy_name,
                    sig.entry_price, budget, budget,
                    deployable, qty, risk_amt,
                    (allocated_total / deployable * 100) if deployable else 0,
                    _rej_reason,
                )
                log.debug("[CRE] %s → qty=0 (budget=₹%s SL=%.2f) — skipped.",
                          sig.symbol, f"{budget:,.0f}", sig.stop_loss)
                continue

            trade_cost = qty * sig.entry_price
            if allocated_total + trade_cost > deployable * 1.05:
                _crd_heat_rejected += 1
                log.info(
                    "[CapitalRiskDecision] symbol=%s strategy=%s "
                    "entry=%.2f allocated_budget=%.0f required_budget=%.0f "
                    "available_budget=%.0f position_size=%d risk_amount=%.0f "
                    "heat_usage=%.1f%% rejection_reason=EXPOSURE_CAP_EXCEEDED",
                    sig.symbol, sig.strategy_name,
                    sig.entry_price, budget, trade_cost,
                    deployable - allocated_total, qty,
                    budget * MAX_RISK_PER_TRADE_PCT,
                    (allocated_total / deployable * 100) if deployable else 0,
                )

                # ── [ExposureCapDecision] — per-rejection quality audit ──────
                try:
                    _reset_exposure_accumulator()
                    from config import MIN_CONFIDENCE_SCORE as _MIN_CONF
                    _ec_rr = sig.risk_reward_ratio
                    _ec_notes: dict = {}
                    try:
                        _ec_notes = _json.loads(sig.notes or "{}")
                    except Exception:
                        pass
                    _ec_score     = sig.confidence
                    _ec_conviction= _ec_notes.get("conviction_score") or sig.confidence / 10
                    _ec_sector    = _ec_notes.get("sector") or _ec_notes.get("sector_name") or "UNKNOWN"
                    _ec_regime    = _ec_notes.get("regime") or "unknown"
                    _ec_r_stop    = abs(sig.entry_price - sig.stop_loss)
                    _ec_r_target  = abs(sig.target_price - sig.entry_price)
                    _ec_r_mult    = round(_ec_r_target / _ec_r_stop, 2) if _ec_r_stop > 0 else 0.0
                    # Projections: would this signal clear downstream gates?
                    #   risk_control: confidence >= MIN_CONFIDENCE_SCORE AND R:R >= 2.0
                    #   simulation:   confidence >= 6.0 AND R:R >= 1.5 (heuristic proxy)
                    #   debate:       confidence >= 6.5 (debate threshold)
                    _ec_pass_rc  = (_ec_score >= _MIN_CONF and _ec_rr >= 2.0)
                    _ec_pass_sim = (_ec_score >= 6.0 and _ec_rr >= 1.5)
                    _ec_pass_deb = (_ec_score >= 6.5)
                    log.info(
                        "[ExposureCapDecision] symbol=%s strategy=%s "
                        "score=%.2f conviction=%.2f sector=%s regime=%s "
                        "entry=%.2f stop=%.2f target=%.2f R_multiple=%.2f "
                        "would_pass_risk_control=%s would_pass_simulation=%s would_pass_debate=%s",
                        sig.symbol, sig.strategy_name,
                        _ec_score, _ec_conviction, _ec_sector, _ec_regime,
                        sig.entry_price, sig.stop_loss, sig.target_price, _ec_r_mult,
                        _ec_pass_rc, _ec_pass_sim, _ec_pass_deb,
                    )
                    _EXPOSURE_REJECTIONS_TODAY.append({
                        "symbol":                  sig.symbol,
                        "strategy":                sig.strategy_name,
                        "score":                   _ec_score,
                        "conviction":              _ec_conviction,
                        "sector":                  _ec_sector,
                        "regime":                  _ec_regime,
                        "R_multiple":              _ec_r_mult,
                        "entry":                   sig.entry_price,
                        "stop":                    sig.stop_loss,
                        "target":                  sig.target_price,
                        "rr":                      _ec_rr,
                        "would_pass_risk_control": _ec_pass_rc,
                        "would_pass_simulation":   _ec_pass_sim,
                        "would_pass_debate":       _ec_pass_deb,
                        "rejection_reason":        "EXPOSURE_CAP_EXCEEDED",
                        **self._opportunity_profile_metadata(sig),
                    })
                    _EXPOSURE_REJECTIONS_LAST_CYCLE.append(_EXPOSURE_REJECTIONS_TODAY[-1])
                except Exception as _ec_err:
                    log.debug("[ExposureCapDecision] audit skipped: %s", _ec_err)

                log.info("[CRE] %s skipped — total exposure limit reached (₹%s / ₹%s).",
                         sig.symbol, f"{allocated_total:,.0f}", f"{deployable:,.0f}")
                continue

            sig.quantity  = qty

            # JSON-aware metadata update — string concatenation onto JSON
            # corrupts the structured notes and destroys is_live, dte, etc.
            _notes_raw = sig.notes or "{}"
            try:
                _meta = _json.loads(_notes_raw)
            except Exception as _e:
                # Plain-text notes (equity / ETF arb signals) are not JSON.
                # Wrap the original text so it is not silently discarded.
                _was_plain_text = bool(_notes_raw) and not _notes_raw.strip().startswith("{")
                if _was_plain_text:
                    log.debug(
                        "[MetadataCorruptionDetected] module=capital_risk_engine  "
                        "symbol=%s  strategy=%s  notes_are_plain_text — wrapping in JSON",
                        sig.symbol, getattr(sig, "strategy_name", "UNKNOWN"),
                    )
                else:
                    log.info(
                        "[MetadataCorruptionDetected] module=capital_risk_engine  "
                        "symbol=%s  strategy=%s  error=%s  notes_snippet=%r "
                        "— wrapping in JSON to preserve content",
                        sig.symbol, getattr(sig, "strategy_name", "UNKNOWN"),
                        type(_e).__name__, _notes_raw[:80],
                    )
                _meta = {"original_notes": _notes_raw} if _notes_raw else {}
            log.debug(
                "[MetadataMutationAudit] module=capital_risk_engine  symbol=%s  "
                "event=before  keys=%s  is_live=%s",
                sig.symbol, sorted(_meta.keys()), _meta.get("is_live", "absent"),
            )
            _meta["cre_budget"] = int(budget)
            _meta["cre_qty"]    = qty
            sig.notes = _json.dumps(_meta)
            log.debug(
                "[MetadataMutationAudit] module=capital_risk_engine  symbol=%s  "
                "event=after  keys=%s  is_live=%s",
                sig.symbol, sorted(_meta.keys()), _meta.get("is_live", "absent"),
            )

            result.append(sig)
            allocated_total += trade_cost

        utilisation = (allocated_total / deployable * 100) if deployable else 0
        log.info(
            "[CRE] %d/%d signals sized. Deployable=₹%s  "
            "Allocated=₹%s (%.0f%% utilisation)",
            len(result), len(signals),
            f"{deployable:,.0f}", f"{allocated_total:,.0f}", utilisation,
        )

        # ── [CapitalRiskSummary] ────────────────────────────────────────
        _all_rej = _crd_budget_rejected + _crd_risk_rejected + _crd_heat_rejected + _crd_sizing_rejected + _crd_other_rejected
        _dom_reason = max(
            [("BUDGET", _crd_budget_rejected), ("RISK_AMOUNT", _crd_risk_rejected),
             ("EXPOSURE_CAP", _crd_heat_rejected), ("SL_SIZING", _crd_sizing_rejected),
             ("OTHER", _crd_other_rejected)],
            key=lambda x: x[1],
        )[0] if _all_rej > 0 else "NONE"
        log.info(
            "[CapitalRiskSummary] signals_in=%d signals_out=%d "
            "budget_rejected=%d risk_rejected=%d heat_rejected=%d "
            "sizing_rejected=%d other_rejected=%d "
            "dominant_rejection_reason=%s deployable=%.0f utilisation_pct=%.1f",
            _crd_signals_in, len(result),
            _crd_budget_rejected, _crd_risk_rejected, _crd_heat_rejected,
            _crd_sizing_rejected, _crd_other_rejected,
            _dom_reason, deployable, utilisation,
        )

        return result

    def deployable_capital(
        self,
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio] = None,
    ) -> float:
        """Public accessor - returns the deployable capital figure."""
        return self._compute_deployable_capital(snapshot, portfolio)

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _compute_deployable_capital(
        self,
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio],
    ) -> float:
        """Deployable = Total Capital x regime_exposure x vix_ceiling x dd_reducer."""
        regime_exposure = _EXPOSURE_MAP.get(snapshot.regime.value, 0.50)

        # VIX ceiling
        vix_ceiling = 1.00
        for threshold, ceiling in _VIX_CEILINGS:
            if snapshot.vix >= threshold:
                vix_ceiling = ceiling
                break

        # Use the more conservative of regime and VIX constraints
        base_exposure = min(regime_exposure, vix_ceiling)

        # Drawdown reducer
        dd_reducer = 1.00
        if portfolio:
            dd = portfolio.drawdown_pct
            for threshold, reducer in _DRAWDOWN_REDUCERS:
                if dd >= threshold:
                    dd_reducer = reducer
                    break

        return TOTAL_CAPITAL * base_exposure * dd_reducer

    def _strategy_budget(self, strategy_name: str, deployable: float) -> float:
        """Capital budget allocated to this specific strategy.

        Resolution order (capital-independent — percentage only):
          1. Exact name match in _STRATEGY_SHARE
          2. base_strategy from evolved_strategies.json → match in _STRATEGY_SHARE
          3. Prefix match in _STRATEGY_SHARE (backward compat: *_RSI_HiVol style)
          4. _DEFAULT_SHARE for genuinely unknown strategies
        """
        # 1. Exact match
        share = _STRATEGY_SHARE.get(strategy_name)

        # 2. Evolved variant: look up base_strategy from the JSON metadata
        if share is None:
            _load_evolved_base_map()
            _base = _EVOLVED_BASE_MAP.get(strategy_name)
            if _base:
                share = _STRATEGY_SHARE.get(_base)

        # 3. Prefix match (backward compat for variants like Breakout_Volume_RSI_HiVol)
        if share is None:
            for _pfx, _pfx_share in _STRATEGY_SHARE.items():
                if strategy_name.startswith(_pfx):
                    share = _pfx_share
                    break

        # 4. Fallback for genuinely unknown strategies
        if share is None:
            share = _DEFAULT_SHARE

        return deployable * share

    def _size_position(self, sig: TradeSignal, budget: float) -> int:
        """
        Risk/Safety feasibility check:
            qty = Risk Amount / Stop Distance

        Risk Amount = budget * MAX_RISK_PER_TRADE_PCT * knowledge_multiplier
        knowledge_multiplier = 0.5 + (confidence / 10) * 2.5   → range [0.5×, 3.0×]
          (non-KDA-authoritative signals only)
        Stop Distance = |entry - stop_loss|

        DTA-SIZING-AUTHORITY-004: for KDA-authoritative signals, knowledge_multiplier
        is fixed at 1.0 — this is a feasibility gate, not a second intelligence
        engine. The VIX/drawdown/regime throttle already lives in `budget`
        (deployable capital); no confidence- or conviction-weighted multiplier is
        needed here. PortfolioAllocationAI remains the sole quantity authority.

        Result is also capped so the notional cost <= strategy budget.
        """
        sl_distance = abs(sig.entry_price - sig.stop_loss)
        if sl_distance < 0.001 or sig.entry_price <= 0:
            return 0

        _kda_authoritative = (
            getattr(sig, "kda_decision", None) in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
            and getattr(sig, "authorization_source", None) in ("KDA", "BOTH")
            and getattr(sig, "kda_evidence_state", None) in ("VALIDATED", "DECISION_ELIGIBLE")
        )
        if _kda_authoritative:
            _k_mult = 1.0
        else:
            # Knowledge-driven risk scaling — confidence 0→10 maps to 0.5×→3.0× base
            _conf   = max(0.0, min(10.0, float(getattr(sig, "confidence", 5.0) or 5.0)))
            _k_mult = 0.5 + (_conf / 10.0) * 2.5
        risk_amount = budget * MAX_RISK_PER_TRADE_PCT * _k_mult
        log.debug(
            "[KnowledgeSizing] %s kda_authoritative=%s k_mult=%.2f risk_amt=%.2f sl_dist=%.2f",
            sig.symbol, _kda_authoritative, _k_mult, risk_amount, sl_distance,
        )
        qty_by_risk   = int(risk_amount / sl_distance)

        # Hard cap: can't buy more than the budget allows
        qty_by_budget = int(budget / sig.entry_price)

        return min(qty_by_risk, qty_by_budget)

    def _print_allocation_report(
        self,
        signals: List[TradeSignal],
        snapshot: MarketSnapshot,
        portfolio: Optional[Portfolio],
        deployable: float,
    ) -> None:
        """Log a formatted capital allocation table for this cycle."""
        dd_pct  = portfolio.drawdown_pct if portfolio else 0.0
        exp_pct = (deployable / TOTAL_CAPITAL * 100) if TOTAL_CAPITAL else 0

        w = 72
        log.info("═" * w)
        log.info(
            "  CAPITAL RISK ENGINE  |  Regime: %-12s  VIX: %.1f",
            snapshot.regime.value, snapshot.vix,
        )
        log.info(
            "  Total Capital: ₹%s  |  Deployable: ₹%s (%.0f%%)",
            f"{TOTAL_CAPITAL:,.0f}", f"{deployable:,.0f}", exp_pct,
        )
        if dd_pct > 0.001:
            log.info(
                "  ⚠️  Portfolio Drawdown: %.1f%% — exposure reduced",
                dd_pct * 100,
            )
        log.info("  %-32s  %-14s  %s", "Strategy", "Budget", "Position Formula")
        log.info("  " + "─" * (w - 2))

        seen: set = set()
        for sig in signals:
            if sig.strategy_name in seen:
                continue
            seen.add(sig.strategy_name)
            budget   = self._strategy_budget(sig.strategy_name, deployable)
            sl_dist  = abs(sig.entry_price - sig.stop_loss)
            risk_amt = budget * MAX_RISK_PER_TRADE_PCT
            ex_qty   = int(risk_amt / sl_dist) if sl_dist > 0 else 0
            log.info(
                "  %-32s  ₹%10s  Risk=₹%s / SL=%.2f → ~%d shares",
                sig.strategy_name,
                f"{budget:,.0f}",
                f"{risk_amt:,.0f}",
                sl_dist, ex_qty,
            )

        log.info("  " + "─" * (w - 2))
        log.info(
            "  Cash reserved: ₹%s (%.0f%%)",
            f"{TOTAL_CAPITAL - deployable:,.0f}",
            (TOTAL_CAPITAL - deployable) / TOTAL_CAPITAL * 100,
        )
        log.info("═" * w)
