"""
cle_learning_executor/cle_research.py — Historical evidence research for Cat-E DNA candidates.

For each Cat-E action (symbol moved big, IIOS had zero DNA coverage) this module:
  1. Fetches 252 days of OHLCV for the symbol via yfinance.
  2. Computes simple features: momentum, volume ratio, intraday range.
  3. Identifies days where similar conditions preceded a threshold-magnitude move.
  4. Evaluates evidence quality: sample_count, win_rate, base_rate, lift.
  5. If evidence is sufficient, creates an InstitutionalDNA record with lifecycle=DISCOVERED.

SAFETY RULES (enforced in every function):
  - lifecycle is ALWAYS "DISCOVERED" — never "INSTITUTIONAL" or any promoted state.
  - No live trading variables are touched.
  - All exceptions are caught; callers receive a failed CLEResearchResult.
  - Idempotency: existing DISCOVERED DNA for the same symbol+direction+study is re-used,
    not duplicated.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# ── Lazy module-level imports (allow patching in tests) ───────────────────────
try:
    import yfinance as yf  # noqa: F401  (used via module reference)
except ImportError:
    yf = None  # type: ignore[assignment]

try:
    from market_learning.idr_repository import IDRRepository, IDRNotFoundError  # noqa: F401
    from market_learning.idr_models import InstitutionalDNA  # noqa: F401
except ImportError:
    IDRRepository    = None   # type: ignore[assignment,misc]
    IDRNotFoundError = Exception  # type: ignore[assignment,misc]
    InstitutionalDNA = None   # type: ignore[assignment]

# ── Minimum evidence thresholds ───────────────────────────────────────────────
MIN_SAMPLE       = 10      # need ≥ 10 historical occurrences of the trigger condition
MIN_WIN_RATE     = 0.50    # ≥ 50 % of occurrences lead to the target-direction move
MIN_LIFT         = 1.3     # signal win rate must be ≥ 1.3× the base rate
HISTORY_DAYS     = 365     # fetch ~1 calendar year of daily bars
MOVE_THRESHOLD   = 1.0     # minimum |daily_return_pct| to count as a "significant move"


# ── Result container ──────────────────────────────────────────────────────────

@dataclass
class CLEResearchResult:
    action_id:    str
    symbol:       str
    direction:    str           # "UP" or "DOWN"
    return_pct:   float         # trigger move that prompted Cat-E

    # Evidence quality
    sample_count: int   = 0
    base_rate:    float = 0.0   # P(|move| >= threshold) on random day
    win_rate:     float = 0.0   # P(threshold_direction_move | trigger_condition)
    lift:         float = 0.0   # win_rate / base_rate

    # Outcome
    status:       str   = "PENDING"   # CANDIDATE_CREATED | INSUFFICIENT_DATA | NO_ACTIONABLE_DNA | FAILED | SKIPPED
    dna_id:       Optional[str] = None
    reason:       str   = ""
    feature_name: str   = ""


# ── OHLCV fetch ───────────────────────────────────────────────────────────────

def _fetch_ohlcv(symbol: str, days: int = HISTORY_DAYS):
    """
    Fetch daily OHLCV for an NSE symbol using yfinance.
    Returns a pandas DataFrame with columns [Open, High, Low, Close, Volume]
    or None on failure.
    """
    try:
        import pandas as pd
        _yf = yf  # use the module-level yfinance reference
        if _yf is None:
            return None

        # NSE symbols need .NS suffix; indices like ^NSEI are passed as-is
        ticker = symbol if ("." in symbol or symbol.startswith("^")) else symbol + ".NS"

        end_dt   = date.today()
        start_dt = end_dt - timedelta(days=days)

        df = _yf.download(
            ticker,
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            progress=False,
            auto_adjust=True,
            timeout=12,
        )

        if df is None or df.empty:
            return None

        # Flatten MultiIndex columns (yfinance >= 0.2.28 behaviour)
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.copy()
                df.columns = df.columns.droplevel(level=-1)
                df = df.loc[:, ~df.columns.duplicated()]
        except Exception:
            pass

        # Keep only the columns we need
        needed = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
        if "Close" not in needed:
            return None

        return df[needed].dropna(how="all")

    except Exception as exc:
        log.warning("[CLE-Research] OHLCV fetch failed for %s: %s", symbol, exc)
        return None


# ── Feature computation ───────────────────────────────────────────────────────

def _compute_features(df):
    """
    Add technical features to the OHLCV DataFrame:
      daily_return  — percentage change from prior close
      momentum_5d   — 5-day return
      vol_ratio_20  — today volume / 20-day rolling average
      high_low_pct  — intraday range as % of close
      rsi_14        — 14-period RSI (DTA-RESEARCH-QUALITY-001)
      mom_accel     — change in 5-day momentum vs 5 days ago -- the same
                      formula already used/validated elsewhere in this
                      codebase (Selection Intelligence Phase 2C/2D)
      hv_20         — 20-day realized volatility (std of daily_return)
    Returns the augmented DataFrame (original is not mutated).
    """
    try:
        import pandas as pd

        df = df.copy()
        close  = df["Close"]
        volume = df.get("Volume", None)

        df["daily_return"] = close.pct_change() * 100.0
        df["momentum_5d"]  = close.pct_change(periods=5) * 100.0
        df["mom_accel"]    = df["momentum_5d"] - df["momentum_5d"].shift(5)
        df["hv_20"]        = df["daily_return"].rolling(20, min_periods=10).std()

        delta    = close.diff()
        gain     = delta.clip(lower=0)
        loss     = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, min_periods=14).mean()
        avg_loss = loss.ewm(com=13, min_periods=14).mean()
        rs       = avg_gain / avg_loss.replace(0, float("nan"))
        df["rsi_14"] = 100 - (100 / (1 + rs))

        if volume is not None:
            vol_ma20       = volume.rolling(20, min_periods=5).mean()
            df["vol_ratio_20"] = volume / vol_ma20.replace(0, 1)
        else:
            df["vol_ratio_20"] = 1.0

        if "High" in df.columns and "Low" in df.columns:
            df["high_low_pct"] = (df["High"] - df["Low"]) / close.replace(0, 1) * 100.0
        else:
            df["high_low_pct"] = 0.0

        return df.dropna(subset=["daily_return", "momentum_5d"])

    except Exception as exc:
        log.warning("[CLE-Research] Feature compute failed: %s", exc)
        return df


# ── Evidence assessment ───────────────────────────────────────────────────────

def _next_day_positions(df, trigger_idx):
    """
    Map each trigger-day index label to the NEXT trading day's index label,
    bounds-safe.

    Root cause of a real, reproducible bug (DTA-CLE-NEXTDAY-BOUNDS-001,
    found 2026-09-25 in a live EOD run): a trigger day that is itself the
    LAST row of *df* has no next day. The original inline pattern
    (`df.index.get_indexer(trigger_idx, method="pad") + 1`) always shifted
    every position by 1 with no upper-bound check, so when a trigger fell
    on the final row this produced position == len(df), which is out of
    bounds for a 0..len(df)-1 index and raised IndexError. Caught by the
    caller's own try/except (fail-safe, 0 evidence), but silently dropped
    that trigger day's evidence from the count instead of just excluding
    the one day with no valid outcome.

    Returns a list of index labels safe to pass to df.index for the
    next-day outcome lookup.
    """
    positions = df.index.get_indexer(trigger_idx, method="pad") + 1
    positions = positions[(positions >= 0) & (positions < len(df))]
    return df.index[positions]


def _assess_evidence(df, direction: str, trigger_return_pct: float):
    """
    Assess how often a volume/momentum spike precedes a large directional move.

    Trigger condition:
      - vol_ratio_20 > 1.5  (volume 50% above 20-day average)
      - momentum_5d in the target direction (positive for UP, negative for DOWN)

    Outcome (the next trading day):
      - |daily_return| >= MOVE_THRESHOLD AND in the correct direction

    Returns (sample_count, base_rate, win_rate, lift).
    """
    try:
        threshold = max(MOVE_THRESHOLD, abs(trigger_return_pct) * 0.5)

        # Base rate: P(|daily_return| >= threshold on any day)
        total_days  = len(df)
        large_moves = (df["daily_return"].abs() >= threshold).sum()
        base_rate   = large_moves / max(total_days, 1)

        # Trigger condition rows (shifted 1 forward so we measure next-day outcome)
        cond = (df["vol_ratio_20"] > 1.5)
        if direction.upper() == "UP":
            cond = cond & (df["momentum_5d"] > 0)
            outcome_mask = df["daily_return"] >= threshold
        else:
            cond = cond & (df["momentum_5d"] < 0)
            outcome_mask = df["daily_return"] <= -threshold

        # Shift trigger one row forward to get next-day outcome (bounds-safe)
        trigger_idx  = df.index[cond]
        next_day_idx = _next_day_positions(df, trigger_idx)
        # Filter to valid indices
        valid        = [i for i in next_day_idx if i in df.index]

        if len(valid) < MIN_SAMPLE:
            return len(valid), base_rate, 0.0, 0.0

        outcomes    = outcome_mask.reindex(valid).fillna(False)
        win_rate    = outcomes.sum() / len(outcomes)
        lift        = win_rate / max(base_rate, 0.001)

        return len(valid), base_rate, float(win_rate), float(lift)

    except Exception as exc:
        log.warning("[CLE-Research] Evidence assessment error: %s", exc)
        return 0, 0.0, 0.0, 0.0


# ── Certified fingerprint library (DTA-RESEARCH-QUALITY-001, revised) ─────
#
# Earlier revision of this module hand-invented 2 extra combinations
# alongside _assess_evidence()'s original volume+momentum condition. On
# review, that duplicated work this codebase already does properly
# elsewhere: Selection Intelligence Phase 2C/2D/7 independently discovers
# and statistically validates combinations against POOLED, cross-sectional
# data (hundreds of records across many symbols) with real promotion gates
# -- a much stronger basis than one hand-picked idea tested for the first
# time on a single stock. This module now REUSES that already-certified
# library directly instead of re-inventing combinations:
#   - data/discovered_fingerprints.json -- every fingerprint Phase 7 has
#     auto-promoted so far (grows over time, zero code change needed here
#     when a new one clears the bar).
#   - _STATIC_CERTIFIED_FINGERPRINT -- the original Phase 2D finding,
#     mirrored here as a plain data spec (kept in sync with
#     FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL in selection_characteristic_
#     analyzer_001.py; not imported directly, to keep this module
#     standalone per its own docstring).
#
# NAMING CAVEAT (found during review, not a bug -- documented in the
# source system too): one certified entry's *name* is the legacy string
# "UP_low_rsi_high_accel" even when its *direction* field is "DOWN" (a
# historical artifact of Phase 7's COMBO_TO_FINGERPRINT_NAME remapping,
# kept for backward compatibility with years of existing history/tests
# elsewhere -- renaming it would break that unrelated system). This
# module NEVER infers direction from the name string -- direction is
# always read from its own explicit field, so this naming quirk cannot
# cause a wrong-direction condition to be evaluated here.
#
# NOT every certified condition is usable here: some reference rs_pct_5d
# (relative strength vs a benchmark index) or vol_expansion, features that
# require data this module does not fetch (only one symbol's own OHLCV,
# no benchmark/index series). Those are safely SKIPPED (fail closed, same
# principle as everywhere else in this codebase) rather than approximated.

_DIRECTIONAL_FEATURES = {"mom_5d", "mom_accel", "rs_pct_5d"}

# certified feature name -> this module's own df column name
_CLE_FEATURE_MAP = {
    "mom_5d":  "momentum_5d",
    "mom_accel": "mom_accel",
    "rsi_14":  "rsi_14",
    "hv_20":   "hv_20",
}

_CERTIFIED_FINGERPRINTS_PATH = os.path.join("data", "discovered_fingerprints.json")

# Mirrors FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL in selection_characteristic_
# analyzer_001.py -- the one Phase 2D finding never written to the JSON
# file above (it predates Phase 7's auto-promotion mechanism).
_STATIC_CERTIFIED_FINGERPRINT = {
    "name": "UP_low_rsi_high_accel",
    "direction": "UP",
    "conditions": [["rsi_14", "low"], ["mom_accel", "high"]],
}


def _load_certified_fingerprints() -> list:
    """
    Read the real, already-validated fingerprint library (Phase 7's auto-
    promoted list + the one static Phase 2D finding). Re-read fresh every
    call (the JSON file grows over time as new ones get promoted
    elsewhere) -- fails open to just the static entry on any error.
    """
    out = [dict(_STATIC_CERTIFIED_FINGERPRINT)]
    try:
        if os.path.exists(_CERTIFIED_FINGERPRINTS_PATH):
            with open(_CERTIFIED_FINGERPRINTS_PATH, encoding="utf-8") as fh:
                specs = json.load(fh)
            seen = {(out[0]["name"], out[0]["direction"])}
            for spec in specs:
                key = (spec.get("name"), spec.get("direction"))
                if key in seen or not spec.get("conditions"):
                    continue
                seen.add(key)
                out.append({
                    "name": spec["name"], "direction": spec["direction"],
                    "conditions": spec["conditions"],
                })
    except Exception as exc:
        log.debug("[CLE-Research] certified fingerprint load failed: %s", exc)
    return out


def _evaluate_certified_fingerprint(df, direction: str, trigger_return_pct: float,
                                     conditions: list):
    """
    Generic evaluator for a certified (feature, band) AND-condition list,
    computed against THIS symbol's own trailing history (per-symbol
    tertiles -- Phase 7's own bands are pooled across many symbols, not
    directly reusable numerically, only the underlying idea is reused).
    Returns (sample_count, base_rate, win_rate, lift); (0,0,0,0) if any
    referenced feature isn't computable here (fail closed, never guess).
    """
    try:
        mapped_cols = []
        for feat, _band in conditions:
            col = _CLE_FEATURE_MAP.get(feat)
            if col is None or col not in df.columns:
                return 0, 0.0, 0.0, 0.0   # unavailable feature -- skip, don't approximate
            mapped_cols.append((feat, col, _band))

        threshold   = max(MOVE_THRESHOLD, abs(trigger_return_pct) * 0.5)
        total_days  = len(df)
        large_moves = (df["daily_return"].abs() >= threshold).sum()
        base_rate   = large_moves / max(total_days, 1)

        cond = None
        for feat, col, band in mapped_cols:
            vals = df[col].dropna()
            if len(vals) < 20:
                return 0, base_rate, 0.0, 0.0
            p33, p66 = vals.quantile(0.33), vals.quantile(0.66)
            flip = feat in _DIRECTIONAL_FEATURES and direction.upper() == "DOWN"
            if band == "high":
                feat_cond = (df[col] <= p33) if flip else (df[col] >= p66)
            elif band == "low":
                feat_cond = (df[col] >= p66) if flip else (df[col] <= p33)
            else:  # "moderate"
                feat_cond = df[col].between(p33, p66)
            cond = feat_cond if cond is None else (cond & feat_cond)
        cond = cond.fillna(False)

        if direction.upper() == "UP":
            outcome_mask = df["daily_return"] >= threshold
        else:
            outcome_mask = df["daily_return"] <= -threshold

        trigger_idx  = df.index[cond]
        next_day_idx = _next_day_positions(df, trigger_idx)
        valid        = [i for i in next_day_idx if i in df.index]

        if len(valid) < MIN_SAMPLE:
            return len(valid), base_rate, 0.0, 0.0

        outcomes = outcome_mask.reindex(valid).fillna(False)
        win_rate = outcomes.sum() / len(outcomes)
        lift     = win_rate / max(base_rate, 0.001)
        return len(valid), base_rate, float(win_rate), float(lift)

    except Exception as exc:
        log.debug("[CLE-Research] certified fingerprint evidence error: %s", exc)
        return 0, 0.0, 0.0, 0.0


def _select_best_fingerprint(df, direction: str, trigger_return_pct: float) -> tuple:
    """
    Test volume_momentum (original, always tested) plus every certified
    fingerprint whose OWN recorded direction matches *direction*, and
    return (best, all_results). 'best' is whichever clears the exact same
    MIN_SAMPLE / MIN_WIN_RATE / MIN_LIFT bar with the highest (evidence-
    adjusted) lift. Falls back to volume_momentum's own result if nothing
    qualifies -- preserving the original single-hypothesis failure/
    messaging behavior exactly.

    _assess_evidence is resolved from this module's namespace at CALL
    time (not bound into a module-level list at import time) so patching
    it in tests continues to work correctly.
    """
    fingerprint_fns = [("volume_momentum", _assess_evidence)]
    for fp in _load_certified_fingerprints():
        if fp["direction"].upper() != direction.upper():
            continue
        conditions = [tuple(c) for c in fp["conditions"]]
        fingerprint_fns.append((
            fp["name"],
            lambda d, dirn, ret, _c=conditions: _evaluate_certified_fingerprint(d, dirn, ret, _c),
        ))

    results = []
    for name, fn in fingerprint_fns:
        try:
            count, base, wr, lift = fn(df, direction, trigger_return_pct)
        except Exception as exc:
            log.debug("[CLE-Research] fingerprint %s failed: %s", name, exc)
            count, base, wr, lift = 0, 0.0, 0.0, 0.0

        adj = 0.0
        try:
            from learning_system.cle_fingerprint_refinement_engine import (
                get_fingerprint_preference_adjustment,
            )
            adj = get_fingerprint_preference_adjustment(name)
        except Exception:
            adj = 0.0

        results.append({
            "name": name, "sample_count": count, "base_rate": base,
            "win_rate": wr, "lift": lift, "adjusted_lift": lift + adj,
        })

    qualifying = [
        r for r in results
        if r["sample_count"] >= MIN_SAMPLE
        and r["win_rate"] >= MIN_WIN_RATE
        and r["lift"] >= MIN_LIFT
    ]
    best = max(qualifying, key=lambda r: r["adjusted_lift"]) if qualifying else results[0]
    return best, results


# ── DNA creation ──────────────────────────────────────────────────────────────

def _create_dna_candidate(
    symbol:        str,
    direction:     str,
    feature_name:  str,
    sample_count:  int,
    win_rate:      float,
    effect_size:   float,
    lift:          float,
    action_id:     str,
    today:         str,
) -> Optional[str]:
    """
    Persist a new InstitutionalDNA record with lifecycle=DISCOVERED.

    SAFETY: lifecycle is ALWAYS "DISCOVERED".  The record cannot affect live
    trading until it progresses through REPLICATED → VERIFIED → INSTITUTIONAL,
    which requires explicit Scientific Director approval + validation gate.

    Idempotency: if a DISCOVERED record for the same symbol+direction+feature
    already exists in the IDR DB for study_id='CLE-001', returns its existing ID.

    Returns the dna_id string on success, or None on failure.
    """
    try:
        # Use module-level imports (allows patching in tests)
        _IDRRepository    = IDRRepository
        _IDRNotFoundError = IDRNotFoundError
        _InstitutionalDNA = InstitutionalDNA
        if _IDRRepository is None or _InstitutionalDNA is None:
            log.error("[CLE-Research] IDR dependencies unavailable — cannot create DNA")
            return None

        repo     = _IDRRepository()
        dna_id   = f"CLE-{symbol}-{direction[:2].upper()}-{today.replace('-', '')}"

        # ── Idempotency check ──────────────────────────────────────────
        try:
            existing = repo.get(dna_id)
            log.info("[CLE-Research] DNA %s already exists (lifecycle=%s) — skipping create",
                     dna_id, existing.lifecycle)
            return dna_id
        except _IDRNotFoundError:
            pass  # does not exist yet — proceed to create

        dna = _InstitutionalDNA(
            id=dna_id,
            feature_name=feature_name,
            direction=direction.upper(),
            category="WINNER" if direction.upper() == "UP" else "LOSER",
            lifecycle="DISCOVERED",          # ← SAFETY: NEVER INSTITUTIONAL
            version=1,
            consensus_score=round(win_rate, 4),
            confidence=round(min(win_rate * 0.8, 0.60), 4),  # cap at 0.60
            effect_size=round(effect_size, 4),
            regime_consistency=0.0,          # unknown until replicated
            sector_consistency=0.0,
            temporal_stability=0.0,
            replication_frequency=0,
            evidence_count=sample_count,
            regime_counts={},
            last_seen=today,
            study_id="CLE-001",
            source="CLE-001",
            created_at=today,
            updated_at=today,
            is_current=True,
            metadata={
                "originating_action_id": action_id,
                "lift":                  round(lift, 4),
                "feature":               feature_name,
                "cle_version":           "1.0",
            },
        )

        repo.save(dna, study_id="CLE-001", operator="CLE-001")
        log.info("[CLE-Research] Created DISCOVERED DNA %s for %s %s (win_rate=%.2f, lift=%.2f)",
                 dna_id, symbol, direction, win_rate, lift)
        return dna_id

    except Exception as exc:
        log.error("[CLE-Research] DNA create failed for %s %s: %s", symbol, direction, exc)
        return None


# ── Public research function ──────────────────────────────────────────────────

def run_historical_research(
    action_id:        str,
    symbol:           str,
    direction:        str,
    return_pct:       float,
    today:            str,
    dry_run:          bool = False,
) -> CLEResearchResult:
    """
    Run historical evidence research for one Cat-E action.

    Parameters
    ----------
    action_id   : unique PGA action ID (PGA-XXXXXXXX)
    symbol      : NSE symbol (e.g. "DRREDDY")
    direction   : "UP" or "DOWN"
    return_pct  : magnitude of the trigger move (positive float)
    today       : ISO date string (YYYY-MM-DD)
    dry_run     : if True, research runs but no DNA is written

    Returns
    -------
    CLEResearchResult with status:
      CANDIDATE_CREATED    — evidence sufficient, DNA written (or dry_run)
      INSUFFICIENT_DATA    — < MIN_SAMPLE occurrences
      NO_ACTIONABLE_DNA    — evidence below win_rate / lift thresholds
      FAILED               — fetch or computation error
    """
    result = CLEResearchResult(action_id=action_id, symbol=symbol,
                               direction=direction, return_pct=return_pct)

    # ── Step 1: fetch OHLCV ──────────────────────────────────────────────
    df = _fetch_ohlcv(symbol)
    if df is None or len(df) < 30:
        result.status = "FAILED"
        result.reason = f"OHLCV fetch returned insufficient rows for {symbol}"
        log.warning("[CLE-Research] %s", result.reason)
        return result

    # ── Step 2: compute features ─────────────────────────────────────────
    df = _compute_features(df)
    if df is None or len(df) < 30:
        result.status = "FAILED"
        result.reason = "Feature computation left < 30 rows"
        return result

    # ── Step 3: assess evidence across combination fingerprints ─────────
    best, _all_fingerprint_results = _select_best_fingerprint(df, direction, return_pct)
    sample_count = best["sample_count"]
    base_rate    = best["base_rate"]
    win_rate     = best["win_rate"]
    lift         = best["lift"]
    result.sample_count = sample_count
    result.base_rate    = round(base_rate, 4)
    result.win_rate     = round(win_rate, 4)
    result.lift         = round(lift, 4)

    # ── Step 4: evidence gates ────────────────────────────────────────────
    if sample_count < MIN_SAMPLE:
        result.status = "INSUFFICIENT_DATA"
        result.reason = (
            f"Only {sample_count} trigger occurrences found "
            f"(need {MIN_SAMPLE})"
        )
        log.info("[CLE-Research] %s %s: %s", symbol, direction, result.reason)
        return result

    if win_rate < MIN_WIN_RATE or lift < MIN_LIFT:
        result.status = "NO_ACTIONABLE_DNA"
        result.reason = (
            f"Evidence weak: win_rate={win_rate:.2f} (need {MIN_WIN_RATE}), "
            f"lift={lift:.2f} (need {MIN_LIFT})"
        )
        log.info("[CLE-Research] %s %s: %s", symbol, direction, result.reason)
        return result

    # ── Step 5: create DNA if evidence sufficient ─────────────────────────
    feature_name  = f"{best['name']}_{direction.lower()}"
    effect_size   = round(win_rate - base_rate, 4)
    result.feature_name = feature_name

    if dry_run:
        result.status = "CANDIDATE_CREATED"
        result.reason = "dry_run=True — DNA not written"
        result.dna_id = f"CLE-{symbol}-{direction[:2].upper()}-{today.replace('-', '')}"
        log.info("[CLE-Research] dry_run: would create DNA %s for %s %s",
                 result.dna_id, symbol, direction)
        return result

    dna_id = _create_dna_candidate(
        symbol=symbol,
        direction=direction,
        feature_name=feature_name,
        sample_count=sample_count,
        win_rate=win_rate,
        effect_size=effect_size,
        lift=lift,
        action_id=action_id,
        today=today,
    )

    if dna_id is not None:
        result.status = "CANDIDATE_CREATED"
        result.dna_id = dna_id
        result.reason = (
            f"DISCOVERED DNA created: sample={sample_count}, "
            f"win_rate={win_rate:.2f}, lift={lift:.2f}"
        )
    else:
        result.status = "FAILED"
        result.reason = "IDRRepository.save() returned None — check logs"

    return result
