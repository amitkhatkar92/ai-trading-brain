"""
opportunity_engine/historical_behaviour_engine.py
===================================================
KLP-003 — Historical Behaviour Engine

Consumes COMPLETED KLP outcomes (KNOWLEDGE_OBSERVATION + OUTCOME_UPDATE pairs)
and produces empirical behaviour profiles via a hierarchical evidence model.

SAFETY CONTRACT
---------------
• broker_calls = 0
• orders = 0, modifications = 0, cancellations = 0
• PAPER_TRADING state: read-only, never changed
• LIVE_TRADING_AUTHORIZED: never set, never checked, never changed
• No mutations to StrategyLab, RiskControl, DecisionEngine, or OrderManager
• no_lookahead = True on every output — entry = reference_entry frozen at scan time
• Read-only with respect to the production trading pipeline

HIERARCHICAL EVIDENCE MODEL
-----------------------------
Level 1: symbol + direction + regime + comparable context  (ATR band + conf band)
Level 2: symbol + direction
Level 3: sector + direction + regime
Level 4: regime + direction  (broad market, same regime)
Level 5: sector + direction
Level 6: broad market + direction (any regime)
Level 7: ATR/scanner fallback (no learned data)

EVIDENCE TIERS (observation count)
------------------------------------
Tier 0:  0– 9   no meaningful local evidence
Tier 1: 10–19   weak
Tier 2: 20–49   developing
Tier 3: 50–99   useful
Tier 4: 100–249 strong developing
Tier 5: 250–499 strong
Tier 6: 500+    high-volume

EFFECTIVE SAMPLE SIZE
---------------------
ESS = sum(recency_weight(obs)) for all relevant observations.
Recency weight uses a half-life of 90 trading days (configurable).
This correctly penalises stale data even when raw count is large.

STABILITY
---------
If recent 25% of observations (by date) materially contradicts the
historical 75%, the evidence is flagged UNSTABLE or DEVELOPING.
"""
from __future__ import annotations

import json
import math
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .hbe_models import (
    BehaviourMetrics,
    BehaviourProfile,
    COMPLETED_OUTCOMES,
    evidence_tier,
    KnowledgeScoreV2Preview,
    OutcomeRecord,
    STOP_HIT,
    TARGET_HIT,
    TIER_LABELS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_VERSION              = "HBE_v1"
_DEFAULT_DATA_DIR     = Path(__file__).parent.parent / "data" / "klp"
_HBE_OUTPUT_DIR       = Path(__file__).parent.parent / "data" / "klp" / "historical_behaviour"

_HALF_LIFE_DAYS       = 90    # recency weight half-life (trading days)
_ATR_BAND_TOLERANCE   = 0.30  # ±30% ATR-pct for Level-1 "comparable context" filter
_CONF_BAND_TOLERANCE  = 2.0   # ±2 confidence units for Level-1 matching
_MIN_OBS_FOR_PROBS    = 5     # minimum obs to compute probabilities
_MIN_OBS_FOR_TIME     = 5     # minimum obs with event to compute time metrics
_STABILITY_RECENT_FRAC = 0.25  # last 25% of obs by date = "recent" for stability check
_STABILITY_UNSTABLE   = 0.20   # hit-rate difference above this → UNSTABLE
_STABILITY_DEVELOPING = 0.10   # difference above this → DEVELOPING

# Evidence source labels (also used as target/stop source)
_L1 = "SYMBOL_DIRECTION_REGIME_CONTEXT"
_L2 = "SYMBOL_DIRECTION"
_L3 = "SECTOR_DIRECTION_REGIME"
_L4 = "REGIME_DIRECTION"
_L5 = "SECTOR_DIRECTION"
_L6 = "BROAD_MARKET_DIRECTION"
_L7 = "ATR_FALLBACK"

_LEVEL_SOURCES = [None, _L1, _L2, _L3, _L4, _L5, _L6, _L7]


# ─────────────────────────────────────────────────────────────────────────────
# Sector lookup — covers the symbols that appear in KLP observations
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL_SECTOR: Dict[str, str] = {
    # Banking & Financial
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "BANKBARODA": "BANK", "INDUSINDBK": "BANK", "AUBANK": "BANK",
    "BANDHANBNK": "BANK", "FEDERALBNK": "BANK", "PNB": "BANK",
    "HDFCAMC": "FINSERVICES", "ANGELONE": "FINSERVICES", "BAJAJFINSV": "FINSERVICES",
    "BAJFINANCE": "FINSERVICES", "MUTHOOTFIN": "FINSERVICES",
    # IT
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "TECHM": "IT", "HCLTECH": "IT",
    "LTTS": "IT", "MPHASIS": "IT", "COFORGE": "IT", "PERSISTENT": "IT",
    # Energy
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "BPCL": "ENERGY", "HPCL": "ENERGY",
    "ADANIGREEN": "ENERGY", "ADANIPOWER": "ENERGY", "NTPC": "ENERGY",
    "POWERGRID": "ENERGY", "TATAPOWER": "ENERGY", "NHPC": "ENERGY",
    "COALINDIA": "ENERGY", "NMDC": "METALS",
    # Auto
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
    "EICHERMOT": "AUTO", "HEROMOTOCO": "AUTO", "ASHOKLEY": "AUTO",
    # Pharma
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA",
    "LUPIN": "PHARMA", "DIVISLAB": "PHARMA", "BIOCON": "PHARMA", "ALKEM": "PHARMA",
    # FMCG
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG", "TATACONSUM": "FMCG",
    "GODREJCP": "FMCG", "NYKAA": "FMCG",
    # Steel / Metals
    "TATASTEEL": "METALS", "JSWSTEEL": "METALS", "HINDALCO": "METALS",
    "VEDL": "METALS", "APLAPOLLO": "METALS",
    # Real Estate
    "PRESTIGE": "REALTY", "DLF": "REALTY", "LODHA": "REALTY", "SOBHA": "REALTY",
    "GODREJPROP": "REALTY",
    # Telecom
    "BHARTIARTL": "TELECOM", "IDEA": "TELECOM",
    # Consumer / Misc
    "ASIANPAINT": "CONSUMER", "HAVELLS": "CONSUMER", "VOLTAS": "CONSUMER",
    "TITAN": "CONSUMER", "CUMMINSIND": "CONSUMER", "INOXWIND": "CONSUMER",
    "FORTIS": "HEALTHCARE", "HDFCLIFE": "INSURANCE",
    # Index
    "NIFTY": "INDEX", "BANKNIFTY": "INDEX",
}


def _get_sector(symbol: str) -> str:
    return _SYMBOL_SECTOR.get(symbol.upper().strip(), "UNKNOWN")


# ─────────────────────────────────────────────────────────────────────────────
# Recency weighting
# ─────────────────────────────────────────────────────────────────────────────

def _recency_weight(trading_date_str: str, reference_date: date, half_life: int = _HALF_LIFE_DAYS) -> float:
    """
    Exponential decay weight: w = 2^(-delta / half_life).
    Future dates (delta < 0) get weight 1.0.
    """
    try:
        td = date.fromisoformat(trading_date_str)
        delta = (reference_date - td).days
        if delta <= 0:
            return 1.0
        return 2.0 ** (-delta / half_life)
    except (ValueError, TypeError):
        return 0.5  # unknown date: neutral weight


# ─────────────────────────────────────────────────────────────────────────────
# Statistical helpers (no scipy/numpy — stdlib only)
# ─────────────────────────────────────────────────────────────────────────────

def _percentile(values: List[float], p: float) -> Optional[float]:
    """Compute p-th percentile [0–100] of a sorted or unsorted list."""
    vs = [v for v in values if v is not None]
    if not vs:
        return None
    vs.sort()
    n = len(vs)
    if n == 1:
        return vs[0]
    idx = (p / 100.0) * (n - 1)
    lo = int(idx)
    hi = lo + 1
    frac = idx - lo
    hi = min(hi, n - 1)
    return round(vs[lo] * (1 - frac) + vs[hi] * frac, 4)


def _safe_prob(numerator: int, denominator: int) -> Optional[float]:
    if denominator < _MIN_OBS_FOR_PROBS:
        return None
    return round(numerator / denominator, 4)


def _effective_sample_size(records: List[OutcomeRecord], reference_date: date) -> float:
    return sum(_recency_weight(r.trading_date, reference_date) for r in records)


# ─────────────────────────────────────────────────────────────────────────────
# Trading days between two date strings (approximation: Mon–Fri, no holidays)
# ─────────────────────────────────────────────────────────────────────────────

def _trading_days_between(start_str: Optional[str], end_str: Optional[str]) -> Optional[int]:
    if not start_str or not end_str:
        return None
    try:
        s = date.fromisoformat(start_str)
        e = date.fromisoformat(end_str)
        if e < s:
            return None
        count = 0
        cur = s
        while cur <= e:
            if cur.weekday() < 5:
                count += 1
            cur = date.fromordinal(cur.toordinal() + 1)
        # Subtract 1 because we count from start+1 (t+0 is observation day)
        return max(count - 1, 1)
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Stability detection
# ─────────────────────────────────────────────────────────────────────────────

def _stability_status(records: List[OutcomeRecord]) -> Tuple[str, Optional[float], Optional[float]]:
    """
    Returns (status, recent_hit_rate, historical_hit_rate).
    Splits records by date: last STABILITY_RECENT_FRAC = recent, rest = historical.
    """
    if len(records) < 10:
        return "insufficient_data", None, None

    sorted_recs = sorted(records, key=lambda r: r.trading_date)
    split_idx = max(1, int(len(sorted_recs) * (1 - _STABILITY_RECENT_FRAC)))
    historical = sorted_recs[:split_idx]
    recent     = sorted_recs[split_idx:]

    if len(recent) < 5 or len(historical) < 5:
        return "insufficient_data", None, None

    def hit_rate(recs: List[OutcomeRecord]) -> float:
        hits = sum(1 for r in recs if r.first_event == TARGET_HIT)
        return hits / len(recs)

    h_rate = hit_rate(historical)
    r_rate = hit_rate(recent)
    diff   = abs(r_rate - h_rate)

    if diff >= _STABILITY_UNSTABLE:
        status = "unstable"
    elif diff >= _STABILITY_DEVELOPING:
        status = "developing"
    else:
        status = "stable"

    return status, round(r_rate, 4), round(h_rate, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_metrics(
    records: List[OutcomeRecord],
    evidence_level: int,
    evidence_source: str,
    fallback_level: int,
    reference_date: date,
) -> BehaviourMetrics:
    """
    Compute all behaviour metrics from a filtered list of OutcomeRecords.
    Never raises — all fields default to None on insufficient data.
    """
    n = len(records)
    ess = _effective_sample_size(records, reference_date)
    tier = evidence_tier(n)

    oldest = min((r.trading_date for r in records), default=None)
    newest = max((r.trading_date for r in records), default=None)

    # ── Stability ─────────────────────────────────────────────────────────────
    stability, recent_hr, hist_hr = _stability_status(records)

    # ── Probabilities ─────────────────────────────────────────────────────────
    with_outcomes = [r for r in records if r.first_event in COMPLETED_OUTCOMES]
    n_out = len(with_outcomes)

    n_target  = sum(1 for r in with_outcomes if r.first_event == TARGET_HIT)
    n_stop    = sum(1 for r in with_outcomes if r.first_event == STOP_HIT)
    n_expired = sum(1 for r in with_outcomes if r.first_event not in (TARGET_HIT, STOP_HIT))

    target_prob  = _safe_prob(n_target,  n_out)
    stop_prob    = _safe_prob(n_stop,    n_out)
    expired_prob = _safe_prob(n_expired, n_out)

    # positive move: directional t5 > 0
    t5_vals = [r.directional_t5 for r in records if r.directional_t5 is not None]
    pos_move_prob = _safe_prob(sum(1 for v in t5_vals if v > 0), len(t5_vals)) if len(t5_vals) >= _MIN_OBS_FOR_PROBS else None

    # ── Move distributions ────────────────────────────────────────────────────
    fav_vals = [r.favourable_ret for r in records if r.favourable_ret is not None]
    adv_vals = [r.adverse_ret    for r in records if r.adverse_ret    is not None]
    mfe_vals = [r.favourable_ret for r in records if r.favourable_ret is not None]  # same

    fav_p25 = _percentile(fav_vals, 25)
    fav_p50 = _percentile(fav_vals, 50)
    fav_p75 = _percentile(fav_vals, 75)
    adv_p25 = _percentile(adv_vals, 25)
    adv_p50 = _percentile(adv_vals, 50)
    adv_p75 = _percentile(adv_vals, 75)

    exp_p25 = _percentile(mfe_vals, 25)
    exp_p50 = _percentile(mfe_vals, 50)
    exp_p75 = _percentile(mfe_vals, 75)

    # ── T+N returns ───────────────────────────────────────────────────────────
    dt1 = [r.directional_t1 for r in records if r.directional_t1 is not None]
    dt3 = [r.directional_t3 for r in records if r.directional_t3 is not None]
    dt5 = [r.directional_t5 for r in records if r.directional_t5 is not None]

    t1p25, t1p50, t1p75 = _percentile(dt1, 25), _percentile(dt1, 50), _percentile(dt1, 75)
    t3p25, t3p50, t3p75 = _percentile(dt3, 25), _percentile(dt3, 50), _percentile(dt3, 75)
    t5p25, t5p50, t5p75 = _percentile(dt5, 25), _percentile(dt5, 50), _percentile(dt5, 75)

    # ── Threshold probabilities ────────────────────────────────────────────────
    def _thresh_prob(vals: List[float], threshold: float) -> Optional[float]:
        if len(vals) < _MIN_OBS_FOR_PROBS:
            return None
        return round(sum(1 for v in vals if v >= threshold) / len(vals), 4)

    prob_1_t1 = _thresh_prob(dt1, 1.0)
    prob_1_t3 = _thresh_prob(dt3, 1.0)
    prob_1_t5 = _thresh_prob(dt5, 1.0)
    prob_2_t1 = _thresh_prob(dt1, 2.0)
    prob_2_t3 = _thresh_prob(dt3, 2.0)
    prob_2_t5 = _thresh_prob(dt5, 2.0)
    prob_3_t5 = _thresh_prob(dt5, 3.0)
    prob_5_t5 = _thresh_prob(dt5, 5.0)

    # ── Time to first event ────────────────────────────────────────────────────
    target_times = [r.days_to_event for r in with_outcomes
                    if r.first_event == TARGET_HIT and r.days_to_event is not None]
    stop_times   = [r.days_to_event for r in with_outcomes
                    if r.first_event == STOP_HIT   and r.days_to_event is not None]
    all_times    = [r.days_to_event for r in with_outcomes if r.days_to_event is not None]

    tt_p25 = _percentile(target_times, 25) if len(target_times) >= _MIN_OBS_FOR_TIME else None
    tt_p50 = _percentile(target_times, 50) if len(target_times) >= _MIN_OBS_FOR_TIME else None
    tt_p75 = _percentile(target_times, 75) if len(target_times) >= _MIN_OBS_FOR_TIME else None
    ts_p25 = _percentile(stop_times,   25) if len(stop_times)   >= _MIN_OBS_FOR_TIME else None
    ts_p50 = _percentile(stop_times,   50) if len(stop_times)   >= _MIN_OBS_FOR_TIME else None
    ts_p75 = _percentile(stop_times,   75) if len(stop_times)   >= _MIN_OBS_FOR_TIME else None

    d_p25 = _percentile(all_times, 25) if len(all_times) >= _MIN_OBS_FOR_TIME else None
    d_p50 = _percentile(all_times, 50) if len(all_times) >= _MIN_OBS_FOR_TIME else None
    d_p75 = _percentile(all_times, 75) if len(all_times) >= _MIN_OBS_FOR_TIME else None

    # ── Historical target/stop offsets ────────────────────────────────────────
    # Compute as % move from entry for TARGET_HIT outcomes
    tgt_offsets = []
    stp_offsets = []
    for r in with_outcomes:
        if r.reference_entry > 0:
            if r.target_hit and r.knowledge_target > 0:
                tgt_offsets.append(abs(r.knowledge_target - r.reference_entry) / r.reference_entry * 100)
            if r.stop_hit and r.knowledge_stop > 0:
                stp_offsets.append(abs(r.reference_entry - r.knowledge_stop) / r.reference_entry * 100)

    tgt_offset_p50 = _percentile(tgt_offsets, 50) if len(tgt_offsets) >= _MIN_OBS_FOR_PROBS else None
    stp_offset_p50 = _percentile(stp_offsets, 50) if len(stp_offsets) >= _MIN_OBS_FOR_PROBS else None

    def _src_conf(val, n_samples) -> Tuple[str, str]:
        if val is None or n_samples < _MIN_OBS_FOR_PROBS:
            return "ATR_FALLBACK", "INSUFFICIENT"
        tier_n = evidence_tier(n_samples)
        if tier_n >= 4:
            return "EMPIRICAL", "HIGH"
        if tier_n >= 2:
            return "EMPIRICAL", "MEDIUM"
        return "EMPIRICAL", "LOW"

    tgt_source, tgt_conf = _src_conf(tgt_offset_p50, len(tgt_offsets))
    stp_source, stp_conf = _src_conf(stp_offset_p50, len(stp_offsets))

    # ── Composite confidence ──────────────────────────────────────────────────
    confidence = _compute_confidence(tier, stability, ess)

    return BehaviourMetrics(
        observation_count=n,
        relevant_sample_size=n,
        effective_sample_size=round(ess, 2),
        oldest_observation=oldest,
        newest_observation=newest,
        evidence_tier=tier,
        evidence_tier_label=TIER_LABELS.get(tier, "UNKNOWN"),
        evidence_level=evidence_level,
        evidence_source=evidence_source,
        fallback_level=fallback_level,
        confidence=confidence,
        positive_move_probability=pos_move_prob,
        target_hit_probability=target_prob,
        stop_first_probability=stop_prob,
        expired_probability=expired_prob,
        favourable_move_p25=fav_p25,
        favourable_move_p50=fav_p50,
        favourable_move_p75=fav_p75,
        adverse_move_p25=adv_p25,
        adverse_move_p50=adv_p50,
        adverse_move_p75=adv_p75,
        time_to_target_p25=tt_p25,
        time_to_target_p50=tt_p50,
        time_to_target_p75=tt_p75,
        time_to_stop_p25=ts_p25,
        time_to_stop_p50=ts_p50,
        time_to_stop_p75=ts_p75,
        expected_move_p25=exp_p25,
        expected_move_p50=exp_p50,
        expected_move_p75=exp_p75,
        t1_ret_p25=t1p25, t1_ret_p50=t1p50, t1_ret_p75=t1p75,
        t3_ret_p25=t3p25, t3_ret_p50=t3p50, t3_ret_p75=t3p75,
        t5_ret_p25=t5p25, t5_ret_p50=t5p50, t5_ret_p75=t5p75,
        prob_move_1pct_by_t1=prob_1_t1,
        prob_move_1pct_by_t3=prob_1_t3,
        prob_move_1pct_by_t5=prob_1_t5,
        prob_move_2pct_by_t1=prob_2_t1,
        prob_move_2pct_by_t3=prob_2_t3,
        prob_move_2pct_by_t5=prob_2_t5,
        prob_move_3pct_by_t5=prob_3_t5,
        prob_move_5pct_by_t5=prob_5_t5,
        expected_days_p25=d_p25,
        expected_days_p50=d_p50,
        expected_days_p75=d_p75,
        knowledge_target_offset_p50=tgt_offset_p50,
        knowledge_stop_offset_p50=stp_offset_p50,
        target_source=tgt_source,
        stop_source=stp_source,
        target_confidence=tgt_conf,
        stop_confidence=stp_conf,
        stability_status=stability,
        recent_hit_rate=recent_hr,
        historical_hit_rate=hist_hr,
    )


def _compute_confidence(tier: int, stability: str, ess: float) -> float:
    """
    Composite confidence [0–1].
    tier_score:      0.5 × (tier / 6)
    stability_bonus: 0.3 × (1.0 for stable, 0.5 for developing, 0.0 otherwise)
    ess_score:       0.2 × min(ess / 100, 1.0)
    """
    tier_score = 0.5 * (tier / 6.0)
    stab_map   = {"stable": 1.0, "developing": 0.5, "unstable": 0.0, "insufficient_data": 0.0}
    stab_score = 0.3 * stab_map.get(stability, 0.0)
    ess_score  = 0.2 * min(ess / 100.0, 1.0)
    return round(tier_score + stab_score + ess_score, 4)


# ─────────────────────────────────────────────────────────────────────────────
# ATR fallback metrics (Level 7)
# ─────────────────────────────────────────────────────────────────────────────

def _atr_fallback_metrics() -> BehaviourMetrics:
    """Return a fully typed Level-7 fallback with no empirical data."""
    return BehaviourMetrics(
        observation_count=0, relevant_sample_size=0, effective_sample_size=0.0,
        oldest_observation=None, newest_observation=None,
        evidence_tier=0, evidence_tier_label=TIER_LABELS[0],
        evidence_level=7, evidence_source=_L7,
        fallback_level=7, confidence=0.0,
        positive_move_probability=None, target_hit_probability=None,
        stop_first_probability=None, expired_probability=None,
        favourable_move_p25=None, favourable_move_p50=None, favourable_move_p75=None,
        adverse_move_p25=None, adverse_move_p50=None, adverse_move_p75=None,
        time_to_target_p25=None, time_to_target_p50=None, time_to_target_p75=None,
        time_to_stop_p25=None, time_to_stop_p50=None, time_to_stop_p75=None,
        expected_move_p25=None, expected_move_p50=None, expected_move_p75=None,
        t1_ret_p25=None, t1_ret_p50=None, t1_ret_p75=None,
        t3_ret_p25=None, t3_ret_p50=None, t3_ret_p75=None,
        t5_ret_p25=None, t5_ret_p50=None, t5_ret_p75=None,
        prob_move_1pct_by_t1=None, prob_move_1pct_by_t3=None, prob_move_1pct_by_t5=None,
        prob_move_2pct_by_t1=None, prob_move_2pct_by_t3=None, prob_move_2pct_by_t5=None,
        prob_move_3pct_by_t5=None, prob_move_5pct_by_t5=None,
        expected_days_p25=None, expected_days_p50=None, expected_days_p75=None,
        knowledge_target_offset_p50=None, knowledge_stop_offset_p50=None,
        target_source=_L7, stop_source=_L7,
        target_confidence="INSUFFICIENT", stop_confidence="INSUFFICIENT",
        stability_status="insufficient_data",
        recent_hit_rate=None, historical_hit_rate=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# KLP file loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_klp_file(path: Path) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Parse one KLP_YYYY-MM-DD.jsonl file.
    Returns (obs_map: obs_id→record, outcome_map: obs_id→record).
    """
    obs_map: Dict[str, Dict] = {}
    outcome_map: Dict[str, Dict] = {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                et = rec.get("event_type", "")
                oid = rec.get("obs_id", "")
                if not oid:
                    continue
                if et == "KNOWLEDGE_OBSERVATION":
                    obs_map[oid] = rec
                elif et == "OUTCOME_UPDATE":
                    outcome_map[oid] = rec
    except OSError:
        pass
    return obs_map, outcome_map


def _join_and_parse(
    obs_map: Dict[str, Dict],
    outcome_map: Dict[str, Dict],
    trading_date: str,
) -> List[OutcomeRecord]:
    """
    Join observations with their outcomes.
    Only records with COMPLETED outcomes are returned.
    """
    records: List[OutcomeRecord] = []
    for oid, obs in obs_map.items():
        outcome = outcome_map.get(oid)
        if not outcome:
            continue
        first_event = outcome.get("first_event", "")
        if first_event not in COMPLETED_OUTCOMES:
            continue

        symbol    = (obs.get("symbol") or "").strip().upper()
        direction = (obs.get("direction") or "BUY").upper()
        regime    = (obs.get("regime") or "").upper()
        entry     = float(obs.get("reference_entry") or 0.0)
        target    = float(obs.get("knowledge_target") or 0.0)
        stop      = float(obs.get("knowledge_stop_loss") or 0.0)
        atr       = float(obs.get("atr") or 0.0)
        atr_pct   = float(obs.get("atr_pct") or 0.0)

        if not atr_pct and atr > 0 and entry > 0:
            atr_pct = round(atr / entry * 100, 4)

        days_to_event = _trading_days_between(
            trading_date, outcome.get("first_event_day")
        )

        records.append(OutcomeRecord(
            obs_id=oid,
            trading_date=trading_date,
            symbol=symbol,
            direction=direction,
            regime=regime,
            sector=_get_sector(symbol),
            reference_entry=entry,
            knowledge_target=target,
            knowledge_stop=stop,
            atr=atr,
            atr_pct=atr_pct,
            scanner_confidence=float(obs.get("scanner_confidence") or 0.0),
            candidate_score=float(obs.get("candidate_score") or 0.0),
            knowledge_score=float(obs.get("knowledge_score") or 0.0),
            knowledge_rr=float(obs.get("knowledge_RR") or 0.0),
            first_event=first_event,
            first_event_day=outcome.get("first_event_day"),
            target_hit=bool(outcome.get("target_hit", False)),
            stop_hit=bool(outcome.get("stop_hit", False)),
            t1_ret_pct=_float_or_none(outcome.get("t1_ret_pct")),
            t3_ret_pct=_float_or_none(outcome.get("t3_ret_pct")),
            t5_ret_pct=_float_or_none(outcome.get("t5_ret_pct")),
            mfe_pct=_float_or_none(outcome.get("mfe_pct")),
            mae_pct=_float_or_none(outcome.get("mae_pct")),
            days_to_event=days_to_event,
            no_lookahead=True,
            source_type=str(obs.get("source_type") or "LIVE"),
            validation_partition=str(obs.get("validation_partition") or ""),
        ))
    return records


def _float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# V2 Score preview
# ─────────────────────────────────────────────────────────────────────────────

def _compute_v2_preview(
    v1_score:    float,
    metrics:     BehaviourMetrics,
    query_direction: str,
) -> KnowledgeScoreV2Preview:
    """
    Compute KNOWLEDGE_RESEARCH_SCORE_V2_PREVIEW.

    Weights:
        40%  V1 scanner features  (scanner_component = v1_score / 1.0)
        30%  empirical target probability
        20%  empirical expected move (p50 magnitude)
        10%  regime × sector historical alignment (positive_move_probability)

    Fallback: if evidence_level >= 6 or confidence < 0.05, return v1 score.
    """
    using_fallback = metrics.evidence_level >= 6 or metrics.confidence < 0.05

    scanner_component = v1_score  # already normalised 0–1 by V1 formula

    # Empirical target probability component (0→0, 1→1)
    tp = metrics.target_hit_probability
    emp_target_component = float(tp) if tp is not None else 0.0

    # Empirical move magnitude component: cap at 5%
    emp50 = metrics.expected_move_p50
    if emp50 is not None:
        emp_move_component = min(abs(emp50) / 5.0, 1.0)
    else:
        emp_move_component = 0.0

    # Historical alignment: positive_move_probability
    pm = metrics.positive_move_probability
    hist_align_component = float(pm) if pm is not None else 0.0

    if using_fallback:
        v2 = v1_score
        using_fallback = True
    else:
        v2 = (
            0.40 * scanner_component +
            0.30 * emp_target_component +
            0.20 * emp_move_component +
            0.10 * hist_align_component
        )
        v2 = round(min(max(v2, 0.0), 1.0), 4)

    return KnowledgeScoreV2Preview(
        score_v2=v2,
        score_v1=round(v1_score, 4),
        v2_delta=round(v2 - v1_score, 4),
        scanner_component=round(scanner_component, 4),
        empirical_target_component=round(emp_target_component, 4),
        target_hit_probability=metrics.target_hit_probability,
        empirical_move_component=round(emp_move_component, 4),
        expected_move_p50=emp50,
        historical_alignment_component=round(hist_align_component, 4),
        evidence_level=metrics.evidence_level,
        evidence_tier=metrics.evidence_tier,
        evidence_confidence=metrics.confidence,
        using_fallback=using_fallback,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class HistoricalBehaviourEngine:
    """
    KLP-003 — Historical Behaviour Engine.

    Usage:
        hbe = HistoricalBehaviourEngine()
        n = hbe.load_outcomes()          # load all KLP files
        profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL")

    For testing, pass outcomes directly:
        hbe = HistoricalBehaviourEngine()
        hbe._outcomes = [OutcomeRecord(...), ...]
        profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")

    broker_calls = 0 always.
    """

    # ── Minimum observation counts per level for "use this level" ─────────────
    # The engine tries each level in order and uses the first with >= this count.
    # Level 1 needs only 5 because it's highly specific.
    _LEVEL_MIN_OBS = [None, 5, 5, 10, 10, 15, 15, 0]

    def __init__(
        self,
        data_dir:       Optional[Path]  = None,
        reference_date: Optional[date]  = None,
        half_life_days: int             = _HALF_LIFE_DAYS,
    ) -> None:
        self._data_dir      = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._reference_date = reference_date or date.today()
        self._half_life     = half_life_days
        self._outcomes:     List[OutcomeRecord] = []
        self._loaded        = False
        # Safety invariants — never changed by this class
        self.broker_calls   = 0
        self.orders         = 0

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_outcomes(self, klp_dir: Optional[Path] = None) -> int:
        """
        Scan all KLP_*.jsonl files and load completed outcomes.
        Returns total completed outcomes loaded.
        """
        base = klp_dir or self._data_dir
        all_records: List[OutcomeRecord] = []
        seen_obs_ids: set = set()

        try:
            for klp_file in sorted(base.glob("KLP_*.jsonl")):
                # Extract date from filename: KLP_YYYY-MM-DD.jsonl
                stem = klp_file.stem  # "KLP_2026-08-20"
                parts = stem.split("_", 1)
                trading_date = parts[1] if len(parts) == 2 else stem
                obs_map, outcome_map = _load_klp_file(klp_file)
                for rec in _join_and_parse(obs_map, outcome_map, trading_date):
                    if rec.obs_id not in seen_obs_ids:
                        all_records.append(rec)
                        seen_obs_ids.add(rec.obs_id)
        except OSError:
            pass

        self._outcomes = all_records
        self._loaded = True
        return len(all_records)

    def get_outcome_count(self) -> int:
        return len(self._outcomes)

    def get_symbol_counts(self) -> Dict[str, int]:
        """Return {symbol: count} for diagnostic purposes."""
        counts: Dict[str, int] = {}
        for r in self._outcomes:
            counts[r.symbol] = counts.get(r.symbol, 0) + 1
        return counts

    def load_bootstrap_records(self, records: List[OutcomeRecord]) -> int:
        """
        D15-003: Inject historical bootstrap OutcomeRecords into the evidence pool.

        Only records with source_type='HISTORICAL' are accepted to prevent
        accidental injection of live/paper data through this path.
        Returns the count of records successfully injected.
        """
        valid = [r for r in records if r.source_type == "HISTORICAL"]
        seen  = {r.obs_id for r in self._outcomes}
        added = 0
        for r in valid:
            if r.obs_id not in seen:
                self._outcomes.append(r)
                seen.add(r.obs_id)
                added += 1
        return added

    # ── Profile ───────────────────────────────────────────────────────────────

    def get_behaviour_profile(
        self,
        symbol:           str,
        direction:        str,
        regime:           Optional[str]   = None,
        sector:           Optional[str]   = None,
        query_atr_pct:    Optional[float] = None,
        query_confidence: Optional[float] = None,
        v1_score:         float           = 0.0,
        query_entry:      Optional[float] = None,
    ) -> BehaviourProfile:
        """
        Return an empirical behaviour profile via hierarchical evidence.

        Parameters:
            symbol:           NSE symbol (e.g. "TATASTEEL")
            direction:        "BUY" or "SELL" / "SHORT"
            regime:           Current market regime ("BULL", "BEAR", "RANGE", "VOLATILE")
            sector:           Override sector (default: auto-detected from symbol)
            query_atr_pct:    ATR% of signal (for Level-1 context matching)
            query_confidence: Scanner confidence of signal (0–10)
            v1_score:         Current KNOWLEDGE_RESEARCH_SCORE_v1 (for V2 delta)
            query_entry:      Signal entry price (for applying % offsets)

        Returns: BehaviourProfile — always non-None. Falls back to Level 7 if no data.
        """
        sym = symbol.upper().strip()
        dir_norm = direction.upper()
        regime_norm = (regime or "").upper()
        sector_norm = sector or _get_sector(sym)

        metrics, level_used = self._find_best_evidence(
            sym, dir_norm, regime_norm, sector_norm, query_atr_pct, query_confidence
        )

        v2_preview = _compute_v2_preview(v1_score, metrics, dir_norm)

        # Scanner ATR-based target/stop as reference
        atr_target_pct: Optional[float] = None
        atr_stop_pct:   Optional[float] = None

        # Knowledge target/stop: apply empirical % offset to entry
        kt: Optional[float] = None
        ks: Optional[float] = None
        tgt_src = metrics.target_source
        stp_src = metrics.stop_source

        if query_entry and query_entry > 0:
            if metrics.knowledge_target_offset_p50 is not None and tgt_src == "EMPIRICAL":
                offset_pct = metrics.knowledge_target_offset_p50 / 100.0
                if dir_norm in ("BUY", "LONG"):
                    kt = round(query_entry * (1 + offset_pct), 2)
                else:
                    kt = round(query_entry * (1 - offset_pct), 2)
                tgt_src = f"EMPIRICAL_L{level_used}"
            if metrics.knowledge_stop_offset_p50 is not None and stp_src == "EMPIRICAL":
                offset_pct = metrics.knowledge_stop_offset_p50 / 100.0
                if dir_norm in ("BUY", "LONG"):
                    ks = round(query_entry * (1 - offset_pct), 2)
                else:
                    ks = round(query_entry * (1 + offset_pct), 2)
                stp_src = f"EMPIRICAL_L{level_used}"

        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return BehaviourProfile(
            query_symbol=sym,
            query_direction=dir_norm,
            query_regime=regime_norm or None,
            query_sector=sector_norm,
            metrics=metrics,
            score_v2_preview=v2_preview,
            atr_scanner_target_pct=atr_target_pct,
            atr_scanner_stop_pct=atr_stop_pct,
            knowledge_target=kt,
            knowledge_stop=ks,
            target_source=tgt_src,
            stop_source=stp_src,
            calculation_ts=now_ts,
            calculation_version=_VERSION,
            no_lookahead=True,
            broker_calls=0,
            orders=0,
        )

    # ── Hierarchical evidence search ──────────────────────────────────────────

    def _find_best_evidence(
        self,
        symbol:      str,
        direction:   str,
        regime:      str,
        sector:      str,
        atr_pct:     Optional[float],
        confidence:  Optional[float],
    ) -> Tuple[BehaviourMetrics, int]:
        """
        Try evidence levels 1–6. Use the first level with enough observations.
        Return (metrics, level_used).  Level 7 = ATR fallback.
        """
        if not self._outcomes:
            return _atr_fallback_metrics(), 7

        # Pre-filter: only records with matching direction (all levels share this)
        dir_records = [r for r in self._outcomes if r.direction == direction]
        if not dir_records:
            return _atr_fallback_metrics(), 7

        # Level 1: symbol + direction + regime + comparable ATR/confidence context
        if regime:
            l1 = [r for r in dir_records
                  if r.symbol == symbol and r.regime == regime
                  and _context_similar(r, atr_pct, confidence)]
            if len(l1) >= self._LEVEL_MIN_OBS[1]:
                return _compute_metrics(l1, 1, _L1, 1, self._reference_date), 1

        # Level 2: symbol + direction
        l2 = [r for r in dir_records if r.symbol == symbol]
        if len(l2) >= self._LEVEL_MIN_OBS[2]:
            return _compute_metrics(l2, 2, _L2, 2, self._reference_date), 2

        # Level 3: sector + direction + regime
        if regime and sector and sector != "UNKNOWN":
            l3 = [r for r in dir_records if r.sector == sector and r.regime == regime]
            if len(l3) >= self._LEVEL_MIN_OBS[3]:
                return _compute_metrics(l3, 3, _L3, 3, self._reference_date), 3

        # Level 4: regime + direction (broad, same regime)
        if regime:
            l4 = [r for r in dir_records if r.regime == regime]
            if len(l4) >= self._LEVEL_MIN_OBS[4]:
                return _compute_metrics(l4, 4, _L4, 4, self._reference_date), 4

        # Level 5: sector + direction
        if sector and sector != "UNKNOWN":
            l5 = [r for r in dir_records if r.sector == sector]
            if len(l5) >= self._LEVEL_MIN_OBS[5]:
                return _compute_metrics(l5, 5, _L5, 5, self._reference_date), 5

        # Level 6: broad market + direction
        if len(dir_records) >= self._LEVEL_MIN_OBS[6]:
            return _compute_metrics(dir_records, 6, _L6, 6, self._reference_date), 6

        # Level 7: ATR fallback
        return _atr_fallback_metrics(), 7

    # ── Diagnostic output ─────────────────────────────────────────────────────

    def write_daily_snapshot(self, output_dir: Optional[Path] = None) -> None:
        """
        D-008: Write a daily summary snapshot of the HBE state to disk.
        Idempotent — safe to call multiple times; overwrites today's file.
        Non-fatal — swallows all errors.
        """
        try:
            base = output_dir or _HBE_OUTPUT_DIR
            base.mkdir(parents=True, exist_ok=True)
            today_str = date.today().isoformat()
            snap_path = base / f"hbe_snapshot_{today_str}.json"
            symbol_counts = self.get_symbol_counts()
            snapshot = {
                "snapshot_date":    today_str,
                "ts_utc":           datetime.now(timezone.utc).isoformat(),
                "outcome_count":    len(self._outcomes),
                "symbol_count":     len(symbol_counts),
                "symbols":          symbol_counts,
                "loaded":           self._loaded,
                "version":          _VERSION,
            }
            import tempfile
            fd, tmp = tempfile.mkstemp(dir=str(base), prefix=".hbe_snap_", suffix=".tmp")
            try:
                with __import__("os").fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(snapshot, fh, indent=2)
                __import__("os").replace(tmp, str(snap_path))
            except Exception:
                try:
                    __import__("os").unlink(tmp)
                except OSError:
                    pass
                raise
        except Exception as exc:
            pass  # non-fatal

    def write_diagnostic_record(
        self,
        profile: BehaviourProfile,
        output_dir: Optional[Path] = None,
    ) -> None:
        try:
            base = output_dir or _HBE_OUTPUT_DIR
            base.mkdir(parents=True, exist_ok=True)
            ledger = base / "hbe_ledger.jsonl"
            record = {
                "ts_utc":             datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "symbol":             profile.query_symbol,
                "direction":          profile.query_direction,
                "regime":             profile.query_regime,
                "sector":             profile.query_sector,
                "observation_count":  profile.metrics.observation_count,
                "relevant_sample_size": profile.metrics.relevant_sample_size,
                "effective_sample_size": profile.metrics.effective_sample_size,
                "evidence_tier":      profile.metrics.evidence_tier,
                "evidence_tier_label": profile.metrics.evidence_tier_label,
                "evidence_level":     profile.metrics.evidence_level,
                "evidence_source":    profile.metrics.evidence_source,
                "fallback_level":     profile.metrics.fallback_level,
                "confidence":         profile.metrics.confidence,
                "positive_move_probability": profile.metrics.positive_move_probability,
                "target_hit_probability": profile.metrics.target_hit_probability,
                "stop_first_probability": profile.metrics.stop_first_probability,
                "favourable_move_p25": profile.metrics.favourable_move_p25,
                "favourable_move_p50": profile.metrics.favourable_move_p50,
                "favourable_move_p75": profile.metrics.favourable_move_p75,
                "adverse_move_p25": profile.metrics.adverse_move_p25,
                "adverse_move_p50": profile.metrics.adverse_move_p50,
                "adverse_move_p75": profile.metrics.adverse_move_p75,
                "time_to_target_p25": profile.metrics.time_to_target_p25,
                "time_to_target_p50": profile.metrics.time_to_target_p50,
                "time_to_target_p75": profile.metrics.time_to_target_p75,
                "time_to_stop_p25": profile.metrics.time_to_stop_p25,
                "time_to_stop_p50": profile.metrics.time_to_stop_p50,
                "time_to_stop_p75": profile.metrics.time_to_stop_p75,
                "expected_move_p25": profile.metrics.expected_move_p25,
                "expected_move_p50": profile.metrics.expected_move_p50,
                "expected_move_p75": profile.metrics.expected_move_p75,
                "knowledge_target_offset_p50": profile.metrics.knowledge_target_offset_p50,
                "knowledge_stop_offset_p50": profile.metrics.knowledge_stop_offset_p50,
                "knowledge_target": profile.knowledge_target,
                "knowledge_stop":   profile.knowledge_stop,
                "target_source":    profile.target_source,
                "stop_source":      profile.stop_source,
                "stability_status": profile.metrics.stability_status,
                "recent_hit_rate":  profile.metrics.recent_hit_rate,
                "historical_hit_rate": profile.metrics.historical_hit_rate,
                "expected_days_p25": profile.metrics.expected_days_p25,
                "expected_days_p50": profile.metrics.expected_days_p50,
                "expected_days_p75": profile.metrics.expected_days_p75,
                "score_v1":         profile.score_v2_preview.score_v1,
                "score_v2_preview": profile.score_v2_preview.score_v2,
                "v2_delta":         profile.score_v2_preview.v2_delta,
                "using_v1_fallback": profile.score_v2_preview.using_fallback,
                "calculation_version": profile.calculation_version,
                "no_lookahead":     True,
                "broker_calls":     0,
                "orders":           0,
            }
            with ledger.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception:
            pass  # non-fatal


# ─────────────────────────────────────────────────────────────────────────────
# Context similarity for Level-1 matching
# ─────────────────────────────────────────────────────────────────────────────

def _context_similar(
    rec:        OutcomeRecord,
    query_atr:  Optional[float],
    query_conf: Optional[float],
) -> bool:
    """
    True if the observation is contextually similar enough for Level-1 matching.
    ATR within ±30%, confidence within ±2 units.
    If either query parameter is None, that dimension is ignored.
    """
    if query_atr is not None and rec.atr_pct > 0:
        if abs(rec.atr_pct - query_atr) / max(query_atr, rec.atr_pct) > _ATR_BAND_TOLERANCE:
            return False
    if query_conf is not None and rec.scanner_confidence > 0:
        if abs(rec.scanner_confidence - query_conf) > _CONF_BAND_TOLERANCE:
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: get or create module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_hbe_singleton: Optional[HistoricalBehaviourEngine] = None


def get_hbe() -> HistoricalBehaviourEngine:
    """Return a loaded module-level singleton HBE."""
    global _hbe_singleton
    if _hbe_singleton is None:
        _hbe_singleton = HistoricalBehaviourEngine()
        _hbe_singleton.load_outcomes()
    return _hbe_singleton
