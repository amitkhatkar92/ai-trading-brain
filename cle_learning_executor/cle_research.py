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

import logging
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
    Returns the augmented DataFrame (original is not mutated).
    """
    try:
        import pandas as pd

        df = df.copy()
        close  = df["Close"]
        volume = df.get("Volume", None)

        df["daily_return"] = close.pct_change() * 100.0
        df["momentum_5d"]  = close.pct_change(periods=5) * 100.0

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

        # Shift trigger one row forward to get next-day outcome
        trigger_idx  = df.index[cond]
        next_day_idx = df.index[df.index.get_indexer(trigger_idx, method="pad") + 1]
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

    # ── Step 3: assess evidence ───────────────────────────────────────────
    sample_count, base_rate, win_rate, lift = _assess_evidence(df, direction, return_pct)
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
    feature_name  = f"volume_momentum_{direction.lower()}"
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
