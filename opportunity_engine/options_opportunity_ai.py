"""
Options Opportunity AI — Layer 4 Agent 2  (Live Rebuild)
=========================================================
Generates options trading signals using real NSE options chain data.

Strategy selection is regime-aware and IV-Rank-driven:

  BULL_TREND   + any IVR  → Bull Call Spread   (defined-risk directional)
  BEAR_MARKET  + any IVR  → Bear Put Spread    (defined-risk directional)
  RANGE_MARKET + IVR ≥ 40 → Iron Condor        (sell premium both sides)
  VOLATILE     + IVR ≥ 55 → Iron Condor        (collect high premium)
  any regime   + IVR < 25 + event → Long Straddle (buy cheap vol before event)

All premiums are in index points (₹ value = premium × lot_size).
No hardcoded strikes, IVs, or expiry dates — everything fetched live.

Confidence discount of 1.5 applied when chain is synthetic (no live data).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.market_data  import MarketSnapshot, RegimeLabel
from models.trade_signal import TradeSignal, SignalDirection, SignalStrength, SignalType
from data_feeds.options_feed import (
    get_options_feed, OptionsFeed, OptionsChain, OptionContract,
    NSE_LOT_SIZES, MIN_TRADABLE_OI,
)
from utils import get_logger

log = get_logger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────

# Instruments to scan on every cycle
OPTIONS_SYMBOLS = ["NIFTY", "BANKNIFTY"]

# IV Rank thresholds
IVR_SELL_THRESHOLD   = 40    # prefer selling premium when IVR ≥ 40
IVR_HIGH_PREMIUM     = 60    # strongly elevated IV (Iron Condor ideal)
IVR_BUY_CHEAP_VOL    = 25    # buy options when IV is cheap

# Minimum DTE before we stop entering new positions on that expiry
MIN_DTE_ENTRY        = 7

# Minimum confidence score to emit a signal (0–10 scale)
MIN_CONFIDENCE       = 6.0

# Confidence penalty applied when live NSE chain is unavailable.
# At 1.5, synthetic signals score ≤ 6.3 - 1.5 = 4.8 < MIN_CONFIDENCE → blocked.
# This is intentional: Black-Scholes ≠ real market price (no skew, no liquidity,
# no bid-ask spread).  Options only trade when yfinance provides a live chain.
SYNTHETIC_PENALTY    = 1.5

# Minimum premium (points) for any leg — avoids junk far-OTM options
MIN_LEG_PREMIUM      = 5.0

# Minimum spread width in index points for directional spreads.
# Below this the wings are too close: strike proximity collapses max-profit
# and makes the trade RR-unfavourable before transaction costs.
# NIFTY interval = 50 pts → min 1 interval; BANKNIFTY = 100 pts → 1 interval.
MIN_SPREAD_WIDTH_NIFTY     = 50.0    # 1 NIFTY strike interval
MIN_SPREAD_WIDTH_BANKNIFTY = 100.0   # 1 BANKNIFTY strike interval

# Minimum credit-to-width ratio for Iron Condor (payoff balance check).
# Net credit must be ≥ this fraction of the wing width to be worth selling.
# Below 0.15 the credit collected doesn't compensate the max-loss risk.
IC_MIN_CREDIT_TO_WIDTH = 0.15

# Minimum RR for debit spreads: max_profit must be ≥ this × net_debit
DEBIT_MIN_RR           = 1.0

# Legacy alias kept so old import paths don't break
OPTIONS_WATCHLIST: List[Dict[str, Any]] = []


class OptionsOpportunityAI:
    """
    Regime-aware, IV-driven options signal generator.
    Called by MasterOrchestrator as part of Layer 4 (OpportunityEngine).
    """

    def __init__(self) -> None:
        self._feed: OptionsFeed = get_options_feed()
        self._http_calls: int = 0
        self._dte_fallback: int = 0
        self._current_snapshot = None  # set during each scan for builder access
        log.info("[OptionsOpportunityAI] Initialised — live data feed ready.")

    # ── Public interface ───────────────────────────────────────────────

    def scan(self, snapshot: MarketSnapshot) -> List[TradeSignal]:
        """
        Scan all options instruments and return high-probability signals.
        Returns an empty list when market conditions are unfavourable.
        """
        signals: List[TradeSignal] = []
        self._http_calls = 0
        self._dte_fallback = 0
        _symbols_scanned = 0

        for symbol in OPTIONS_SYMBOLS:
            try:
                # ── Per-symbol capability gate ─────────────────────────
                # Only scan symbols with a live chain — synthetic chains
                # produce corrupted IV/OI signals and are skipped entirely.
                # This means NIFTY options work even when BANKNIFTY is down.
                try:
                    from data_feeds import get_feed_manager as _gfm_cap
                    _cap = _gfm_cap().get_options_capability(symbol)
                    log.info(
                        "[OptionsCapability] symbol=%-12s  chain_live=%-5s  "
                        "strategies_enabled=%-5s  source=%s",
                        symbol, _cap["chain_live"], _cap["strategies_enabled"],
                        _cap["source"],
                    )
                    if not _cap["strategies_enabled"]:
                        log.info(
                            "[OptionsCapability] %s source=%s — strategies SKIPPED "
                            "(live chain required for options signals)",
                            symbol, _cap["source"],
                        )
                        continue
                except Exception:
                    pass  # capability check unavailable — proceed normally

                _symbols_scanned += 1
                sig = self._scan_symbol(symbol, snapshot)
                if sig and sig.confidence >= MIN_CONFIDENCE:
                    signals.append(sig)
                    try:
                        meta = json.loads(sig.notes)
                        dte  = meta.get("dte", "?")
                    except Exception:
                        dte  = "?"
                    log.info(
                        "[OptionsOpportunityAI] %s  strategy=%s  "
                        "entry=%.2f  confidence=%.1f  DTE=%s",
                        symbol, sig.strategy_name, sig.entry_price,
                        sig.confidence, dte,
                    )
            except Exception as exc:
                log.warning(
                    "[OptionsOpportunityAI] %s scan raised: %s", symbol, exc
                )

        log.info(
            "[OptionsOpportunityAI] Scan complete — %d signal(s) emitted.",
            len(signals),
        )
        log.info(
            "[OEOptionsProfile] symbols_scanned=%d  http_calls=%d  dte_fallback=%d"
            "  signals=%d",
            _symbols_scanned, self._http_calls, self._dte_fallback, len(signals),
        )
        return signals

    # ── Per-instrument ─────────────────────────────────────────────────

    def _scan_symbol(
        self, symbol: str, snapshot: MarketSnapshot
    ) -> Optional[TradeSignal]:
        self._current_snapshot = snapshot  # available to _base_confidence via builders
        chain = self._feed.get_chain(symbol, dte_target=20)
        self._http_calls += 1
        if chain is None:
            log.debug("[OptionsOpportunityAI] No chain for %s.", symbol)
            return None

        # ── OI Trace: strategy_input stage ───────────────────────────────
        try:
            _si_ce_oi  = sum(c.oi for c in chain.contracts if c.option_type == "CE")
            _si_pe_oi  = sum(c.oi for c in chain.contracts if c.option_type == "PE")
            _si_w_oi   = sum(1 for c in chain.contracts if (c.oi or 0) > 0)
            log.debug(
                "[OptionsOITrace] stage=strategy_input symbol=%s contracts=%d "
                "contracts_with_oi=%d call_oi=%.0f put_oi=%.0f pcr=%.4f is_live=%s",
                symbol, len(chain.contracts), _si_w_oi,
                _si_ce_oi, _si_pe_oi, chain.pcr or 0, chain.is_live,
            )
        except Exception:
            pass

        if chain.dte < MIN_DTE_ENTRY:
            # Near-term expiry (typically last week of weekly cycle, DTE 0–6).
            # Dhan always returns the near-term contract; request a farther
            # dte_target so the feed falls through to yfinance which selects
            # the correct next-weekly / next-monthly expiry.
            log.info(
                "[OptionsOpportunityAI] %s DTE=%d < %d — requesting next expiry "
                "(dte_target=21).",
                symbol, chain.dte, MIN_DTE_ENTRY,
            )
            chain = self._feed.get_chain(symbol, dte_target=21)
            self._http_calls += 1
            self._dte_fallback += 1
            if chain is None or chain.dte < MIN_DTE_ENTRY:
                log.info(
                    "[OptionsOpportunityAI] %s — no expiry with DTE≥%d available; skipping.",
                    symbol, MIN_DTE_ENTRY,
                )
                return None
            log.info(
                "[OptionsOpportunityAI] %s — switched to next expiry DTE=%d.",
                symbol, chain.dte,
            )

        # ── Chain quality gate ──────────────────────────────────────────
        # Scores 0.0–1.0. Below 0.5 means partial/illiquid/stale chain.
        quality_score, quality_issues = self._feed.chain_quality_score(chain)
        if chain.is_live and quality_score < 0.5:
            log.warning(
                "[OptionsOpportunityAI] %s chain quality=%.2f — skipping. Issues: %s",
                symbol, quality_score, "; ".join(quality_issues),
            )
            return None

        # ── DISCOVERED: emit full market context before strategy selection ──
        # This is the foundation of the knowledge lifecycle.  Every discovered
        # opportunity — regardless of whether it proceeds — gets a record with
        # full chain context (OI, PCR, IV provenance, bid-ask spread) attached.
        opportunity_id = None
        try:
            from knowledge_system.options_opportunity_registry import (
                get_options_opportunity_registry,
            )
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
                OptionsOpportunityObservation,
                OBS_DISCOVERED,
                IV_SOURCE_LIVE_MARKET, IV_SOURCE_MODEL_ESTIMATE,
                DATA_SOURCE_ANGEL_ONE, DATA_SOURCE_YFINANCE, DATA_SOURCE_SYNTHETIC,
            )
            registry = get_options_opportunity_registry()
            journal  = get_options_observation_journal()

            # Determine strategy name for the opportunity_id — use tentative
            tentative_strat = self._select_strategy(snapshot, chain) or "UNKNOWN"
            opportunity_id  = registry.new_opportunity_id(symbol)

            # Determine IV and data provenance from chain
            _data_src  = getattr(chain, "data_source", "") or (
                DATA_SOURCE_ANGEL_ONE if chain.is_live else DATA_SOURCE_SYNTHETIC
            )
            _iv_src = (
                IV_SOURCE_LIVE_MARKET if _data_src == DATA_SOURCE_YFINANCE
                else IV_SOURCE_MODEL_ESTIMATE if _data_src == DATA_SOURCE_ANGEL_ONE
                else "DERIVED"
            )

            # Build per-leg context for the ATM contracts
            legs_ctx = []
            for leg_contract in [chain.atm_call(), chain.atm_put()]:
                if leg_contract:
                    legs_ctx.append({
                        "strike":        leg_contract.strike,
                        "option_type":   leg_contract.option_type,
                        "premium":       leg_contract.premium,
                        "bid":           leg_contract.bid,
                        "ask":           leg_contract.ask,
                        "iv":            leg_contract.iv,
                        "delta":         leg_contract.delta,
                        "gamma":         leg_contract.gamma,
                        "theta":         leg_contract.theta,
                        "vega":          leg_contract.vega,
                        "open_interest": leg_contract.open_interest,
                        "volume":        leg_contract.volume,
                        "iv_source":     getattr(leg_contract, "iv_source", _iv_src),
                    })

            # Compute time of day
            _hour = datetime.now().hour
            _tod = (
                "PRE_MARKET" if _hour < 9
                else "OPENING"  if _hour < 10
                else "CLOSING"  if _hour >= 15
                else "NORMAL"
            )

            obs_disc = OptionsOpportunityObservation(
                obs_id        = journal.make_obs_id(symbol, tentative_strat),
                symbol        = symbol,
                strategy_name = tentative_strat,
                observed_at   = datetime.now().isoformat(),
                state         = OBS_DISCOVERED,
                opportunity_id = opportunity_id,
                confidence    = self._base_confidence(chain, "pre_strategy"),
                direction     = str(snapshot.regime.value if hasattr(snapshot.regime, "value") else snapshot.regime),
                dte           = chain.dte,
                iv_rank       = chain.iv_rank,
                chain_quality = quality_score,
                regime        = str(snapshot.regime.value if hasattr(snapshot.regime, "value") else snapshot.regime),
                vix           = float(getattr(snapshot, "vix", 0) or 0),
                data_source   = _data_src,
                iv_source     = _iv_src,
                greek_source  = (
                    "LIVE_MARKET" if _iv_src == IV_SOURCE_LIVE_MARKET
                    else "MODEL_ESTIMATE"
                ),
                spot_price    = chain.spot,
                atm_iv        = chain.atm_iv,
                total_ce_oi   = chain.total_ce_oi,
                total_pe_oi   = chain.total_pe_oi,
                pcr           = chain.pcr,
                atm_bid_ask_spread = getattr(chain, "atm_bid_ask_spread_pct", 0.0),
                time_of_day   = _tod,
                events_today  = list(getattr(snapshot, "events_today", None) or []),
                legs_context  = legs_ctx,
            )
            journal.record(obs_disc)
        except Exception as _disc_exc:
            log.debug("[OptionsOpportunityAI] DISCOVERED record failed: %s", _disc_exc)

        strategy = self._select_strategy(snapshot, chain)
        if strategy is None:
            return None

        builders = {
            "Bull_Call_Spread":  self._build_bull_call_spread,
            "Bear_Put_Spread":   self._build_bear_put_spread,
            "Iron_Condor_Range": self._build_iron_condor,
            "Long_Straddle":     self._build_long_straddle,
        }
        build_fn = builders.get(strategy)
        if build_fn is None:
            return None

        signal = build_fn(chain, strategy)
        if signal is None:
            return None

        # Embed chain quality into notes for downstream validation
        try:
            meta = json.loads(signal.notes)
            meta["chain_quality"]  = quality_score
            meta["chain_issues"]   = quality_issues
            meta["is_live"]        = chain.is_live
            meta["opportunity_id"] = opportunity_id   # stable lifecycle ID
            meta["data_source"]    = getattr(chain, "data_source", "")
            meta["iv_source"]      = (
                "LIVE_MARKET" if getattr(chain, "data_source", "") == "YFINANCE"
                else "MODEL_ESTIMATE" if getattr(chain, "data_source", "") == "ANGEL_ONE"
                else "DERIVED"
            )
            signal.notes = json.dumps(meta)
        except Exception:
            pass

        # Discount confidence if we had to use a synthetic chain
        if not chain.is_live:
            signal.confidence = max(
                round(signal.confidence - SYNTHETIC_PENALTY, 1), 4.0
            )
            try:
                meta = json.loads(signal.notes)
                meta["data_quality"] = "synthetic"
                signal.notes = json.dumps(meta)
            except Exception:
                pass

        return signal

    # ── Strategy selector ──────────────────────────────────────────────

    def _select_strategy(
        self, snapshot: MarketSnapshot, chain: OptionsChain
    ) -> Optional[str]:
        """Return the best strategy name given regime and IVR, or None."""
        regime    = snapshot.regime
        ivr       = chain.iv_rank
        has_event = bool(snapshot.events_today)

        # Long Straddle: cheap vol + imminent event
        if has_event and ivr < IVR_BUY_CHEAP_VOL:
            log.info(
                "[OptionsOpportunityAI] %s: event day + IVR=%.0f < %d → Long Straddle",
                chain.symbol, ivr, IVR_BUY_CHEAP_VOL,
            )
            return "Long_Straddle"

        if regime == RegimeLabel.BULL_TREND:
            return "Bull_Call_Spread"

        if regime == RegimeLabel.BEAR_MARKET:
            return "Bear_Put_Spread"

        if regime in (RegimeLabel.RANGE_MARKET, RegimeLabel.VOLATILE):
            if ivr >= IVR_SELL_THRESHOLD:
                return "Iron_Condor_Range"
            if regime == RegimeLabel.RANGE_MARKET:
                return "Iron_Condor_Range"

        log.debug(
            "[OptionsOpportunityAI] %s: regime=%s IVR=%.0f → no suitable strategy.",
            chain.symbol, regime.value, ivr,
        )
        return None

    # ── Strategy builders ──────────────────────────────────────────────

    def _build_bull_call_spread(
        self, chain: OptionsChain, strategy: str
    ) -> Optional[TradeSignal]:
        """
        Bull Call Spread
        ─────────────────
        Buy ATM call + Sell 1-strike OTM call (same expiry).
        Net debit   = buy_premium − sell_premium   (known max loss)
        Max profit  = strike_width − net_debit     (if spot > short strike at expiry)
        """
        atm_c = chain.atm_call()
        if not atm_c or atm_c.premium < MIN_LEG_PREMIUM:
            return None

        otm_cs = chain.otm_calls_above(atm_c.strike, n=1)
        if not otm_cs:
            return None
        sell_c = otm_cs[0]
        if sell_c.premium < MIN_LEG_PREMIUM:
            return None

        if chain.is_live and (
            atm_c.open_interest < MIN_TRADABLE_OI
            or sell_c.open_interest < MIN_TRADABLE_OI
        ):
            log.debug(
                "[OptionsOpportunityAI] BCS %s: OI too low — skip.", chain.symbol
            )
            return None

        net_debit    = round(atm_c.premium - sell_c.premium, 2)
        spread_width = sell_c.strike - atm_c.strike
        max_profit   = round(spread_width - net_debit, 2)
        if net_debit <= 0 or max_profit <= 0:
            return None

        # ── Spread construction validation ─────────────────────────────
        # Check 1: minimum wing width (strikes not too close)
        _min_w = (MIN_SPREAD_WIDTH_BANKNIFTY
                  if chain.symbol == "BANKNIFTY"
                  else MIN_SPREAD_WIDTH_NIFTY)
        if spread_width < _min_w:
            log.debug(
                "[OptionsOpportunityAI] BCS %s spread_width=%.0f < %.0f — invalid.",
                chain.symbol, spread_width, _min_w,
            )
            return None
        # Check 2: minimum RR (max_profit ≥ 1× net_debit)
        if max_profit < net_debit * DEBIT_MIN_RR:
            log.debug(
                "[OptionsOpportunityAI] BCS %s RR=%.2f < %.2f — unfavourable.",
                chain.symbol, max_profit / net_debit, DEBIT_MIN_RR,
            )
            return None

        stop_prem   = round(net_debit * 0.50, 2)          # exit at 50 % loss
        target_prem = round(net_debit + max_profit * 0.60, 2)  # take 60 % of max profit

        legs = [
            {"type": "CE", "strike": atm_c.strike,  "direction": "BUY",
             "premium": atm_c.premium,  "iv": atm_c.iv,  "delta": atm_c.delta,
             "gamma": atm_c.gamma, "theta": atm_c.theta, "vega": atm_c.vega,
             "open_interest": atm_c.open_interest, "volume": atm_c.volume,
             "bid": atm_c.bid, "ask": atm_c.ask,
             "iv_source": getattr(atm_c, "iv_source", "")},
            {"type": "CE", "strike": sell_c.strike, "direction": "SELL",
             "premium": sell_c.premium, "iv": sell_c.iv, "delta": sell_c.delta,
             "gamma": sell_c.gamma, "theta": sell_c.theta, "vega": sell_c.vega,
             "open_interest": sell_c.open_interest, "volume": sell_c.volume,
             "bid": sell_c.bid, "ask": sell_c.ask,
             "iv_source": getattr(sell_c, "iv_source", "")},
        ]
        meta = {
            "strategy_type": "BULL_CALL_SPREAD",
            "spread_rr": round(max_profit / net_debit, 2),
            "net_debit": net_debit,
            "spread_width": spread_width,
            "max_profit": max_profit,
            "max_loss": net_debit,
            "lot_size": NSE_LOT_SIZES.get(chain.symbol, 75),
            "dte": chain.dte,
            "iv_rank": chain.iv_rank,
            "spot": chain.spot,
            "legs": legs,
        }
        return TradeSignal(
            symbol        = chain.symbol,
            direction     = SignalDirection.BUY,
            signal_type   = SignalType.OPTIONS,
            strength      = SignalStrength.MODERATE,
            entry_price   = net_debit,
            stop_loss     = stop_prem,
            target_price  = target_prem,
            confidence    = self._base_confidence(chain, "debit_spread", strategy_name=strategy, snapshot=self._current_snapshot),
            source_agent  = "OptionsOpportunityAI",
            strategy_name = strategy,
            strike_price  = float(atm_c.strike),
            option_type   = "BULL_CALL_SPREAD",
            notes         = json.dumps(meta),
            atr           = round(chain.atm_iv * chain.spot, 2),
        )

    def _build_bear_put_spread(
        self, chain: OptionsChain, strategy: str
    ) -> Optional[TradeSignal]:
        """
        Bear Put Spread
        ────────────────
        Buy ATM put + Sell 1-strike OTM put (lower strike).
        Net debit  = buy_premium − sell_premium
        Max profit = strike_width − net_debit
        """
        atm_p = chain.atm_put()
        if not atm_p or atm_p.premium < MIN_LEG_PREMIUM:
            return None

        otm_ps = chain.otm_puts_below(atm_p.strike, n=1)
        if not otm_ps:
            return None
        sell_p = otm_ps[0]
        if sell_p.premium < MIN_LEG_PREMIUM:
            return None

        if chain.is_live and (
            atm_p.open_interest < MIN_TRADABLE_OI
            or sell_p.open_interest < MIN_TRADABLE_OI
        ):
            return None

        net_debit    = round(atm_p.premium - sell_p.premium, 2)
        spread_width = atm_p.strike - sell_p.strike
        max_profit   = round(spread_width - net_debit, 2)
        if net_debit <= 0 or max_profit <= 0:
            return None

        # ── Spread construction validation ─────────────────────────────
        _min_w = (MIN_SPREAD_WIDTH_BANKNIFTY
                  if chain.symbol == "BANKNIFTY"
                  else MIN_SPREAD_WIDTH_NIFTY)
        if spread_width < _min_w:
            log.debug(
                "[OptionsOpportunityAI] BPS %s spread_width=%.0f < %.0f — invalid.",
                chain.symbol, spread_width, _min_w,
            )
            return None
        if max_profit < net_debit * DEBIT_MIN_RR:
            log.debug(
                "[OptionsOpportunityAI] BPS %s RR=%.2f < %.2f — unfavourable.",
                chain.symbol, max_profit / net_debit, DEBIT_MIN_RR,
            )
            return None

        stop_prem   = round(net_debit * 0.50, 2)
        target_prem = round(net_debit + max_profit * 0.60, 2)

        legs = [
            {"type": "PE", "strike": atm_p.strike,  "direction": "BUY",
             "premium": atm_p.premium,  "iv": atm_p.iv,  "delta": atm_p.delta,
             "gamma": atm_p.gamma, "theta": atm_p.theta, "vega": atm_p.vega,
             "open_interest": atm_p.open_interest, "volume": atm_p.volume,
             "bid": atm_p.bid, "ask": atm_p.ask,
             "iv_source": getattr(atm_p, "iv_source", "")},
            {"type": "PE", "strike": sell_p.strike, "direction": "SELL",
             "premium": sell_p.premium, "iv": sell_p.iv, "delta": sell_p.delta,
             "gamma": sell_p.gamma, "theta": sell_p.theta, "vega": sell_p.vega,
             "open_interest": sell_p.open_interest, "volume": sell_p.volume,
             "bid": sell_p.bid, "ask": sell_p.ask,
             "iv_source": getattr(sell_p, "iv_source", "")},
        ]
        meta = {
            "strategy_type": "BEAR_PUT_SPREAD",
            "spread_rr": round(max_profit / net_debit, 2),
            "net_debit": net_debit,
            "spread_width": spread_width,
            "max_profit": max_profit,
            "max_loss": net_debit,
            "lot_size": NSE_LOT_SIZES.get(chain.symbol, 75),
            "dte": chain.dte,
            "iv_rank": chain.iv_rank,
            "spot": chain.spot,
            "legs": legs,
        }
        return TradeSignal(
            symbol        = chain.symbol,
            direction     = SignalDirection.SELL,
            signal_type   = SignalType.OPTIONS,
            strength      = SignalStrength.MODERATE,
            entry_price   = net_debit,
            stop_loss     = stop_prem,
            target_price  = target_prem,
            confidence    = self._base_confidence(chain, "debit_spread", strategy_name=strategy, snapshot=self._current_snapshot),
            source_agent  = "OptionsOpportunityAI",
            strategy_name = strategy,
            strike_price  = float(atm_p.strike),
            option_type   = "BEAR_PUT_SPREAD",
            notes         = json.dumps(meta),
            atr           = round(chain.atm_iv * chain.spot, 2),
        )

    def _build_iron_condor(
        self, chain: OptionsChain, strategy: str
    ) -> Optional[TradeSignal]:
        """
        Iron Condor  (sell OTM call spread + sell OTM put spread)
        ─────────────────────────────────────────────────────────
        Sell 1-strike OTM call / Buy 2-strikes OTM call  (call side)
        Sell 1-strike OTM put  / Buy 2-strikes OTM put   (put side)

        Max profit = net credit received (spot stays between short strikes)
        Max loss   = strike width − net credit
        """
        atm = chain.atm_strike()

        sell_c_list = chain.otm_calls_above(atm, n=2)
        if len(sell_c_list) < 2:
            return None
        sell_c, buy_c = sell_c_list[0], sell_c_list[1]

        sell_p_list = chain.otm_puts_below(atm, n=2)
        if len(sell_p_list) < 2:
            return None
        sell_p, buy_p = sell_p_list[0], sell_p_list[1]

        if chain.is_live:
            min_oi = MIN_TRADABLE_OI // 2
            for leg in (sell_c, buy_c, sell_p, buy_p):
                if leg.open_interest < min_oi:
                    return None

        for leg in (sell_c, buy_c, sell_p, buy_p):
            if leg.premium < MIN_LEG_PREMIUM:
                return None

        call_credit = round(sell_c.premium - buy_c.premium, 2)
        put_credit  = round(sell_p.premium - buy_p.premium, 2)
        net_credit  = round(call_credit + put_credit, 2)
        call_width  = buy_c.strike - sell_c.strike
        put_width   = sell_p.strike - buy_p.strike
        max_loss    = round(call_width - net_credit, 2)

        if net_credit <= 0 or max_loss <= 0:
            return None

        # ── Spread construction validation ─────────────────────────────
        # Check 1: balanced wings (call width vs put width within 20%)
        if put_width > 0 and call_width > 0:
            wing_ratio = max(call_width, put_width) / min(call_width, put_width)
            if wing_ratio > 1.20:
                log.debug(
                    "[OptionsOpportunityAI] IC %s wings unbalanced: "
                    "call_width=%.0f put_width=%.0f ratio=%.2f > 1.20.",
                    chain.symbol, call_width, put_width, wing_ratio,
                )
                return None
        # Check 2: credit must be ≥ IC_MIN_CREDIT_TO_WIDTH × wing width
        credit_to_width = net_credit / call_width if call_width > 0 else 0
        if credit_to_width < IC_MIN_CREDIT_TO_WIDTH:
            log.debug(
                "[OptionsOpportunityAI] IC %s credit_to_width=%.2f < %.2f — "
                "insufficient premium vs max-loss.",
                chain.symbol, credit_to_width, IC_MIN_CREDIT_TO_WIDTH,
            )
            return None

        # Close when 75 % of credit is retained (25 % left to collect)
        target_prem = round(net_credit * 0.25, 2)
        # Exit if debit to close = 2 × initial credit (100 % loss on credit)
        stop_prem   = round(net_credit * 2.0, 2)

        legs = [
            {"type": "CE", "strike": sell_c.strike, "direction": "SELL",
             "premium": sell_c.premium, "iv": sell_c.iv, "delta": sell_c.delta,
             "gamma": sell_c.gamma, "theta": sell_c.theta, "vega": sell_c.vega,
             "open_interest": sell_c.open_interest, "volume": sell_c.volume,
             "bid": sell_c.bid, "ask": sell_c.ask,
             "iv_source": getattr(sell_c, "iv_source", "")},
            {"type": "CE", "strike": buy_c.strike,  "direction": "BUY",
             "premium": buy_c.premium,  "iv": buy_c.iv,  "delta": buy_c.delta,
             "gamma": buy_c.gamma, "theta": buy_c.theta, "vega": buy_c.vega,
             "open_interest": buy_c.open_interest, "volume": buy_c.volume,
             "bid": buy_c.bid, "ask": buy_c.ask,
             "iv_source": getattr(buy_c, "iv_source", "")},
            {"type": "PE", "strike": sell_p.strike, "direction": "SELL",
             "premium": sell_p.premium, "iv": sell_p.iv, "delta": sell_p.delta,
             "gamma": sell_p.gamma, "theta": sell_p.theta, "vega": sell_p.vega,
             "open_interest": sell_p.open_interest, "volume": sell_p.volume,
             "bid": sell_p.bid, "ask": sell_p.ask,
             "iv_source": getattr(sell_p, "iv_source", "")},
            {"type": "PE", "strike": buy_p.strike,  "direction": "BUY",
             "premium": buy_p.premium,  "iv": buy_p.iv,  "delta": buy_p.delta,
             "gamma": buy_p.gamma, "theta": buy_p.theta, "vega": buy_p.vega,
             "open_interest": buy_p.open_interest, "volume": buy_p.volume,
             "bid": buy_p.bid, "ask": buy_p.ask,
             "iv_source": getattr(buy_p, "iv_source", "")},
        ]
        meta = {
            "strategy_type": "IRON_CONDOR",
            "net_credit": net_credit,
            "call_credit": call_credit,
            "put_credit": put_credit,
            "call_width": call_width,
            "put_width": put_width,
            "credit_to_width": round(credit_to_width, 3),
            "max_profit": net_credit,
            "max_loss": max_loss,
            "lot_size": NSE_LOT_SIZES.get(chain.symbol, 75),
            "dte": chain.dte,
            "iv_rank": chain.iv_rank,
            "spot": chain.spot,
            "legs": legs,
        }
        return TradeSignal(
            symbol        = chain.symbol,
            direction     = SignalDirection.SELL,   # net sellers of premium
            signal_type   = SignalType.SPREAD,
            strength      = SignalStrength.MODERATE,
            entry_price   = net_credit,
            stop_loss     = stop_prem,
            target_price  = target_prem,
            confidence    = self._base_confidence(chain, "credit_spread", strategy_name=strategy, snapshot=self._current_snapshot),
            source_agent  = "OptionsOpportunityAI",
            strategy_name = strategy,
            strike_price  = float(atm),
            option_type   = "IRON_CONDOR",
            notes         = json.dumps(meta),
            atr           = round(chain.atm_iv * chain.spot, 2),
        )

    def _build_long_straddle(
        self, chain: OptionsChain, strategy: str
    ) -> Optional[TradeSignal]:
        """
        Long Straddle  (buy ATM call + buy ATM put)
        ─────────────────────────────────────────────
        Profits from a large move in either direction.
        Best before events when IV is cheap (IVR < 25).

        Max loss   = total premium paid
        Break-even = ATM ± total_premium
        """
        atm_c = chain.atm_call()
        atm_p = chain.atm_put()
        if not atm_c or not atm_p:
            return None
        if atm_c.premium < MIN_LEG_PREMIUM or atm_p.premium < MIN_LEG_PREMIUM:
            return None

        if chain.is_live and (
            atm_c.open_interest < MIN_TRADABLE_OI
            or atm_p.open_interest < MIN_TRADABLE_OI
        ):
            return None

        total_debit = round(atm_c.premium + atm_p.premium, 2)
        stop_prem   = round(total_debit * 0.40, 2)   # exit at 60 % loss
        target_prem = round(total_debit * 2.0,  2)   # target: position doubles

        legs = [
            {"type": "CE", "strike": atm_c.strike, "direction": "BUY",
             "premium": atm_c.premium, "iv": atm_c.iv, "delta": atm_c.delta,
             "gamma": atm_c.gamma, "theta": atm_c.theta, "vega": atm_c.vega,
             "open_interest": atm_c.open_interest, "volume": atm_c.volume,
             "bid": atm_c.bid, "ask": atm_c.ask,
             "iv_source": getattr(atm_c, "iv_source", "")},
            {"type": "PE", "strike": atm_p.strike, "direction": "BUY",
             "premium": atm_p.premium, "iv": atm_p.iv, "delta": atm_p.delta,
             "gamma": atm_p.gamma, "theta": atm_p.theta, "vega": atm_p.vega,
             "open_interest": atm_p.open_interest, "volume": atm_p.volume,
             "bid": atm_p.bid, "ask": atm_p.ask,
             "iv_source": getattr(atm_p, "iv_source", "")},
        ]
        meta = {
            "strategy_type": "LONG_STRADDLE",
            "total_debit": total_debit,
            "max_loss": total_debit,
            "breakeven_up":   round(atm_c.strike + total_debit, 2),
            "breakeven_down": round(atm_p.strike - total_debit, 2),
            "lot_size": NSE_LOT_SIZES.get(chain.symbol, 75),
            "dte": chain.dte,
            "iv_rank": chain.iv_rank,
            "spot": chain.spot,
            "legs": legs,
        }
        return TradeSignal(
            symbol        = chain.symbol,
            direction     = SignalDirection.BUY,
            signal_type   = SignalType.OPTIONS,
            strength      = SignalStrength.MODERATE,
            entry_price   = total_debit,
            stop_loss     = stop_prem,
            target_price  = target_prem,
            confidence    = self._base_confidence(chain, "straddle", strategy_name=strategy, snapshot=self._current_snapshot),
            source_agent  = "OptionsOpportunityAI",
            strategy_name = strategy,
            strike_price  = float(atm_c.strike),
            option_type   = "LONG_STRADDLE",
            notes         = json.dumps(meta),
            atr           = round(chain.atm_iv * chain.spot, 2),
        )

    # ── Confidence scoring ─────────────────────────────────────────────

    def _base_confidence(
        self,
        chain: OptionsChain,
        stype: str,
        strategy_name: str = "",
        snapshot=None,
    ) -> float:
        """
        Return 0–10 confidence based on chain quality, IVR fit, DTE,
        learned strategy×regime weights, and knowledge store influence.

        Learning connections (Phase 4 fix — gaps closed):
          1. OptionsPerformanceTracker.get_weight() → multiplicative weight
             based on historical win_rate for this strategy×regime pair.
          2. OptionsKnowledgeStore.get_influence() → bounded additive delta
             only when knowledge is in VALIDATED or AUTHENTICATED state.
          3. Both connections are wrapped in try/except — failures fall back
             to the static formula, preserving existing production behaviour.
        """
        base = 6.5
        if chain.is_live:
            base += 0.5
        if 15 <= chain.dte <= 25:
            base += 0.3
        elif chain.dte < 10:
            base -= 0.5
        if stype in ("debit_spread", "straddle") and chain.iv_rank < IVR_BUY_CHEAP_VOL:
            base += 0.5
        if stype == "credit_spread" and chain.iv_rank >= IVR_HIGH_PREMIUM:
            base += 0.7

        # ── 1. OptionsPerformanceTracker weight (learned, persisted) ──────
        try:
            from learning_system.options_performance_tracker import (
                get_options_performance_tracker,
            )
            regime_str = ""
            if snapshot is not None:
                regime_str = str(
                    snapshot.regime.value
                    if hasattr(snapshot.regime, "value")
                    else snapshot.regime
                )
            # Map stype to canonical strategy type name for weight lookup
            stype_map = {
                "debit_spread":  "BULL_CALL_SPREAD",
                "credit_spread": "IRON_CONDOR",
                "straddle":      "LONG_STRADDLE",
            }
            lookup_name = strategy_name or stype_map.get(stype, stype.upper())
            tracker = get_options_performance_tracker()
            weight  = tracker.get_weight(lookup_name, regime_str)
            # weight 1.0 → no change; 0.9 → -0.15; 0.5 → -0.75
            base += (weight - 1.0) * 1.5
        except Exception:
            pass

        # ── 2. OptionsKnowledgeStore influence (validated knowledge only) ──
        try:
            from knowledge_system.options_knowledge_store import get_options_knowledge_store
            from knowledge_system.options_feature_extractor import (
                _ivr_band, _dte_band,
            )
            if snapshot is not None and chain is not None:
                regime_str = str(
                    snapshot.regime.value
                    if hasattr(snapshot.regime, "value")
                    else snapshot.regime
                )
                ivr_band  = _ivr_band(chain.iv_rank)
                dte_band  = _dte_band(chain.dte)
                ctx_key   = f"{regime_str}|{ivr_band}|{dte_band}"
                sn = strategy_name or stype
                store     = get_options_knowledge_store()
                influence, ks_state = store.get_influence(sn, ctx_key)
                # influence is ±0.05/0.10 fraction → scale to 10-pt system
                base += influence * 10.0
        except Exception:
            pass

        return min(round(base, 1), 9.5)
