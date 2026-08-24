"""
Options Feature Extractor
==========================

Converts a raw options observation into a structured feature vector suitable
for pattern discovery, hypothesis generation, and knowledge validation.

TEMPORAL SAFETY GUARANTEE: every feature is computed exclusively from data
present in the observation record at `observed_at` time.  No look-ahead.

Feature categories:
  - Market regime features (regime, VIX band, time-of-day)
  - Options-specific features (IVR band, DTE band, PCR band)
  - Chain quality features (bid-ask spread, OI concentration, OI imbalance)
  - Strategy-signal features (direction, confidence band)
  - Calendar / temporal features (days-to-expiry, market session)
  - Data quality features (iv_source, data_source, chain_quality band)

All categorical features are bucketed strings (not raw floats) so they
combine correctly in pattern analysis.  The bucket boundaries are conservative
and documented below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Bucket definitions (documented for reproducibility) ───────────────────

# VIX bands
VIX_LOW    = "VIX_LOW"    # < 15
VIX_NORMAL = "VIX_NORMAL" # 15–20
VIX_ELEV   = "VIX_ELEV"   # 20–28
VIX_HIGH   = "VIX_HIGH"   # 28–40
VIX_EXTREME = "VIX_EXTREME" # > 40

# IVR bands
IVR_VERY_LOW  = "IVR_VERY_LOW"   # < 20
IVR_LOW       = "IVR_LOW"        # 20–35
IVR_NORMAL    = "IVR_NORMAL"     # 35–55
IVR_HIGH      = "IVR_HIGH"       # 55–75
IVR_VERY_HIGH = "IVR_VERY_HIGH"  # > 75

# DTE bands
DTE_NEAR    = "DTE_NEAR"    # < 7
DTE_WEEKLY  = "DTE_WEEKLY"  # 7–14
DTE_BI_WEEKLY = "DTE_BI_WEEKLY" # 14–21
DTE_MONTHLY = "DTE_MONTHLY" # 21–35
DTE_FAR     = "DTE_FAR"     # > 35

# PCR bands
PCR_EXTREME_BEARISH = "PCR_BEARISH_EXTREME"  # > 2.0
PCR_BEARISH         = "PCR_BEARISH"          # 1.5–2.0
PCR_NEUTRAL         = "PCR_NEUTRAL"          # 0.8–1.5
PCR_BULLISH         = "PCR_BULLISH"          # 0.5–0.8
PCR_EXTREME_BULLISH = "PCR_BULLISH_EXTREME"  # < 0.5
PCR_UNAVAILABLE     = "PCR_UNAVAILABLE"

# Bid-ask spread bands (as % of mid premium)
SPREAD_TIGHT  = "SPREAD_TIGHT"  # < 3%
SPREAD_NORMAL = "SPREAD_NORMAL" # 3–8%
SPREAD_WIDE   = "SPREAD_WIDE"   # 8–15%
SPREAD_VERY_WIDE = "SPREAD_VERY_WIDE"  # > 15%

# Confidence bands
CONF_LOW    = "CONF_LOW"    # < 6.5
CONF_MEDIUM = "CONF_MEDIUM" # 6.5–7.5
CONF_HIGH   = "CONF_HIGH"   # 7.5–8.5
CONF_VERY_HIGH = "CONF_VERY_HIGH"  # > 8.5

# OI imbalance: (CE_OI - PE_OI) / (CE_OI + PE_OI), -1 to +1
OI_HEAVY_CALL  = "OI_HEAVY_CALL"   # > 0.3 CE-dominant
OI_SLIGHT_CALL = "OI_SLIGHT_CALL"  # 0.1–0.3
OI_BALANCED    = "OI_BALANCED"     # -0.1 to 0.1
OI_SLIGHT_PUT  = "OI_SLIGHT_PUT"   # -0.3 to -0.1
OI_HEAVY_PUT   = "OI_HEAVY_PUT"    # < -0.3 PE-dominant
OI_UNAVAILABLE = "OI_UNAVAILABLE"

# Chain quality bands
CHAIN_LOW    = "CHAIN_LOW"    # < 0.4
CHAIN_MEDIUM = "CHAIN_MEDIUM" # 0.4–0.7
CHAIN_HIGH   = "CHAIN_HIGH"   # > 0.7


@dataclass
class OptionsFeatureVector:
    """
    Structured feature representation of one options observation.

    All fields are strings (bucketed categories) to allow direct use in
    frequency tables and pattern analysis without normalisation.

    Numeric raw values are preserved alongside for validation / regression.
    """
    opportunity_id:   Optional[str] = None
    symbol:           str = ""
    strategy_name:    str = ""
    observed_at:      str = ""

    # ── Categorical features ───────────────────────────────────────────
    regime:          str = ""      # BULL / BEAR / SIDEWAYS / UNCERTAIN
    vix_band:        str = ""      # VIX_*
    ivr_band:        str = ""      # IVR_*
    dte_band:        str = ""      # DTE_*
    pcr_band:        str = ""      # PCR_*
    spread_band:     str = ""      # SPREAD_*
    confidence_band: str = ""      # CONF_*
    oi_imbalance:    str = ""      # OI_*
    chain_quality_band: str = ""   # CHAIN_*
    direction:       str = ""      # BULLISH / BEARISH / NEUTRAL
    time_of_day:     str = ""      # PRE_MARKET / OPENING / NORMAL / CLOSING
    data_source:     str = ""      # ANGEL_ONE / YFINANCE / SYNTHETIC
    iv_source:       str = ""      # LIVE_MARKET / MODEL_ESTIMATE / DERIVED / UNAVAILABLE
    has_events:      str = ""      # TRUE / FALSE

    # ── Raw numeric values (for research, not pattern matching) ────────
    raw_vix:            float = 0.0
    raw_iv_rank:        float = 0.0
    raw_dte:            int   = 0
    raw_pcr:            float = 0.0
    raw_spread_pct:     float = 0.0
    raw_confidence:     float = 0.0
    raw_chain_quality:  float = 0.0
    raw_total_ce_oi:    int   = 0
    raw_total_pe_oi:    int   = 0
    raw_spot:           float = 0.0

    # ── Combination keys for pattern matching ─────────────────────────
    # Pre-computed joins of high-signal feature groups
    regime_ivr_dte:  str = ""   # "{regime}|{ivr_band}|{dte_band}"
    regime_vix_pcr:  str = ""   # "{regime}|{vix_band}|{pcr_band}"
    strategy_regime_dir: str = "" # "{strategy}|{regime}|{direction}"
    full_key:        str = ""   # all top features joined for max granularity

    # ── Validity flag ──────────────────────────────────────────────────
    is_valid:         bool = True   # False if critical fields missing
    missing_fields:   List[str] = field(default_factory=list)


def extract_features(obs: dict) -> OptionsFeatureVector:
    """
    Extract a feature vector from a raw observation dict (as stored in JSONL).

    Returns an OptionsFeatureVector.  Never raises; returns is_valid=False
    if critical fields are unavailable.
    """
    try:
        return _extract(obs)
    except Exception as exc:
        log.debug("[OptionsFeatureExtractor] Error extracting features: %s", exc)
        return OptionsFeatureVector(
            opportunity_id=obs.get("opportunity_id"),
            symbol=obs.get("symbol", ""),
            strategy_name=obs.get("strategy_name", ""),
            observed_at=obs.get("observed_at", ""),
            is_valid=False,
            missing_fields=["extraction_error"],
        )


def _extract(obs: dict) -> OptionsFeatureVector:
    missing: List[str] = []

    # ── Required fields ────────────────────────────────────────────────
    symbol        = obs.get("symbol", "")
    strategy_name = obs.get("strategy_name", "")
    observed_at   = obs.get("observed_at", "")
    opportunity_id = obs.get("opportunity_id")

    if not symbol:
        missing.append("symbol")
    if not strategy_name:
        missing.append("strategy_name")

    # ── VIX ────────────────────────────────────────────────────────────
    raw_vix = float(obs.get("vix") or 0)
    vix_band = _vix_band(raw_vix)

    # ── IVR ────────────────────────────────────────────────────────────
    raw_ivr = float(obs.get("iv_rank") or 0)
    ivr_band = _ivr_band(raw_ivr)

    # ── DTE ────────────────────────────────────────────────────────────
    raw_dte  = int(obs.get("dte") or 0)
    dte_band = _dte_band(raw_dte)
    if raw_dte == 0:
        missing.append("dte")

    # ── PCR ────────────────────────────────────────────────────────────
    raw_pcr  = float(obs.get("pcr") or 0)
    ce_oi    = int(obs.get("total_ce_oi") or 0)
    pe_oi    = int(obs.get("total_pe_oi") or 0)
    # Derive PCR from raw OI if direct field missing
    if raw_pcr == 0 and ce_oi > 0:
        raw_pcr = pe_oi / ce_oi
    pcr_band = _pcr_band(raw_pcr, ce_oi + pe_oi)

    # ── Bid-ask spread ─────────────────────────────────────────────────
    raw_spread = float(obs.get("atm_bid_ask_spread") or 0)
    spread_band = _spread_band(raw_spread)
    if raw_spread == 0:
        missing.append("atm_bid_ask_spread")

    # ── Confidence ────────────────────────────────────────────────────
    raw_conf    = float(obs.get("confidence") or 0)
    conf_band   = _conf_band(raw_conf)

    # ── Chain quality ─────────────────────────────────────────────────
    raw_chain   = float(obs.get("chain_quality") or 0)
    chain_band  = _chain_band(raw_chain)

    # ── OI imbalance ──────────────────────────────────────────────────
    oi_imbalance = _oi_imbalance_band(ce_oi, pe_oi)

    # ── Other categorical ─────────────────────────────────────────────
    regime    = str(obs.get("regime") or "UNKNOWN").upper()
    direction = str(obs.get("direction") or "UNKNOWN").upper()
    tod       = str(obs.get("time_of_day") or "NORMAL").upper()
    data_src  = str(obs.get("data_source") or "UNKNOWN").upper()
    iv_src    = str(obs.get("iv_source") or "UNKNOWN").upper()
    events    = obs.get("events_today") or []
    has_events = "TRUE" if events else "FALSE"

    # ── Combination keys ──────────────────────────────────────────────
    regime_ivr_dte    = f"{regime}|{ivr_band}|{dte_band}"
    regime_vix_pcr    = f"{regime}|{vix_band}|{pcr_band}"
    strategy_regime_dir = f"{strategy_name}|{regime}|{direction}"
    full_key = "|".join([
        strategy_name, regime, vix_band, ivr_band, dte_band,
        pcr_band, spread_band, direction, chain_band, has_events,
    ])

    is_valid = len(missing) < 3

    return OptionsFeatureVector(
        opportunity_id   = opportunity_id,
        symbol           = symbol,
        strategy_name    = strategy_name,
        observed_at      = observed_at,
        regime           = regime,
        vix_band         = vix_band,
        ivr_band         = ivr_band,
        dte_band         = dte_band,
        pcr_band         = pcr_band,
        spread_band      = spread_band,
        confidence_band  = conf_band,
        oi_imbalance     = oi_imbalance,
        chain_quality_band = chain_band,
        direction        = direction,
        time_of_day      = tod,
        data_source      = data_src,
        iv_source        = iv_src,
        has_events       = has_events,
        raw_vix          = raw_vix,
        raw_iv_rank      = raw_ivr,
        raw_dte          = raw_dte,
        raw_pcr          = raw_pcr,
        raw_spread_pct   = raw_spread,
        raw_confidence   = raw_conf,
        raw_chain_quality = raw_chain,
        raw_total_ce_oi  = ce_oi,
        raw_total_pe_oi  = pe_oi,
        raw_spot         = float(obs.get("spot_price") or 0),
        regime_ivr_dte   = regime_ivr_dte,
        regime_vix_pcr   = regime_vix_pcr,
        strategy_regime_dir = strategy_regime_dir,
        full_key         = full_key,
        is_valid         = is_valid,
        missing_fields   = missing,
    )


# ── Bucket helpers ─────────────────────────────────────────────────────────

def _vix_band(v: float) -> str:
    if v <= 0:
        return VIX_NORMAL  # default
    if v < 15:
        return VIX_LOW
    if v < 20:
        return VIX_NORMAL
    if v < 28:
        return VIX_ELEV
    if v <= 40:
        return VIX_HIGH
    return VIX_EXTREME


def _ivr_band(v: float) -> str:
    if v < 20:
        return IVR_VERY_LOW
    if v < 35:
        return IVR_LOW
    if v < 55:
        return IVR_NORMAL
    if v <= 75:
        return IVR_HIGH
    return IVR_VERY_HIGH


def _dte_band(v: int) -> str:
    if v < 7:
        return DTE_NEAR
    if v < 14:
        return DTE_WEEKLY
    if v < 21:
        return DTE_BI_WEEKLY
    if v <= 35:
        return DTE_MONTHLY
    return DTE_FAR


def _pcr_band(v: float, total_oi: int) -> str:
    if total_oi == 0:
        return PCR_UNAVAILABLE
    if v <= 0:
        return PCR_UNAVAILABLE
    if v > 2.0:
        return PCR_EXTREME_BEARISH
    if v > 1.5:
        return PCR_BEARISH
    if v > 0.8:
        return PCR_NEUTRAL
    if v > 0.5:
        return PCR_BULLISH
    return PCR_EXTREME_BULLISH


def _spread_band(v: float) -> str:
    """v is ATM bid-ask spread as decimal fraction of mid-price."""
    if v <= 0:
        return SPREAD_NORMAL  # unknown → assume normal
    pct = v * 100 if v <= 1 else v   # accept both 0.05 and 5.0 form
    if pct < 3:
        return SPREAD_TIGHT
    if pct < 8:
        return SPREAD_NORMAL
    if pct <= 15:
        return SPREAD_WIDE
    return SPREAD_VERY_WIDE


def _conf_band(v: float) -> str:
    if v < 6.5:
        return CONF_LOW
    if v < 7.5:
        return CONF_MEDIUM
    if v <= 8.5:
        return CONF_HIGH
    return CONF_VERY_HIGH


def _chain_band(v: float) -> str:
    if v < 0.4:
        return CHAIN_LOW
    if v <= 0.7:
        return CHAIN_MEDIUM
    return CHAIN_HIGH


def _oi_imbalance_band(ce_oi: int, pe_oi: int) -> str:
    total = ce_oi + pe_oi
    if total == 0:
        return OI_UNAVAILABLE
    imb = (ce_oi - pe_oi) / total  # +1 = all CE, -1 = all PE
    if imb > 0.3:
        return OI_HEAVY_CALL
    if imb > 0.1:
        return OI_SLIGHT_CALL
    if imb >= -0.1:
        return OI_BALANCED
    if imb >= -0.3:
        return OI_SLIGHT_PUT
    return OI_HEAVY_PUT
