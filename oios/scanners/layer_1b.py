"""
oios/scanners/layer_1b.py

Layer 1B — Early Warning DNA Scanner

Question: What is quietly building before a public cause emerges?

Detects stocks showing accumulation signals — rising delivery, quiet volume
build, tight price consolidation — that precede a visible public catalyst.

Phase B archetypes:
  DNA_1B_QUIET_ACCUMULATION  — volume building quietly under the surface
  DNA_1B_DELIVERY_EXPANSION  — delivery % rising (genuine holders accumulating)
  DNA_1B_LOW_NOISE_STRENGTH  — tight range with gradual upward drift
  DNA_1B_SECTOR_PRE_BKT      — sector breadth building before individual breakout

Signal type: "1B"
Minimum write threshold: base_score > 4.0
Phase B defaults: expected_move_pct=8.0, expected_ttl_days=18

CRITICAL: This scanner does NOT write to the database.
All writes go through:
  Scanner → Opportunity Service → Repository → Database

This discipline is mandatory (MAS Section 7, Phase B Build Order).
"""

from __future__ import annotations
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (Phase B defaults per MAS Section 5, Layer 1B)
# ---------------------------------------------------------------------------

MIN_WRITE_THRESHOLD = 4.0   # base_score must exceed this to write signal_birth
EXPECTED_MOVE_PCT   = 8.0   # universal default until archetype distributions are active
EXPECTED_TTL_DAYS   = 18    # Phase B default — 1B signals have longer TTL than 1A
SIGNAL_TYPE         = "1B"
ARCHETYPE_VERSION   = 1


# ---------------------------------------------------------------------------
# Raw detection result — imported from layer_1a to avoid duplication
# We keep a local RawSignal definition so layer_1b has no cross-scanner import
# ---------------------------------------------------------------------------

@dataclass
class RawSignal:
    """
    Output of a Layer 1B archetype detector.
    Not yet persisted — the scanner creates these; the service layer writes them.
    """
    symbol:                   str
    archetype_id:             str
    base_score:               float
    direction:                str             # "LONG" | "SHORT"
    detected_at:              str             # ISO-8601 date
    birth_price:              float
    regime:                   str

    signal_type:              str             = SIGNAL_TYPE
    archetype_version:        int             = ARCHETYPE_VERSION
    expected_ttl_days:        int             = EXPECTED_TTL_DAYS
    expected_move_pct:        float           = EXPECTED_MOVE_PCT
    expected_move_pct_source: str             = "UNIVERSAL_DEFAULT_8PCT"
    theme_phase_at_birth:     Optional[str]   = None
    consensus_score_at_birth: Optional[float] = None

    @property
    def qualifies(self) -> bool:
        return self.base_score > MIN_WRITE_THRESHOLD


# ---------------------------------------------------------------------------
# OHLCV price window — same structure as Layer 1A
# ---------------------------------------------------------------------------

@dataclass
class PriceWindow:
    symbol:  str
    dates:   list[str]
    closes:  list[float]
    volumes: list[float]
    highs:   list[float]
    lows:    list[float]

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

    def sma(self, period: int) -> float:
        if self.n < period:
            return self.close()
        return sum(self.closes[-period:]) / period

    def atr_pct(self, period: int = 14) -> float:
        """ATR as a percentage of close price. Measures volatility/noise."""
        if self.n < period + 1:
            return 0.0
        trs = []
        for i in range(-period, 0):
            high = self.highs[i]
            low  = self.lows[i]
            prev_close = self.closes[i - 1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        avg_tr = sum(trs) / len(trs)
        return (avg_tr / self.close()) * 100 if self.close() > 0 else 0.0

    def price_change_pct(self, lookback: int) -> float:
        if self.n < lookback + 1:
            return 0.0
        return (self.closes[-1] / self.closes[-(lookback + 1)] - 1.0) * 100


# ---------------------------------------------------------------------------
# BHAV delivery window — daily delivery percentage per symbol
# ---------------------------------------------------------------------------

@dataclass
class BhavWindow:
    symbol:          str
    dates:           list[str]
    delivery_pcts:   list[float]   # 0.0–1.0; stored as fraction

    @property
    def n(self) -> int:
        return len(self.delivery_pcts)

    def latest(self) -> float:
        return self.delivery_pcts[-1] if self.delivery_pcts else 0.0

    def ago(self, days: int) -> float:
        """Delivery pct `days` sessions ago. Returns 0.0 if not enough history."""
        idx = -(days + 1)
        if abs(idx) > self.n:
            return 0.0
        return self.delivery_pcts[idx]

    def trend(self, days: int = 5) -> float:
        """Latest delivery pct minus pct `days` sessions ago."""
        return self.latest() - self.ago(days)


# ---------------------------------------------------------------------------
# Data loaders — SELECT only, no writes
# ---------------------------------------------------------------------------

def _load_price_window(
    conn: sqlite3.Connection,
    symbol: str,
    as_of_date: str,
    lookback_rows: int = 252,
) -> Optional[PriceWindow]:
    """
    Load the last lookback_rows trading sessions for symbol up to as_of_date.
    Returns None if fewer than 25 rows available.
    """
    rows = conn.execute("""
        SELECT trade_date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (symbol, as_of_date, lookback_rows)).fetchall()

    if len(rows) < 25:
        return None

    rows.reverse()
    return PriceWindow(
        symbol  = symbol,
        dates   = [r[0] for r in rows],
        closes  = [r[4] for r in rows],
        volumes = [r[5] for r in rows],
        highs   = [r[2] for r in rows],
        lows    = [r[3] for r in rows],
    )


def _load_bhav_window(
    conn: sqlite3.Connection,
    symbol: str,
    as_of_date: str,
    lookback_rows: int = 30,
) -> Optional[BhavWindow]:
    """
    Load BHAV delivery percentage history for symbol.
    Returns None if fewer than 5 rows available — Delivery Expansion archetype
    gracefully degrades when BHAV data is not yet populated.
    """
    rows = conn.execute("""
        SELECT trade_date, delivery_pct
        FROM bhav_daily
        WHERE symbol = ?
          AND trade_date <= ?
          AND delivery_pct IS NOT NULL
        ORDER BY trade_date DESC
        LIMIT ?
    """, (symbol, as_of_date, lookback_rows)).fetchall()

    if len(rows) < 5:
        return None

    rows.reverse()
    return BhavWindow(
        symbol        = symbol,
        dates         = [r[0] for r in rows],
        delivery_pcts = [float(r[1]) for r in rows],
    )


def _sector_breadth(
    conn: sqlite3.Connection,
    symbol: str,
    as_of_date: str,
) -> Optional[float]:
    """
    Compute what fraction of the symbol's sector had positive 5-day returns,
    weighted by sector_purity_score. Returns None when < 5 sector peers have data.
    Excludes the symbol itself.
    """
    sector_row = conn.execute(
        "SELECT sector FROM universe_stocks WHERE symbol = ? AND is_active = 1",
        (symbol,),
    ).fetchone()
    if sector_row is None:
        return None

    sector = sector_row[0]

    peers = conn.execute("""
        SELECT u.symbol, u.sector_purity_score
        FROM universe_stocks u
        WHERE u.sector = ? AND u.is_active = 1 AND u.symbol != ?
    """, (sector, symbol)).fetchall()

    if len(peers) < 4:
        return None

    # For each peer compute 5-day return from ohlcv_daily
    weighted_positive = 0.0
    weight_total = 0.0
    peers_with_data = 0

    for peer_sym, purity in peers:
        rows = conn.execute("""
            SELECT close FROM ohlcv_daily
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date DESC LIMIT 6
        """, (peer_sym, as_of_date)).fetchall()

        if len(rows) < 6:
            continue

        closes = [r[0] for r in rows]
        ret_5d = (closes[0] / closes[5] - 1.0) * 100
        weight_total += purity
        if ret_5d > 0:
            weighted_positive += purity
        peers_with_data += 1

    if peers_with_data < 4:
        return None

    return weighted_positive / weight_total if weight_total > 0 else 0.0


# ---------------------------------------------------------------------------
# Archetype detectors
# ---------------------------------------------------------------------------

def _detect_quiet_accumulation(
    pw: PriceWindow,
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1B_QUIET_ACCUMULATION — Volume building quietly without price breakout

    This is the early warning equivalent of Momentum Continuation.
    The stock is accumulating at a base — volume trending up while price
    stays rangebound. Not yet a public breakout — hence "quiet".

    Conditions:
    - 5-day average volume > 10-day average volume (volume building)
    - 10-day average volume > 20-day average volume (trend confirmed)
    - Price range is narrowing: daily range last 5d < daily range last 10d
    - Price above 20-day SMA (holding a support level)
    - Today's volume < 2× 20-day avg (NOT a spike — accumulation is quiet)
    - 20-day price change between -2% and +8% (not already broken out)

    Scoring:
    - base_score = 4.0 + volume_trend + consolidation
    """
    if pw.n < 22:
        return None

    # Volume must be building over multiple timeframes
    avg_vol_5  = sum(pw.volumes[-6:-1]) / 5
    avg_vol_10 = sum(pw.volumes[-11:-1]) / 10
    avg_vol_20 = pw.avg_volume(20)

    if avg_vol_5 <= avg_vol_10:
        return None
    if avg_vol_10 <= avg_vol_20:
        return None

    # Not a single spike — quiet accumulation
    if pw.volume() > 2.0 * avg_vol_20:
        return None

    # Price holding above 20-day SMA
    sma_20 = pw.sma(20)
    if pw.close() < sma_20:
        return None

    # Not already broken out (20d change < 8%)
    change_20d = pw.price_change_pct(20)
    if change_20d > 8.0 or change_20d < -2.0:
        return None

    # Range narrowing: compare avg daily range last 5 vs last 10
    range_5  = sum(pw.highs[i] - pw.lows[i] for i in range(-6, -1)) / 5
    range_10 = sum(pw.highs[i] - pw.lows[i] for i in range(-11, -1)) / 10
    if range_5 >= range_10:
        return None

    # Score: volume trend strength + consolidation tightness
    vol_trend_ratio   = avg_vol_5 / avg_vol_20  # how far above average
    volume_component  = min(2.0, max(0.0, (vol_trend_ratio - 1.0) / 0.5 * 2.0))
    range_compression = 1.0 - (range_5 / range_10)  # 0 = unchanged, 1 = fully compressed
    consolidation     = min(2.0, range_compression * 4.0)

    base_score = 4.0 + volume_component + consolidation

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1B_QUIET_ACCUMULATION",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


def _detect_delivery_expansion(
    pw: PriceWindow,
    bw: Optional[BhavWindow],
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1B_DELIVERY_EXPANSION — Delivery percentage rising (genuine holders accumulating)

    Rising delivery % means buyers are holding overnight rather than squaring off intraday.
    This is a structural demand signal — not speculation.

    Requires BHAV data. Degrades gracefully if unavailable.

    Conditions:
    - BHAV window available (>= 10 rows with delivery data)
    - Delivery % today > 30% (not trivially low)
    - Delivery % today > delivery % 5 days ago (expanding)
    - 5-day trend in delivery > 0.05 (5 percentage points up, minimum)
    - Volumes are not collapsing (avg_vol_5d >= 0.7 × avg_vol_20d)
    - Price not declining sharply (5d return > -3%)

    Scoring:
    - base_score = 4.0 + delivery_expansion + price_strength
    """
    if bw is None or bw.n < 10:
        # Graceful degradation: no BHAV data for this symbol
        return None

    if pw.n < 22:
        return None

    latest_delivery = bw.latest()
    if latest_delivery < 0.30:
        return None

    trend_5d = bw.trend(5)
    if trend_5d < 0.05:
        return None

    delivery_5d_ago = bw.ago(5)
    if latest_delivery <= delivery_5d_ago:
        return None

    # Volume not collapsing
    avg_vol_5  = sum(pw.volumes[-6:-1]) / 5
    avg_vol_20 = pw.avg_volume(20)
    if avg_vol_20 > 0 and avg_vol_5 < 0.70 * avg_vol_20:
        return None

    # Price not in a downtrend
    change_5d = pw.price_change_pct(5)
    if change_5d < -3.0:
        return None

    # Score
    delivery_expansion = min(2.5, (trend_5d / 0.25) * 2.5)  # 5pp → 0, 25pp → max
    price_strength     = min(1.5, max(0.0, (change_5d + 3.0) / 8.0 * 1.5))

    base_score = 4.0 + delivery_expansion + price_strength

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1B_DELIVERY_EXPANSION",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


def _detect_low_noise_strength(
    pw: PriceWindow,
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1B_LOW_NOISE_STRENGTH — Tight range with gradual upward drift

    Strong stocks under professional accumulation exhibit:
    - Unusually low volatility (ATR % below normal)
    - Gradual upward drift: close > 5-day SMA > 10-day SMA > 20-day SMA
    - No volume spikes (no panic exits, no speculation)
    - Trend persisting: 5-day price change positive but modest (1–6%)

    Conditions:
    - 14-day ATR as % of close < 1.5% (very low noise)
    - SMA alignment: close > sma_5 > sma_10 > sma_20
    - 5-day price change between 1% and 6%
    - Max single-day range in last 10 days < 3% (no violent moves)

    Scoring:
    - base_score = 4.0 + noise_reduction + drift_quality
    """
    if pw.n < 22:
        return None

    atr_pct = pw.atr_pct(14)
    if atr_pct >= 1.5:
        return None

    sma_5  = pw.sma(5)
    sma_10 = pw.sma(10)
    sma_20 = pw.sma(20)

    # Strict SMA alignment
    if not (pw.close() > sma_5 > sma_10 > sma_20):
        return None

    change_5d = pw.price_change_pct(5)
    if not (1.0 <= change_5d <= 6.0):
        return None

    # No violent moves in last 10 days
    max_range_10d = max(
        (pw.highs[i] - pw.lows[i]) / pw.closes[i - 1] * 100
        for i in range(-10, 0)
        if pw.closes[i - 1] > 0
    )
    if max_range_10d >= 3.0:
        return None

    noise_reduction = min(2.0, (1.5 - atr_pct) / 1.5 * 2.0)
    drift_quality   = min(2.0, (change_5d - 1.0) / 5.0 * 2.0)

    base_score = 4.0 + noise_reduction + drift_quality

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1B_LOW_NOISE_STRENGTH",
        base_score   = round(base_score, 3),
        direction    = "LONG",
        detected_at  = detected_at,
        birth_price  = pw.close(),
        regime       = regime,
    )


def _detect_sector_pre_breakout(
    pw: PriceWindow,
    sector_breadth: Optional[float],
    detected_at: str,
    regime: str,
) -> Optional[RawSignal]:
    """
    DNA_1B_SECTOR_PRE_BKT — Sector breadth building before individual breakout

    When sector peers are quietly moving up (sector breadth building), a stock
    approaching its 20-day high with mid-range RSI is showing sector pre-breakout
    characteristics. This fires BEFORE the individual stock breaks out.

    Conditions:
    - Close within 5% of 20-day high (approaching breakout zone)
    - RSI proxy 45–65 (mid-range, not overbought — accumulation zone)
    - 20-day SMA is rising (slope positive: sma_20 today > sma_20 5d ago)
    - Sector breadth >= 0.50 (majority of sector peers positive 5-day return)
    - Volume not spiking (vol_today < 1.8× 20-day avg)

    Scoring:
    - base_score = 4.0 + proximity_score + breadth_score
    """
    if pw.n < 22:
        return None

    high_20d = max(pw.highs[-20:])
    if high_20d <= 0:
        return None

    proximity = pw.close() / high_20d
    if not (0.95 <= proximity <= 1.0):
        return None

    # RSI proxy
    def _rsi_proxy(closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains  = [max(0.0, closes[i] - closes[i - 1]) for i in range(-period, 0)]
        losses = [max(0.0, closes[i - 1] - closes[i]) for i in range(-period, 0)]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

    rsi = _rsi_proxy(pw.closes)
    if not (45 <= rsi <= 65):
        return None

    # SMA slope: compare current sma_20 vs sma_20 five sessions ago
    if pw.n < 26:
        return None
    sma_20_now  = sum(pw.closes[-20:]) / 20
    sma_20_5d   = sum(pw.closes[-25:-5]) / 20
    if sma_20_now <= sma_20_5d:
        return None

    # Volume not spiking
    avg_vol_20 = pw.avg_volume(20)
    if avg_vol_20 > 0 and pw.volume() > 1.8 * avg_vol_20:
        return None

    # Sector breadth
    if sector_breadth is None or sector_breadth < 0.50:
        return None

    proximity_score = (proximity - 0.95) / 0.05 * 2.0  # 0 at 95%, 2.0 at 100%
    breadth_score   = min(2.0, (sector_breadth - 0.50) / 0.30 * 2.0)

    base_score = 4.0 + proximity_score + breadth_score

    return RawSignal(
        symbol       = pw.symbol,
        archetype_id = "DNA_1B_SECTOR_PRE_BKT",
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
) -> list[RawSignal]:
    """
    Run all Layer 1B archetypes on a single symbol.
    Returns only signals with base_score > MIN_WRITE_THRESHOLD (4.0).
    Does NOT write to the database.
    """
    pw = _load_price_window(conn, symbol, detected_at)
    if pw is None:
        log.debug("[Layer1B] %s: insufficient price history — skipping", symbol)
        return []

    # Load BHAV window — may be None if not yet populated (graceful degradation)
    bw = _load_bhav_window(conn, symbol, detected_at)

    # Sector breadth — may be None if too few peers have data
    breadth = _sector_breadth(conn, symbol, detected_at)

    detectors = [
        lambda: _detect_quiet_accumulation(pw, detected_at, regime),
        lambda: _detect_delivery_expansion(pw, bw, detected_at, regime),
        lambda: _detect_low_noise_strength(pw, detected_at, regime),
        lambda: _detect_sector_pre_breakout(pw, breadth, detected_at, regime),
    ]

    signals = []
    for detector in detectors:
        raw = detector()
        if raw is not None and raw.qualifies:
            signals.append(raw)

    if signals:
        log.info(
            "[Layer1B] %s: %d signal(s) detected: %s",
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
    symbols_no_bhav:    int = 0   # graceful degradation counter

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
    Run Layer 1B scanner across all symbols.
    Returns ScanResult — signals are NOT written to DB here.
    The caller passes qualifying signals to the Opportunity Service.
    """
    result = ScanResult(scan_date=scan_date, regime=regime)

    for symbol in symbols:
        result.symbols_scanned += 1
        pw = _load_price_window(conn, symbol, scan_date)
        if pw is None:
            result.symbols_no_data += 1
            continue

        bw = _load_bhav_window(conn, symbol, scan_date)
        if bw is None:
            result.symbols_no_bhav += 1

        breadth = _sector_breadth(conn, symbol, scan_date)

        detectors = [
            lambda: _detect_quiet_accumulation(pw, scan_date, regime),
            lambda: _detect_delivery_expansion(pw, bw, scan_date, regime),
            lambda: _detect_low_noise_strength(pw, scan_date, regime),
            lambda: _detect_sector_pre_breakout(pw, breadth, scan_date, regime),
        ]

        for detector in detectors:
            raw = detector()
            if raw is not None and raw.qualifies:
                result.signals_raw.append(raw)

    log.info(
        "[Layer1B] Scan complete: %d scanned, %d qualifying signals, "
        "%d no_data, %d no_bhav",
        result.symbols_scanned,
        len(result.qualifying_signals),
        result.symbols_no_data,
        result.symbols_no_bhav,
    )
    return result
