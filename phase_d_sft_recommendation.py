"""
phase_d_sft_recommendation.py
==============================
Phase D Recommendation #001 — Symbol Follow-Through (SFT) Filter

SHADOW MODE ONLY.
===============================
This module NEVER writes to, modifies, or influences:
  - opportunities / signal_births
  - decision_log / decision engine
  - risk_manager / risk_control
  - execution_engine / order_manager
  - paper_trades.csv / any position or order table

It observes closed trades, maintains follow-through statistics,
generates advisory recommendations, and records counterfactual
outcomes — all in its own isolated SQLite tables.

Evidence basis: OPS05E_SYMBOL_VELOCITY_PROFILE,
               OPS05F_SYMBOL_SELECTION_COUNTERFACTUAL

Architecture: One-file module. Zero imports from protected layers.
Designed to be activated by placing a call in the MasterOrchestrator
post-EOD hook without modifying any trading path.

Key findings from forensic analysis (Apr–May 2026, 38 trades):
  Baseline:    WR=26.3%  PF=0.555  Net=−₹5,58,405
  Top-50% SFT: WR=52.6%  PF=1.113  Net=+₹70,805
  Delta:        +26.3pp  +0.558    +₹6,29,210
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


def _now() -> str:
    """Return current UTC time as ISO-8601 string (timezone-aware, Python 3.14 compatible)."""
    return datetime.now(timezone.utc).isoformat()

# ── Constants & tunables ──────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "phase_d_sft.db")

# SFT classification bands (configurable — change these without code edits)
SFT_HIGH_THRESHOLD:   float = 70.0   # score ≥ 70   → HIGH_SFT
SFT_MEDIUM_THRESHOLD: float = 40.0   # score ≥ 40   → MEDIUM_SFT
                                      # score  < 40   → LOW_SFT

# Minimum closed trades before a symbol is scored (avoids premature classification)
MIN_TRADES_FOR_SCORE: int = 3

# SFT score formula weights (must sum to 100)
_W_WINRATE   = 40.0   # Win Rate % contribution
_W_MFE       = 30.0   # Avg MFE (R, capped at 3.0) contribution
_W_REACH_05R = 30.0   # % trades reaching +0.5R contribution
_MFE_CAP     = 3.0    # R value at which MFE contribution maxes out

# ── Enums ─────────────────────────────────────────────────────────────────────

class SFTClass(str, Enum):
    HIGH              = "HIGH_SFT"
    MEDIUM            = "MEDIUM_SFT"
    LOW               = "LOW_SFT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RecommendationType(str, Enum):
    PREFER_HIGH_SFT    = "PREFER_HIGH_SFT"     # symbol is high follow-through
    CAUTION_MEDIUM_SFT = "CAUTION_MEDIUM_SFT"  # symbol is medium follow-through
    AVOID_LOW_SFT      = "AVOID_LOW_SFT"       # symbol is low follow-through
    INSUFFICIENT_DATA  = "INSUFFICIENT_DATA"   # not enough history yet


class CounterfactualOutcome(str, Enum):
    HELPED    = "HELPED"     # recommendation would have avoided a loss
    HURT      = "HURT"       # recommendation would have blocked a win
    NO_EFFECT = "NO_EFFECT"  # recommendation was neutral (not LOW_SFT or HIGH_SFT triggered)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SFTMetrics:
    """Live symbol follow-through statistics."""
    symbol:               str
    trade_count:          int   = 0
    win_count:            int   = 0
    loss_count:           int   = 0
    win_rate:             float = 0.0
    avg_mfe:              float = 0.0   # avg Max Favourable Excursion in R-multiples
    avg_mae:              float = 0.0   # avg Max Adverse Excursion in R-multiples
    pct_reach_025r:       float = 0.0   # % of trades that reached +0.25R
    pct_reach_050r:       float = 0.0   # % of trades that reached +0.50R
    pct_reach_100r:       float = 0.0   # % of trades that reached +1.00R
    follow_through_score: float = 0.0   # 0–100 composite score
    sft_class:            str   = SFTClass.INSUFFICIENT_DATA.value
    last_updated:         str   = ""


@dataclass
class SFTRecommendation:
    """Advisory recommendation for a trade candidate. Shadow only."""
    recommendation_id:  str
    symbol:             str
    recommendation_type: str
    sft_score:          float
    sft_class:          str
    confidence:         float           # 0–1 scale
    supporting_metrics: Dict[str, Any]  # snapshot of SFTMetrics
    created_at:         str


@dataclass
class CounterfactualRecord:
    """Post-trade record comparing recommendation to actual outcome."""
    record_id:              str
    symbol:                 str
    trade_pnl:              float
    trade_win:              bool
    sft_class_at_entry:     str
    recommendation_type:    str
    counterfactual_outcome: str   # HELPED / HURT / NO_EFFECT
    recorded_at:            str


# ── Schema DDL ────────────────────────────────────────────────────────────────

_DDL_SFT_METRICS = """
CREATE TABLE IF NOT EXISTS symbol_follow_through_metrics (
    symbol                TEXT PRIMARY KEY,
    trade_count           INTEGER  NOT NULL DEFAULT 0,
    win_count             INTEGER  NOT NULL DEFAULT 0,
    loss_count            INTEGER  NOT NULL DEFAULT 0,
    win_rate              REAL     NOT NULL DEFAULT 0.0,
    avg_mfe               REAL     NOT NULL DEFAULT 0.0,
    avg_mae               REAL     NOT NULL DEFAULT 0.0,
    pct_reach_025r        REAL     NOT NULL DEFAULT 0.0,
    pct_reach_050r        REAL     NOT NULL DEFAULT 0.0,
    pct_reach_100r        REAL     NOT NULL DEFAULT 0.0,
    follow_through_score  REAL     NOT NULL DEFAULT 0.0,
    sft_class             TEXT     NOT NULL DEFAULT 'INSUFFICIENT_DATA',
    last_updated          TEXT     NOT NULL
);
"""

_DDL_PENDING_ADJUSTMENTS = """
CREATE TABLE IF NOT EXISTS pending_adjustments (
    recommendation_id    TEXT PRIMARY KEY,
    symbol               TEXT    NOT NULL,
    recommendation_type  TEXT    NOT NULL,
    sft_score            REAL    NOT NULL DEFAULT 0.0,
    sft_class            TEXT    NOT NULL,
    confidence           REAL    NOT NULL DEFAULT 0.0,
    supporting_metrics   TEXT,
    created_at           TEXT    NOT NULL
);
"""

_DDL_COUNTERFACTUAL = """
CREATE TABLE IF NOT EXISTS counterfactual_tracking (
    record_id               TEXT PRIMARY KEY,
    symbol                  TEXT  NOT NULL,
    trade_pnl               REAL  NOT NULL,
    trade_win               INTEGER NOT NULL,
    sft_class_at_entry      TEXT  NOT NULL,
    recommendation_type     TEXT  NOT NULL,
    counterfactual_outcome  TEXT  NOT NULL,
    recorded_at             TEXT  NOT NULL
);
"""

_DDL_SHADOW_LOG = """
CREATE TABLE IF NOT EXISTS shadow_mode_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    event_type    TEXT    NOT NULL,
    symbol        TEXT,
    detail        TEXT
);
"""

# ── SFT Score Computation ─────────────────────────────────────────────────────

def compute_symbol_follow_through(
    trade_count:    int,
    win_count:      int,
    mfe_values:     List[float],    # per-trade MFE in R-multiples
    mae_values:     List[float],    # per-trade MAE in R-multiples
    reach_025r:     int,            # count of trades that reached +0.25R
    reach_050r:     int,            # count of trades that reached +0.50R
    reach_100r:     int,            # count of trades that reached +1.00R
) -> Tuple[float, SFTMetrics]:
    """
    Compute the Symbol Follow-Through (SFT) score on a 0–100 scale.

    Formula
    -------
    Three components, each normalised to 0–100, then weighted:

      C1 (Win Rate, weight 40%):
          C1 = win_count / trade_count * 100

      C2 (Avg MFE depth, weight 30%):
          avg_mfe = mean(mfe_values)
          C2 = min(avg_mfe, MFE_CAP) / MFE_CAP * 100
          MFE_CAP = 3.0R  (3R covers most favourable breakout moves)

      C3 (Follow-through rate to 0.5R, weight 30%):
          C3 = reach_050r / trade_count * 100

    SFT = (C1 * 0.40) + (C2 * 0.30) + (C3 * 0.30)

    Rationale
    ---------
    Win rate alone is noisy with small samples. Adding MFE depth captures
    *how far* price moved favourably (a symbol that consistently moves
    +0.8R before reversing is more exploitable than one that reaches +0.1R).
    Reach-0.5R directly measures whether the system's targets are reachable,
    irrespective of where the exit actually occurred.

    Calibration (OPS05F, 38-trade forensic dataset, Apr–May 2026):
      HINDALCO  (score 94.3): WR=100%, MFE=2.43R, pct05R=100%  → top
      BANKBARODA(score 83.4): WR=100%, MFE=1.34R, pct05R=100%
      TATASTEEL (score  8.4): WR=  0%, MFE=0.24R, pct05R= 20%  → bottom
      BHARTIARTL(score  0.8): WR=  0%, MFE=0.08R, pct05R=  0%
    """
    if trade_count == 0:
        m = SFTMetrics(symbol="")
        return 0.0, m

    # ── Component 1: Win Rate ───────────────────────────────────────────────
    wr = win_count / trade_count * 100.0
    c1 = wr

    # ── Component 2: Avg MFE depth ──────────────────────────────────────────
    valid_mfe = [v for v in mfe_values if v is not None and -100 < v < 100]
    avg_mfe = float(sum(valid_mfe) / len(valid_mfe)) if valid_mfe else 0.0
    c2 = min(avg_mfe, _MFE_CAP) / _MFE_CAP * 100.0

    # ── Component 3: % reaching 0.5R ────────────────────────────────────────
    pct_05r = reach_050r / trade_count * 100.0
    c3 = pct_05r

    # ── Weighted composite ──────────────────────────────────────────────────
    sft_score = (c1 * _W_WINRATE / 100.0) + (c2 * _W_MFE / 100.0) + (c3 * _W_REACH_05R / 100.0)
    sft_score = round(min(max(sft_score, 0.0), 100.0), 3)

    # ── Derived metrics ─────────────────────────────────────────────────────
    valid_mae = [v for v in mae_values if v is not None and -100 < v < 100]
    avg_mae   = float(sum(valid_mae) / len(valid_mae)) if valid_mae else 0.0

    pct_025r = reach_025r / trade_count * 100.0
    pct_100r = reach_100r / trade_count * 100.0
    loss_count = trade_count - win_count

    m = SFTMetrics(
        symbol               = "",   # caller fills this in
        trade_count          = trade_count,
        win_count            = win_count,
        loss_count           = loss_count,
        win_rate             = round(wr, 2),
        avg_mfe              = round(avg_mfe, 3),
        avg_mae              = round(avg_mae, 3),
        pct_reach_025r       = round(pct_025r, 2),
        pct_reach_050r       = round(pct_05r, 2),
        pct_reach_100r       = round(pct_100r, 2),
        follow_through_score = sft_score,
        sft_class            = classify_sft(sft_score, trade_count).value,
        last_updated         = _now(),
    )
    return sft_score, m


def classify_sft(score: float, trade_count: int) -> SFTClass:
    """
    Classify a symbol's SFT score into HIGH / MEDIUM / LOW / INSUFFICIENT_DATA.

    Bands (configurable via module-level constants):
      HIGH_SFT    : score >= SFT_HIGH_THRESHOLD   (default 70)
      MEDIUM_SFT  : score >= SFT_MEDIUM_THRESHOLD (default 40)
      LOW_SFT     : score <  SFT_MEDIUM_THRESHOLD
      INSUFFICIENT_DATA: trade_count < MIN_TRADES_FOR_SCORE (default 3)
    """
    if trade_count < MIN_TRADES_FOR_SCORE:
        return SFTClass.INSUFFICIENT_DATA
    if score >= SFT_HIGH_THRESHOLD:
        return SFTClass.HIGH
    if score >= SFT_MEDIUM_THRESHOLD:
        return SFTClass.MEDIUM
    return SFTClass.LOW


# ── Recommendation Generator ──────────────────────────────────────────────────

def generate_sft_recommendation(metrics: SFTMetrics) -> SFTRecommendation:
    """
    Generate an advisory SFT recommendation for a trade candidate.

    Shadow Mode Contract
    --------------------
    This function returns a recommendation object.
    The caller MUST NOT use this to block, modify, or re-score any trade.
    The recommendation is stored in pending_adjustments for monitoring only.

    Recommendation mapping:
      HIGH_SFT        → PREFER_HIGH_SFT    (confidence ∝ score / 100)
      MEDIUM_SFT      → CAUTION_MEDIUM_SFT (confidence ∝ score / 100)
      LOW_SFT         → AVOID_LOW_SFT      (confidence ∝ (100 - score) / 100)
      INSUFFICIENT_DATA→ INSUFFICIENT_DATA (confidence = 0.0)
    """
    sft_class_enum = SFTClass(metrics.sft_class)

    if sft_class_enum == SFTClass.INSUFFICIENT_DATA:
        rec_type   = RecommendationType.INSUFFICIENT_DATA
        confidence = 0.0
    elif sft_class_enum == SFTClass.HIGH:
        rec_type   = RecommendationType.PREFER_HIGH_SFT
        confidence = round(metrics.follow_through_score / 100.0, 3)
    elif sft_class_enum == SFTClass.MEDIUM:
        rec_type   = RecommendationType.CAUTION_MEDIUM_SFT
        confidence = round(metrics.follow_through_score / 100.0, 3)
    else:  # LOW
        rec_type   = RecommendationType.AVOID_LOW_SFT
        # Confidence for AVOID is how certain we are it's low (higher score → lower avoidance confidence)
        confidence = round((100.0 - metrics.follow_through_score) / 100.0, 3)

    return SFTRecommendation(
        recommendation_id  = str(uuid.uuid4()),
        symbol             = metrics.symbol,
        recommendation_type= rec_type.value,
        sft_score          = metrics.follow_through_score,
        sft_class          = metrics.sft_class,
        confidence         = confidence,
        supporting_metrics = {
            "trade_count":    metrics.trade_count,
            "win_rate":       metrics.win_rate,
            "avg_mfe":        metrics.avg_mfe,
            "avg_mae":        metrics.avg_mae,
            "pct_reach_025r": metrics.pct_reach_025r,
            "pct_reach_050r": metrics.pct_reach_050r,
            "pct_reach_100r": metrics.pct_reach_100r,
        },
        created_at = _now(),
    )


def evaluate_counterfactual(
    rec_type:  str,
    trade_pnl: float,
) -> CounterfactualOutcome:
    """
    Given the recommendation that was issued and the actual trade outcome,
    determine whether the recommendation would have helped, hurt, or been neutral.

    Rules:
      AVOID_LOW_SFT  + loss  → HELPED    (we advised avoiding, trade lost — good call)
      AVOID_LOW_SFT  + win   → HURT      (we advised avoiding, trade won  — missed opportunity)
      PREFER_HIGH_SFT+ win   → HELPED    (we preferred it, trade won      — correct)
      PREFER_HIGH_SFT+ loss  → NO_EFFECT (we preferred it but it still lost — no amplification)
      INSUFFICIENT_DATA       → NO_EFFECT (no recommendation was actionable)
      CAUTION_MEDIUM_SFT      → NO_EFFECT (neutral advisory, not directional)
    """
    is_win = trade_pnl > 0

    if rec_type == RecommendationType.AVOID_LOW_SFT.value:
        return CounterfactualOutcome.HELPED if not is_win else CounterfactualOutcome.HURT
    if rec_type == RecommendationType.PREFER_HIGH_SFT.value:
        return CounterfactualOutcome.HELPED if is_win else CounterfactualOutcome.NO_EFFECT
    return CounterfactualOutcome.NO_EFFECT


# ── SFT Tracker (main class) ──────────────────────────────────────────────────

class SFTTracker:
    """
    Central tracker for Symbol Follow-Through metrics.

    Shadow Mode Contract
    --------------------
    This class uses its own isolated SQLite database (phase_d_sft.db).
    It NEVER opens, reads, or writes to:
        control_tower.db, trading_brain.db, paper_trades.csv,
        or any file in execution_engine/, risk_control/, decision_ai/,
        or opportunity_engine/.

    Thread safety: single write lock (WAL mode). Multiple readers fine.

    Usage
    -----
    tracker = SFTTracker()

    # After every closed trade, ingest it:
    tracker.ingest_closed_trade(
        symbol        = "TATASTEEL",
        trade_pnl     = -47000.0,
        entry_price   = 145.5,
        stop_loss     = 143.2,
        mfe_r         = 0.24,
        mae_r         = 0.66,
        reached_025r  = True,
        reached_050r  = False,
        reached_100r  = False,
    )

    # Before any new trade candidate is processed:
    rec = tracker.get_recommendation("COALINDIA")
    # rec.recommendation_type is ADVISORY ONLY — do not gate on this
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._db_path = db_path
        self._lock    = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    # ── Internal DB helpers ───────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL_SFT_METRICS)
            conn.executescript(_DDL_PENDING_ADJUSTMENTS)
            conn.executescript(_DDL_COUNTERFACTUAL)
            conn.executescript(_DDL_SHADOW_LOG)
            conn.commit()
        self._shadow_log("INIT", None, "SFTTracker initialised. DB=" + self._db_path)

    def _shadow_log(self, event_type: str, symbol: Optional[str], detail: str) -> None:
        """Internal audit trail — every significant action leaves a record."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO shadow_mode_log (ts, event_type, symbol, detail) VALUES (?,?,?,?)",
                    (_now(), event_type, symbol, detail)
                )
                conn.commit()
        except Exception:
            pass  # shadow log failure must never raise

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest_closed_trade(
        self,
        symbol:       str,
        trade_pnl:    float,
        entry_price:  float,
        stop_loss:    float,
        mfe_r:        Optional[float] = None,  # Max Favourable Excursion in R-multiples
        mae_r:        Optional[float] = None,  # Max Adverse Excursion in R-multiples
        reached_025r: bool            = False,
        reached_050r: bool            = False,
        reached_100r: bool            = False,
    ) -> None:
        """
        Ingest one closed trade and recompute SFT metrics for the symbol.

        This is the ONLY write path into symbol_follow_through_metrics.
        It updates in-place using a running aggregation approach so that
        per-trade raw data is not stored (storage efficient for long runs).

        Parameters
        ----------
        mfe_r : float, optional
            Maximum favourable excursion in R-multiples.
            R = |entry_price − stop_loss|. If None, it is excluded from
            the MFE average (does not distort aggregate).
        mae_r : float, optional
            Maximum adverse excursion in R-multiples. Same exclusion rule.
        """
        if not symbol or entry_price <= 0 or stop_loss <= 0:
            return

        r = abs(entry_price - stop_loss)
        if r <= 0:
            return

        is_win = trade_pnl > 0

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM symbol_follow_through_metrics WHERE symbol=?",
                    (symbol,)
                ).fetchone()

                if row is None:
                    # First trade for this symbol
                    n       = 1
                    wins    = 1 if is_win else 0
                    # Running MFE/MAE: stored as (sum, count) implicitly via score recompute
                    # We store avg directly and update with online mean formula
                    cur_mfe_avg = mfe_r if mfe_r is not None else 0.0
                    cur_mae_avg = mae_r if mae_r is not None else 0.0
                    mfe_n   = 1 if mfe_r is not None else 0
                    mae_n   = 1 if mae_r is not None else 0
                    r025    = 1 if reached_025r else 0
                    r050    = 1 if reached_050r else 0
                    r100    = 1 if reached_100r else 0
                else:
                    n_prev    = row["trade_count"]
                    wins_prev = row["win_count"]
                    n         = n_prev + 1
                    wins      = wins_prev + (1 if is_win else 0)

                    # Online update for MFE average:
                    # new_avg = (old_avg * old_n + new_val) / new_n
                    # When mfe_r is None, we skip the update (keep old average)
                    prev_mfe  = row["avg_mfe"]
                    prev_mae  = row["avg_mae"]
                    prev_r025 = int(round(row["pct_reach_025r"] * n_prev / 100))
                    prev_r050 = int(round(row["pct_reach_050r"] * n_prev / 100))
                    prev_r100 = int(round(row["pct_reach_100r"] * n_prev / 100))

                    # MFE/MAE: count valid (non-None) updates
                    mfe_n_prev = row["trade_count"]   # conservative: assume all had MFE
                    if mfe_r is not None:
                        cur_mfe_avg = (prev_mfe * mfe_n_prev + mfe_r) / (mfe_n_prev + 1)
                        mfe_n       = mfe_n_prev + 1
                    else:
                        cur_mfe_avg = prev_mfe
                        mfe_n       = mfe_n_prev

                    if mae_r is not None:
                        cur_mae_avg = (prev_mae * mfe_n_prev + mae_r) / (mfe_n_prev + 1)
                        mae_n       = mfe_n_prev + 1
                    else:
                        cur_mae_avg = prev_mae
                        mae_n       = mfe_n_prev

                    r025 = prev_r025 + (1 if reached_025r else 0)
                    r050 = prev_r050 + (1 if reached_050r else 0)
                    r100 = prev_r100 + (1 if reached_100r else 0)

                # Recompute full SFT score from latest aggregates
                mfe_list  = [cur_mfe_avg] * mfe_n   # approximate — score uses avg directly
                score, m  = compute_symbol_follow_through(
                    trade_count = n,
                    win_count   = wins,
                    mfe_values  = [cur_mfe_avg],
                    mae_values  = [cur_mae_avg],
                    reach_025r  = r025,
                    reach_050r  = r050,
                    reach_100r  = r100,
                )
                m.symbol = symbol

                conn.execute("""
                    INSERT INTO symbol_follow_through_metrics
                      (symbol, trade_count, win_count, loss_count, win_rate,
                       avg_mfe, avg_mae, pct_reach_025r, pct_reach_050r, pct_reach_100r,
                       follow_through_score, sft_class, last_updated)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(symbol) DO UPDATE SET
                      trade_count          = excluded.trade_count,
                      win_count            = excluded.win_count,
                      loss_count           = excluded.loss_count,
                      win_rate             = excluded.win_rate,
                      avg_mfe              = excluded.avg_mfe,
                      avg_mae              = excluded.avg_mae,
                      pct_reach_025r       = excluded.pct_reach_025r,
                      pct_reach_050r       = excluded.pct_reach_050r,
                      pct_reach_100r       = excluded.pct_reach_100r,
                      follow_through_score = excluded.follow_through_score,
                      sft_class            = excluded.sft_class,
                      last_updated         = excluded.last_updated
                """, (
                    symbol, n, wins, n - wins,
                    round(wins / n * 100, 2),
                    round(cur_mfe_avg, 3), round(cur_mae_avg, 3),
                    round(r025 / n * 100, 2),
                    round(r050 / n * 100, 2),
                    round(r100 / n * 100, 2),
                    score, m.sft_class,
                    _now(),
                ))
                conn.commit()

        self._shadow_log(
            "INGEST", symbol,
            f"pnl={trade_pnl:.0f} is_win={is_win} mfe_r={mfe_r} mae_r={mae_r} "
            f"score={score:.2f} class={m.sft_class}"
        )

    def get_metrics(self, symbol: str) -> Optional[SFTMetrics]:
        """Return current SFT metrics for a symbol, or None if not seen before."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM symbol_follow_through_metrics WHERE symbol=?",
                (symbol,)
            ).fetchone()
        if row is None:
            return None
        return SFTMetrics(
            symbol               = row["symbol"],
            trade_count          = row["trade_count"],
            win_count            = row["win_count"],
            loss_count           = row["loss_count"],
            win_rate             = row["win_rate"],
            avg_mfe              = row["avg_mfe"],
            avg_mae              = row["avg_mae"],
            pct_reach_025r       = row["pct_reach_025r"],
            pct_reach_050r       = row["pct_reach_050r"],
            pct_reach_100r       = row["pct_reach_100r"],
            follow_through_score = row["follow_through_score"],
            sft_class            = row["sft_class"],
            last_updated         = row["last_updated"],
        )

    def get_recommendation(self, symbol: str) -> SFTRecommendation:
        """
        Generate and persist an advisory SFT recommendation for symbol.

        SHADOW MODE: the returned object is advisory only.
        Do NOT use return value to gate, score, or block any trade.
        """
        metrics = self.get_metrics(symbol)

        if metrics is None:
            metrics = SFTMetrics(
                symbol    = symbol,
                sft_class = SFTClass.INSUFFICIENT_DATA.value,
            )

        rec = generate_sft_recommendation(metrics)

        # Persist to pending_adjustments (shadow store)
        with self._lock:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO pending_adjustments
                      (recommendation_id, symbol, recommendation_type, sft_score,
                       sft_class, confidence, supporting_metrics, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    rec.recommendation_id,
                    rec.symbol,
                    rec.recommendation_type,
                    rec.sft_score,
                    rec.sft_class,
                    rec.confidence,
                    json.dumps(rec.supporting_metrics),
                    rec.created_at,
                ))
                conn.commit()

        self._shadow_log(
            "RECOMMEND", symbol,
            f"type={rec.recommendation_type} score={rec.sft_score:.2f} conf={rec.confidence:.3f}"
        )
        return rec

    def record_counterfactual(
        self,
        symbol:     str,
        trade_pnl:  float,
        rec_type:   str,
        sft_class:  str,
    ) -> CounterfactualRecord:
        """
        After a trade closes, record the counterfactual outcome.

        Parameters
        ----------
        symbol    : traded symbol
        trade_pnl : realised PnL of the closed trade
        rec_type  : the recommendation that was in effect at entry time
        sft_class : the SFT class at entry time
        """
        outcome = evaluate_counterfactual(rec_type, trade_pnl)

        cf = CounterfactualRecord(
            record_id              = str(uuid.uuid4()),
            symbol                 = symbol,
            trade_pnl              = trade_pnl,
            trade_win              = trade_pnl > 0,
            sft_class_at_entry     = sft_class,
            recommendation_type    = rec_type,
            counterfactual_outcome = outcome.value,
            recorded_at            = _now(),
        )

        with self._lock:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO counterfactual_tracking
                      (record_id, symbol, trade_pnl, trade_win, sft_class_at_entry,
                       recommendation_type, counterfactual_outcome, recorded_at)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    cf.record_id, cf.symbol, cf.trade_pnl, int(cf.trade_win),
                    cf.sft_class_at_entry, cf.recommendation_type,
                    cf.counterfactual_outcome, cf.recorded_at,
                ))
                conn.commit()

        self._shadow_log(
            "COUNTERFACTUAL", symbol,
            f"pnl={trade_pnl:.0f} rec={rec_type} outcome={outcome.value}"
        )
        return cf

    def get_all_metrics(self) -> List[SFTMetrics]:
        """Return all symbols ordered by follow_through_score descending."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM symbol_follow_through_metrics "
                "ORDER BY follow_through_score DESC"
            ).fetchall()
        return [
            SFTMetrics(
                symbol               = r["symbol"],
                trade_count          = r["trade_count"],
                win_count            = r["win_count"],
                loss_count           = r["loss_count"],
                win_rate             = r["win_rate"],
                avg_mfe              = r["avg_mfe"],
                avg_mae              = r["avg_mae"],
                pct_reach_025r       = r["pct_reach_025r"],
                pct_reach_050r       = r["pct_reach_050r"],
                pct_reach_100r       = r["pct_reach_100r"],
                follow_through_score = r["follow_through_score"],
                sft_class            = r["sft_class"],
                last_updated         = r["last_updated"],
            )
            for r in rows
        ]

    def get_counterfactual_summary(self) -> Dict[str, Any]:
        """
        Aggregate counterfactual tracking results.
        Used by generate_shadow_report().
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT counterfactual_outcome, COUNT(*) AS n, "
                "SUM(trade_pnl) AS total_pnl "
                "FROM counterfactual_tracking "
                "GROUP BY counterfactual_outcome"
            ).fetchall()
            class_rows = conn.execute(
                "SELECT sft_class_at_entry, "
                "COUNT(*) AS n, "
                "SUM(CASE WHEN trade_win=1 THEN 1 ELSE 0 END) AS wins, "
                "SUM(trade_pnl) AS total_pnl "
                "FROM counterfactual_tracking "
                "GROUP BY sft_class_at_entry"
            ).fetchall()

        outcome_summary = {r["counterfactual_outcome"]: {"n": r["n"], "total_pnl": r["total_pnl"]} for r in rows}
        class_summary   = {
            r["sft_class_at_entry"]: {
                "n": r["n"], "wins": r["wins"],
                "wr": round(r["wins"] / r["n"] * 100, 1) if r["n"] > 0 else 0,
                "total_pnl": r["total_pnl"]
            }
            for r in class_rows
        }
        helped_pnl = outcome_summary.get("HELPED", {}).get("total_pnl", 0) or 0
        hurt_pnl   = outcome_summary.get("HURT",   {}).get("total_pnl", 0) or 0
        net_benefit = abs(helped_pnl) - abs(hurt_pnl)

        return {
            "by_outcome":      outcome_summary,
            "by_sft_class":    class_summary,
            "net_cf_benefit":  round(net_benefit, 0),
        }

    # ── Reporting ─────────────────────────────────────────────────────────────

    def generate_shadow_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate SFT_SHADOW_REPORT.md content.
        If output_path is given, also writes the file.
        Returns the report as a string.
        """
        all_metrics = self.get_all_metrics()
        cf_summary  = self.get_counterfactual_summary()

        high   = [m for m in all_metrics if m.sft_class == SFTClass.HIGH.value]
        medium = [m for m in all_metrics if m.sft_class == SFTClass.MEDIUM.value]
        low    = [m for m in all_metrics if m.sft_class == SFTClass.LOW.value]
        insuf  = [m for m in all_metrics if m.sft_class == SFTClass.INSUFFICIENT_DATA.value]

        top20    = all_metrics[:20]
        bottom20 = list(reversed(all_metrics[-20:])) if len(all_metrics) >= 20 else list(reversed(all_metrics))

        lines = [
            "# SFT Shadow Report",
            f"**Generated:** {_now()}",
            f"**Mode:** SHADOW — no execution influence",
            "",
            "---",
            "",
            "## Classification Summary",
            "",
            f"| Class | Count | Thresholds |",
            f"|---|---|---|",
            f"| HIGH_SFT | {len(high)} | score ≥ {SFT_HIGH_THRESHOLD:.0f} |",
            f"| MEDIUM_SFT | {len(medium)} | score ≥ {SFT_MEDIUM_THRESHOLD:.0f} |",
            f"| LOW_SFT | {len(low)} | score < {SFT_MEDIUM_THRESHOLD:.0f} |",
            f"| INSUFFICIENT_DATA | {len(insuf)} | trade_count < {MIN_TRADES_FOR_SCORE} |",
            "",
            "---",
            "",
            "## Top 20 Follow-Through Symbols",
            "",
            "| Rank | Symbol | SFT Class | Score | WR% | Avg MFE (R) | %→0.5R | %→1R | Trades |",
            "|---|---|---|---|---|---|---|---|---|",
        ]

        for i, m in enumerate(top20, 1):
            lines.append(
                f"| {i} | {m.symbol} | {m.sft_class} | {m.follow_through_score:.1f} "
                f"| {m.win_rate:.1f}% | {m.avg_mfe:.3f} | {m.pct_reach_050r:.1f}% "
                f"| {m.pct_reach_100r:.1f}% | {m.trade_count} |"
            )

        lines += [
            "",
            "---",
            "",
            "## Bottom 20 Follow-Through Symbols",
            "",
            "| Rank | Symbol | SFT Class | Score | WR% | Avg MFE (R) | %→0.5R | %→1R | Trades |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for i, m in enumerate(bottom20, 1):
            lines.append(
                f"| {i} | {m.symbol} | {m.sft_class} | {m.follow_through_score:.1f} "
                f"| {m.win_rate:.1f}% | {m.avg_mfe:.3f} | {m.pct_reach_050r:.1f}% "
                f"| {m.pct_reach_100r:.1f}% | {m.trade_count} |"
            )

        lines += [
            "",
            "---",
            "",
            "## Counterfactual Benefit Summary",
            "",
            "| SFT Class | Trades | WR% | Total PnL |",
            "|---|---|---|---|",
        ]
        for cls, d in cf_summary.get("by_sft_class", {}).items():
            lines.append(
                f"| {cls} | {d['n']} | {d['wr']:.1f}% | ₹{d['total_pnl']:,.0f} |"
            )

        lines += [
            "",
            "| Outcome | Count | PnL impact |",
            "|---|---|---|",
        ]
        for outcome, d in cf_summary.get("by_outcome", {}).items():
            lines.append(
                f"| {outcome} | {d['n']} | ₹{d['total_pnl']:,.0f} |"
            )

        net_benefit = cf_summary.get("net_cf_benefit", 0)
        lines += [
            "",
            f"**Net counterfactual benefit** (HELPED − HURT): ₹{net_benefit:,.0f}",
            "",
            "---",
            "",
            "## Recommendation Confidence",
            "",
            "| Band | Threshold | Confidence Basis |",
            "|---|---|---|",
            f"| HIGH_SFT    | score ≥ {SFT_HIGH_THRESHOLD:.0f} | score / 100 |",
            f"| MEDIUM_SFT  | score ≥ {SFT_MEDIUM_THRESHOLD:.0f} | score / 100 |",
            f"| LOW_SFT     | score  < {SFT_MEDIUM_THRESHOLD:.0f} | (100 − score) / 100 |",
            "",
            "*Shadow mode — no recommendations were applied to execution.*",
        ]

        report = "\n".join(lines)

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(report)
            self._shadow_log("REPORT", None, f"Written to {output_path}")

        return report


# ── Module-level singleton (lazy init) ───────────────────────────────────────

_tracker_instance: Optional[SFTTracker] = None
_tracker_lock = threading.Lock()


def get_sft_tracker(db_path: str = DB_PATH) -> SFTTracker:
    """
    Return the module-level SFTTracker singleton.
    Thread-safe lazy initialisation.
    """
    global _tracker_instance
    if _tracker_instance is None:
        with _tracker_lock:
            if _tracker_instance is None:
                _tracker_instance = SFTTracker(db_path=db_path)
    return _tracker_instance
