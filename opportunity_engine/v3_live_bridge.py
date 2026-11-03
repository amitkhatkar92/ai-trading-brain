"""
opportunity_engine/v3_live_bridge.py
=====================================
V3 Mover Discovery -- LIVE signal bridge.

Converts Mover Discovery V3's (opportunity_engine/mover_discovery_v3.py)
daily top-ranked UP/DOWN picks into real TradeSignal objects, additive to
(never replacing) the existing EquityScannerAI signal source. Signals built
here flow through the EXACT SAME downstream pipeline as every other equity
signal -- StrategyLab (observation-only) -> CapitalRiskEngine -> RiskControl
-> MarketSimulation -> RiskGuardian -> Debate -> KDA (sole final authority)
-> Execution. Nothing here bypasses any existing risk gate.

mover_discovery_v3.py itself is deliberately left untouched in its own
"NEVER generates TradeSignal objects" design constraint -- TradeSignal
construction happens entirely in THIS module, not there.

Safety posture (first real-money exposure of this research pool):
  - Bounded daily exposure: at most V3_BRIDGE_MAX_UP + V3_BRIDGE_MAX_DOWN
    new signals per trading day (small, explicit, easy to monitor/rollback).
  - Quality floor: only candidates scoring >= V3_BRIDGE_MIN_SCORE are
    considered at all.
  - Once-per-trading-day guard (persisted state) -- V3's pool is a daily
    artifact, not a per-cycle recompute.
  - Confidence kept in the same modest 5.0-6.5 band as knowledge_referred
    signals -- KDA's own evidence-based authority is the real gatekeeper,
    not a high static confidence value.
  - Never raises; returns [] on any failure.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_STATE_PATH = Path("data/opportunity_engine/v3_live_bridge_state.json")

# Conservative initial exposure bounds -- tune up only with live evidence.
V3_BRIDGE_MAX_UP    = 3
V3_BRIDGE_MAX_DOWN  = 2
V3_BRIDGE_MIN_SCORE = 0.55
RR_DEFAULT          = 2.5
STOP_ATR_MULTIPLIER = 1.5
STRATEGY_NAME       = "V3_Mover_Discovery"

# Sector-rotation-enabled weight config, validated to sum to 1.0. Kept
# separate from mover_discovery_v3._DEFAULT_CONFIG (which stays at
# sector_rotation=0.0) so the module's own default/test behavior is
# completely unaffected by this bridge's choices.
def _bridge_v3_config():
    from opportunity_engine.mover_discovery_v3 import V3Config, V3UpWeights, V3DownWeights
    up_weights = V3UpWeights(
        atr_pct=0.225, mom_5d=0.18, rs_pct_5d=0.18, vol_ratio=0.18,
        mom_accel=0.135, sector_rotation=0.10,
    )
    down_weights = V3DownWeights(
        neg_mom_5d=0.27, neg_mom_accel=0.225, vol_expansion=0.18,
        atr_pct=0.135, rsi_overbought=0.09, sector_down=0.0,
        sector_rotation=0.10,
    )
    cfg = V3Config(
        enabled=True, shadow_mode=True,   # shadow_mode stays True: mover_discovery_v3.py
        discovery_pool_size=20,           # itself still never writes CandidateStore/signals.
        up_weights=up_weights, down_weights=down_weights,
    )
    cfg.validate()
    return cfg


def _load_state() -> Dict[str, Any]:
    try:
        if _STATE_PATH.exists():
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("[V3LiveBridge] state read failed, treating as fresh: %s", exc)
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(_STATE_PATH)
    except Exception as exc:
        log.warning("[V3LiveBridge] state write failed (non-fatal): %s", exc)


def _already_ran_today(trade_date: str) -> bool:
    return _load_state().get("last_run_trade_date") == trade_date


def _mark_ran(trade_date: str, up_count: int, down_count: int) -> None:
    _save_state({
        "last_run_trade_date": trade_date,
        "last_run_at": datetime.now().isoformat(),
        "up_signals": up_count,
        "down_signals": down_count,
    })


def _build_signal(cand: Dict[str, Any], direction: str, live_price: Optional[float]):
    """direction: 'UP' or 'DOWN'. Returns a TradeSignal, or None if no live
    price is available -- this is a brand-new real-money signal source, so
    entries never fall back to a stale ohlcv_daily close (could be a full
    trading day old by execution time)."""
    from models.trade_signal import TradeSignal, SignalDirection, SignalType, SignalStrength

    if not live_price or live_price <= 0:
        return None
    entry = live_price
    if entry <= 0:
        return None

    atr = float(cand.get("atr_14") or 0.0)
    if atr <= 0:
        atr = entry * (float(cand.get("atr_pct") or 1.5) / 100.0)
    stop_dist = max(atr * STOP_ATR_MULTIPLIER, entry * 0.010)

    score = float(cand.get("v3_up_score" if direction == "UP" else "v3_down_score") or 0.0)
    confidence = round(min(5.0 + max(score - 0.5, 0.0) * 3.0, 6.5), 2)

    if direction == "UP":
        sig_direction = SignalDirection.BUY
        stop_loss    = round(entry - stop_dist, 2)
        target_price = round(entry + RR_DEFAULT * stop_dist, 2)
    else:
        sig_direction = SignalDirection.SHORT
        stop_loss    = round(entry + stop_dist, 2)
        target_price = round(entry - RR_DEFAULT * stop_dist, 2)
        if target_price <= 0:
            return None

    return TradeSignal(
        symbol          = cand["symbol"],
        direction       = sig_direction,
        signal_type     = SignalType.EQUITY,
        strength        = SignalStrength.WEAK,
        entry_price     = entry,
        stop_loss       = stop_loss,
        target_price    = target_price,
        quantity        = 1,  # placeholder -- Risk Engine overwrites
        strategy_name   = STRATEGY_NAME,
        confidence      = confidence,
        source_agent    = "V3MoverDiscoveryBridge",
        notes           = f"v3_{direction.lower()}_score:{score:.4f}",
        atr             = atr,
        entry_zone_low  = round(max(0.0, entry - atr * 0.10), 2),
        entry_zone_high = round(entry + atr * 0.10, 2),
        scanner_score   = score,
        price_is_live   = True,
    )


def run_v3_live_bridge(snapshot=None, trading_date: Optional[str] = None) -> List[Any]:
    """
    Build and return real TradeSignal objects from today's V3 top picks,
    bounded and quality-gated per the module constants above. Runs at most
    once per trading date. Never raises -- returns [] on any failure.
    """
    try:
        from opportunity_engine.mover_discovery_v3_shadow_runner import (
            _load_universe_symbols, _load_ohlcv_from_db, _resolve_trade_date,
        )
        from opportunity_engine.mover_discovery_v3 import compute_v3_features, score_universe, select_candidates
        from opportunity_engine.sector_rotation_momentum import attach_sector_rotation_ranks
        from predictive_gap.liquid_universe_builder_001 import _load_existing_sector_map

        td = trading_date or _resolve_trade_date()
        if _already_ran_today(td):
            return []

        symbols = _load_universe_symbols()
        if not symbols:
            return []

        ohlcv = _load_ohlcv_from_db(symbols, td)
        if not ohlcv:
            return []

        features = []
        for sym, bars in ohlcv.items():
            feat = compute_v3_features(sym, bars["closes"], bars["highs"], bars["lows"], bars["volumes"])
            if feat is not None:
                features.append(feat)
        if len(features) < 10:
            return []

        sector_map = {}
        try:
            sector_map = _load_existing_sector_map()
        except Exception as exc:
            log.warning("[V3LiveBridge] sector map load failed, sector_rotation neutral: %s", exc)
        features = attach_sector_rotation_ranks(features, sector_map)

        cfg = _bridge_v3_config()
        scored = score_universe(features, cfg)
        up_cands, down_cands = select_candidates(scored, cfg, pool_size=cfg.discovery_pool_size)

        up_cands   = [c for c in up_cands   if float(c.get("v3_up_score")   or 0.0) >= V3_BRIDGE_MIN_SCORE][:V3_BRIDGE_MAX_UP]
        down_cands = [c for c in down_cands if float(c.get("v3_down_score") or 0.0) >= V3_BRIDGE_MIN_SCORE][:V3_BRIDGE_MAX_DOWN]

        # universe_stocks/ohlcv_daily store symbols WITH the .NS/.BO suffix;
        # _do_fetch_prices() expects BARE symbols (it adds its own .NS) and
        # returns results keyed by bare symbol. TradeSignal.symbol must also
        # be bare -- the rest of the pipeline (OrderManager/broker security
        # map) expects bare symbols throughout.
        def _bare(sym: str) -> str:
            return sym.replace(".NS", "").replace(".BO", "").strip()

        bare_symbols = [_bare(c["symbol"]) for c in up_cands + down_cands]
        live_prices: Dict[str, float] = {}
        try:
            from opportunity_engine.equity_scanner_ai import _do_fetch_prices
            live_prices = _do_fetch_prices(bare_symbols)
        except Exception as exc:
            log.warning("[V3LiveBridge] live price fetch failed: %s", exc)

        signals = []
        for c in up_cands:
            bare_sym = _bare(c["symbol"])
            sig = _build_signal({**c, "symbol": bare_sym}, "UP", live_prices.get(bare_sym))
            if sig is not None:
                signals.append(sig)
        for c in down_cands:
            bare_sym = _bare(c["symbol"])
            sig = _build_signal({**c, "symbol": bare_sym}, "DOWN", live_prices.get(bare_sym))
            if sig is not None:
                signals.append(sig)

        _mark_ran(td, len(up_cands), len(down_cands))
        log.info("[V3LiveBridge] trade_date=%s up=%d down=%d signals_built=%d",
                 td, len(up_cands), len(down_cands), len(signals))
        return signals
    except Exception as exc:
        log.warning("[V3LiveBridge] run failed, returning no signals: %s", exc)
        return []
