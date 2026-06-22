"""
oios/scanners/layer_1a.py

Layer 1A — Confirmation DNA Scanner

Question: What has already begun moving?

Detects stocks that have demonstrably started a directional move using
price, volume, and momentum evidence.

Phase A archetypes implemented:
  DNA_1A_MOMENTUM_CONT     — Momentum Continuation
  DNA_1A_52W_HIGH_EXPAND   — 52-Week High Expansion
  DNA_1A_SECTOR_BKT        — Sector Breakout Accelerator
  DNA_1A_RESULTS_FOLLOWTHR — Results Follow-Through

Signal type: "1A"
Minimum write threshold: base_score > 4.0
Phase A defaults: expected_move_pct=8.0, expected_ttl_days=10

CRITICAL: This scanner does NOT write to the database.
All writes go through:
  Scanner → Opportunity Service → Repository → Database

This discipline is mandatory (MAS Section 7, Phase A Critical Rule).
"""

from __future__ import annotations
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (Phase A defaults per MAS Section 5, Layer 1A)
# ---------------------------------------------------------------------------

MIN_WRITE_THRESHOLD     = 4.0   # base_score must exceed this to write signal_birth
EXPECTED_MOVE_PCT       = 8.0   # universal default until archetype distributions are active
EXPECTED_TTL_DAYS       = 10    # Phase A default for all 1A archetypes
SIGNAL_TYPE             = "1A"
ARCHETYPE_VERSION       = 1


# ---------------------------------------------------------------------------
# Raw detection result — pure Python, no DB coupling
# ---------------------------------------------------------------------------

@dataclass
class RawSignal:
    """
    Output of a Layer 1A archetype detector.
    Not yet persisted — the scanner creates these; the service layer writes them.
    """
    symbol:                 str
    archetype_id:           str
    base_score:             float
    direction:              str             # "LONG" | "SHORT"
    detected_at:            str             # ISO-8601 date
    birth_price:            float
    regime:                 str

    signal_type:            str             = SIGNAL_TYPE
    archetype_version:      int             = ARCHETYPE_VERSION
    expected_ttl_days:      int             = EXPECTED_TTL_DAYS
    expected_move_pct:      float           = EXPECTED_MOVE_PCT
    expected_move_pct_source: str           = "UNIVERSAL_DEFAULT_8PCT"
    theme_phase_at_birth:   Optional[str]   = None
    consensus_score_at_birth: Optional[float] = None

    @property
    def qualifies(self) -> bool:
        return self.base_score > MIN_WRITE_THRESHOLD


# ---------------------------------------------------------------------------
# OHLCV price window — loaded once per symbol per scan cycle
# ---------------------------------------------------------------------------

@dataclass
class PriceWindow:
    symbol:      str
    dates:       list[str]
    closes:      list[float]
    volumes:     list[float]
    highs:       list[float]
    lows:        list[float]

    @property
    def n(self) -> int:
        return len(self.closes)

    def close(self, i: int = -1) -> float:
        return self.closes[i]

    def volume(self, i: int = -1) -> float:
        return self.volumes[i]

    def avg_volume(self, lookback: int = 20) -> float:
        window = self.volumes[-(lookback + 1):-1] if len(self.volumes) > lookback else self.volumes[:-1]
        return sum(window) / len(window) if window else 0.0

    def high_52w(self) -> float:
        window = self.highs[-252:] if len(self.highs) >= 252 else self.highs
        return max(window) if window else 0.0

    def price_change_pct(self, lookback: int = 20) -> float:
        """% change over last `lookback` trading sessions."""
        if len(self.closes) < lookback + 1:
            return 0.0
        return (self.closes[-1] / self.closes[-(lookback + 1)] - 1.0) * 100


# ---------------------------------------------------------------------------
# OHLCV data loader (reads from ohlcv_daily table)
# ---------------------------------------------------------------------------

def _load_price_window(
    conn: sqlite3.Connection,
    symbol: str,
    as_of_date: str,
    lookback_rows: int = 252,
) -> Optional[PriceWindow]:
    """
    Load the last lookback_rows trading sessions for symbol up to as_of_date.
    Returns None if fewer than 30 rows available (not enough data to scan).
    """
    rows = conn.execute("""
        SELECT trade_date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (symbol, as_of_date, lookback_rows)).fetchall()

    if len(rows) < 30:
        return None

    rows.reverse()  # chronological order
    return PriceWindow(
        symbol  = symbol,
        dates   = [r[0] for r in rows],
        closes  = [r[4] for r in rows],
        volumes = [r[5] for r in rows],
        highs   = [r[2] for r in rows],
        lows    = [r[3] for r in rows],
    )


# ---------------------------------------------------------------------------
# Archetype detectors
# ---------------------------------------------------------------------------

def _detect_momentum_continuation(
    pw: PriceWindow,
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1A_MOMENTUM_CONT — Momentum Continuation

    Conditions:
    - 20-day return > 5%
    - Close above 20-day SMA
    - Volume on last session ≥ 1.2× 20-day average
    - Not in top 5% of 52-week range (not yet crowded)

    Scoring:
    - base_score = 4.0 + momentum_component + volume_component
    - momentum_component: 0–3.0 (scaled on 20d return 5%→20%)
    - volume_component:   0–2.0 (scaled on vol ratio 1.2×→3.0×)
    """
    if pw.n < 22:
        return None

    change_20d = pw.price_change_pct(20)
    if change_20d < 5.0:
        return None

    sma_20 = sum(pw.closes[-20:]) / 20
    if pw.close() <= sma_20:
        return None

    avg_vol  = pw.avg_volume(20)
    vol_ratio = pw.volume() / avg_vol if avg_vol > 0 else 0
    if vol_ratio < 1.2:
        return None

    high_52 = pw.high_52w()
    near_high_pct = (pw.close() / high_52) if high_52 > 0 else 0
    if near_high_pct > 0.98:  # too close to 52w high — crowding risk
        return None

    momentum_component = min(3.0, max(0.0, (change_20d - 5.0) / 15.0 * 3.0))
    volume_component   = min(2.0, max(0.0, (vol_ratio - 1.2) / 1.8 * 2.0))
    base_score = 4.0 + momentum_component + volume_component

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1A_MOMENTUM_CONT",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


def _detect_52w_high_expansion(
    pw: PriceWindow,
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1A_52W_HIGH_EXPAND — 52-Week High Expansion

    Conditions:
    - Close within 2% of 52-week high (approaching breakout zone)
    - Close is higher than the previous 5-session average
    - Volume ≥ 1.5× 20-day average on the approach
    - 52-week high has not been broken in the last 5 sessions (fresh approach)

    Scoring:
    - base_score = 4.0 + proximity_score + momentum_score
    - proximity_score: 0–3.0 (closer to 52w high is higher)
    - momentum_score:  0–2.0 (volume confirmation)
    """
    if pw.n < 22:
        return None

    high_52 = pw.high_52w()
    if high_52 <= 0:
        return None

    proximity = pw.close() / high_52
    if proximity < 0.98:  # must be within 2% of 52w high
        return None
    if proximity > 1.01:  # already broken out too far (catch on first breakout, not post-rally)
        return None

    avg_vol   = pw.avg_volume(20)
    vol_ratio = pw.volume() / avg_vol if avg_vol > 0 else 0
    if vol_ratio < 1.5:
        return None

    # Confirm the 52w high was not already broken in the last 5 sessions
    recent_highs = pw.highs[-6:-1]
    if recent_highs and max(recent_highs) >= high_52 * 0.995:
        # Already broken recently — this is not a fresh approach
        return None

    avg_close_5 = sum(pw.closes[-6:-1]) / 5
    if pw.close() <= avg_close_5:
        return None

    proximity_score = (proximity - 0.98) / 0.02 * 3.0
    volume_score    = min(2.0, (vol_ratio - 1.5) / 1.5 * 2.0)
    base_score = 4.0 + proximity_score + volume_score

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1A_52W_HIGH_EXPAND",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


def _detect_sector_breakout_accelerator(
    pw: PriceWindow,
    detected_at: str,
    regime: str,
    sector_return_5d: Optional[float] = None,
) -> Optional[RawSignal]:
    """
    DNA_1A_SECTOR_BKT — Sector Breakout Accelerator

    Conditions:
    - 10-day return > 7% (strong individual move)
    - Volume ≥ 1.3× 20-day average (accumulation)
    - If sector_return_5d is available: stock is outperforming sector by > 2%
    - RSI proxy (14-day) between 55 and 80 (moving but not overbought)

    Scoring:
    - base_score = 4.0 + breakout_component + outperformance_component
    """
    if pw.n < 22:
        return None

    change_10d = pw.price_change_pct(10)
    if change_10d < 7.0:
        return None

    avg_vol   = pw.avg_volume(20)
    vol_ratio = pw.volume() / avg_vol if avg_vol > 0 else 0
    if vol_ratio < 1.3:
        return None

    # Simplified RSI proxy using closing gains vs losses
    def _rsi_proxy(closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains = [max(0, closes[i] - closes[i - 1]) for i in range(-period, 0)]
        losses = [max(0, closes[i - 1] - closes[i]) for i in range(-period, 0)]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    rsi = _rsi_proxy(pw.closes)
    if not (55 <= rsi <= 80):
        return None

    breakout_component = min(2.0, (change_10d - 7.0) / 8.0 * 2.0)
    outperformance_component = 0.0
    if sector_return_5d is not None:
        stock_5d = pw.price_change_pct(5)
        outperformance = stock_5d - sector_return_5d
        if outperformance < 2.0:
            return None
        outperformance_component = min(2.0, outperformance / 5.0 * 2.0)
    else:
        # No sector data — apply a neutral modifier
        outperformance_component = 0.5

    base_score = 4.0 + breakout_component + outperformance_component

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1A_SECTOR_BKT",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


def _detect_results_followthrough(
    pw: PriceWindow,
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1A_RESULTS_FOLLOWTHR — Results Follow-Through

    Phase A proxy (no corporate event calendar available):
    Looks for a single large-gap-up day (> 3%) followed by at least 3 days of
    continued positive closes with declining volume (healthy absorption).

    This is a conservative proxy. The real archetype activates with
    `daily_events` pipeline (Phase E0). For now this fires only on clear
    post-results follow-through patterns.

    Conditions:
    - A single-day gap-up > 3% in the last 5 sessions
    - The 3 sessions after the gap are all positive (close > prior close)
    - Volume on the gap day ≥ 2× 20-day average (results volume burst)
    - Volume in the 3 follow-through days is < volume on gap day (settling)
    """
    if pw.n < 25:
        return None

    # Look for gap day in last 5 sessions (excluding today)
    gap_idx = None
    gap_pct = 0.0
    for i in range(-5, -1):
        day_return = (pw.closes[i] / pw.closes[i - 1] - 1.0) * 100
        if day_return > 3.0:
            gap_idx = i
            gap_pct = day_return
            break

    if gap_idx is None:
        return None

    # Volume on gap day must be ≥ 2× 20-day avg
    avg_vol = pw.avg_volume(20)
    gap_volume = pw.volumes[gap_idx]
    if avg_vol <= 0 or gap_volume < 2.0 * avg_vol:
        return None

    # Check 3 follow-through days after gap_idx
    if abs(gap_idx) < 3:
        return None  # not enough follow-through data yet

    follow_closes  = [pw.closes[gap_idx + k] for k in range(1, 4) if (gap_idx + k) < 0]
    follow_volumes = [pw.volumes[gap_idx + k] for k in range(1, 4) if (gap_idx + k) < 0]

    if len(follow_closes) < 3:
        return None

    # All 3 follow days must be up
    ref_close = pw.closes[gap_idx - 1]
    prev = pw.closes[gap_idx]
    for c in follow_closes:
        if c <= prev:
            return None
        prev = c

    # Volume declining after gap
    if follow_volumes and max(follow_volumes) >= gap_volume:
        return None

    gap_score     = min(2.0, (gap_pct - 3.0) / 5.0 * 2.0)
    volume_score  = min(2.0, (gap_volume / avg_vol - 2.0) / 3.0 * 2.0)
    base_score = 4.0 + gap_score + volume_score

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1A_RESULTS_FOLLOWTHR",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


# ---------------------------------------------------------------------------
# Per-symbol scan (all archetypes)
# ---------------------------------------------------------------------------

def scan_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    detected_at: str,
    regime: str,
    sector_return_5d: Optional[float] = None,
) -> list[RawSignal]:
    """
    Run all Layer 1A archetypes on a single symbol.
    Returns only signals with base_score > MIN_WRITE_THRESHOLD (4.0).
    Does NOT write to the database.
    """
    pw = _load_price_window(conn, symbol, detected_at)
    if pw is None:
        log.debug("[Layer1A] %s: insufficient price history — skipping", symbol)
        return []

    detectors = [
        lambda: _detect_momentum_continuation(pw, detected_at, regime),
        lambda: _detect_52w_high_expansion(pw, detected_at, regime),
        lambda: _detect_sector_breakout_accelerator(pw, detected_at, regime, sector_return_5d),
        lambda: _detect_results_followthrough(pw, detected_at, regime),
    ]

    signals = []
    for detector in detectors:
        raw = detector()
        if raw is not None and raw.qualifies:
            signals.append(raw)

    if signals:
        log.info(
            "[Layer1A] %s: %d signal(s) detected: %s",
            symbol,
            len(signals),
            [f"{s.archetype_id}={s.base_score:.2f}" for s in signals],
        )
    return signals


# ---------------------------------------------------------------------------
# Full universe scan
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    scan_date:          str
    regime:             str
    symbols_scanned:    int = 0
    signals_raw:        list[RawSignal] = field(default_factory=list)
    symbols_no_data:    int = 0

    @property
    def qualifying_signals(self) -> list[RawSignal]:
        return [s for s in self.signals_raw if s.qualifies]


def run_scan(
    conn: sqlite3.Connection,
    symbols: list[str],
    scan_date: str,
    regime: str,
) -> ScanResult:
    """
    Run Layer 1A scanner across all symbols.
    Returns ScanResult — signals are not written to DB here.
    The caller passes qualifying signals to the Opportunity Service.
    """
    result = ScanResult(scan_date=scan_date, regime=regime)

    for symbol in symbols:
        result.symbols_scanned += 1
        signals = scan_symbol(conn, symbol, scan_date, regime)
        result.signals_raw.extend(signals)
        if not signals:
            # Check if we even have data for this symbol
            has_data = conn.execute(
                "SELECT 1 FROM ohlcv_daily WHERE symbol=? LIMIT 1", (symbol,)
            ).fetchone()
            if not has_data:
                result.symbols_no_data += 1

    log.info(
        "[Layer1A] Scan complete date=%s regime=%s scanned=%d raw_signals=%d qualifying=%d",
        scan_date, regime,
        result.symbols_scanned,
        len(result.signals_raw),
        len(result.qualifying_signals),
    )
    return result
