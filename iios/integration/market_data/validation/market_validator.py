"""iios/integration/market_data/validation/market_validator.py

Orchestrates all validation steps for incoming market data.
"""
from __future__ import annotations

import time
from typing import Any

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_tick      import MarketTick
from iios.integration.market_data.core.market_trade     import MarketTrade
from iios.integration.market_data.market_data_constants import DEFAULT_STALE_QUOTE_SEC, AnomalyType
from iios.integration.market_data.validation.anomaly_detector   import AnomalyDetector
from iios.integration.market_data.validation.duplicate_detector import DuplicateDetector
from iios.integration.market_data.validation.gap_detector       import GapDetector
from iios.integration.market_data.validation.quality_report     import QualityIssue, QualityReport


class MarketValidator:
    """
    Composite validator for all market data types.

    Creates and maintains one:
    - GapDetector      (per validator instance, shared across symbols)
    - DuplicateDetector
    - AnomalyDetector

    Returns QualityReport for batch validation.
    """

    def __init__(
        self,
        provider_id:       str   = "",
        max_gap_sec:       float = 300.0,
        stale_threshold:   float = DEFAULT_STALE_QUOTE_SEC,
        max_future_sec:    float = 5.0,
        dup_window:        int   = 50_000,
    ) -> None:
        self._provider_id     = provider_id
        self._stale_sec       = stale_threshold
        self._max_future_sec  = max_future_sec
        self._gap      = GapDetector(max_gap_sec=max_gap_sec)
        self._dup      = DuplicateDetector(window_size=dup_window)
        self._anomaly  = AnomalyDetector()
        self._total_validated = 0
        self._total_issues    = 0

    # ── Per-type validation ────────────────────────────────────────────────────

    def validate_tick(self, tick: MarketTick) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        issues.extend(self._timestamp_checks(tick.symbol, tick.timestamp, tick.received_at))
        if d := self._dup.check_tick(tick):
            issues.append(d)
        if g := self._gap.check_tick(tick):
            issues.append(g)
        issues.extend(self._anomaly.check_tick(tick))
        self._tally(issues)
        return issues

    def validate_quote(self, quote: MarketQuote) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        issues.extend(self._timestamp_checks(quote.symbol, quote.timestamp, quote.received_at))
        if d := self._dup.check_quote(quote):
            issues.append(d)
        if g := self._gap.check_quote(quote):
            issues.append(g)
        issues.extend(self._anomaly.check_quote(quote))
        self._tally(issues)
        return issues

    def validate_trade(self, trade: MarketTrade) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        issues.extend(self._timestamp_checks(trade.symbol, trade.timestamp, trade.received_at))
        if d := self._dup.check_trade(trade):
            issues.append(d)
        issues.extend(self._anomaly.check_trade(trade))
        self._tally(issues)
        return issues

    def validate_candle(self, candle: MarketCandle) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        if d := self._dup.check_candle(candle):
            issues.append(d)
        if g := self._gap.check_candle(candle):
            issues.append(g)
        issues.extend(self._anomaly.check_candle(candle))
        self._tally(issues)
        return issues

    def validate_snapshot(self, snap: MarketSnapshot) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        issues.extend(self._timestamp_checks(snap.symbol, snap.timestamp, snap.received_at))
        if snap.bid > 0 and snap.ask > 0 and snap.bid > snap.ask:
            issues.append(QualityIssue(
                anomaly_type=AnomalyType.SPREAD_INVERSION, symbol=snap.symbol,
                field_name="bid_ask",
                message=f"Inverted spread in snapshot for {snap.symbol}.",
                severity="error",
            ))
        self._tally(issues)
        return issues

    # ── Batch report ──────────────────────────────────────────────────────────

    def validate_ticks_batch(self, ticks: list[MarketTick]) -> QualityReport:
        rpt = QualityReport(
            provider_id  = self._provider_id,
            symbol       = ticks[0].symbol if ticks else "",
            period_start = min(t.timestamp for t in ticks) if ticks else 0.0,
            period_end   = max(t.timestamp for t in ticks) if ticks else 0.0,
            total_records = len(ticks),
        )
        for tick in ticks:
            issues = self.validate_tick(tick)
            if issues:
                rpt.invalid_records += 1
                for iss in issues:
                    rpt.add_issue(iss)
            else:
                rpt.valid_records += 1
        rpt.compute_score()
        return rpt

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "provider_id":     self._provider_id,
            "total_validated": self._total_validated,
            "total_issues":    self._total_issues,
            "gap":             self._gap.stats(),
            "duplicate":       self._dup.stats(),
            "anomaly":         self._anomaly.stats(),
        }

    # ── Internals ──────────────────────────────────────────────────────────────

    def _timestamp_checks(
        self, symbol: str, ts: float, received_at: float
    ) -> list[QualityIssue]:
        now = time.time()
        issues: list[QualityIssue] = []
        if ts > now + self._max_future_sec:
            issues.append(QualityIssue(
                anomaly_type = AnomalyType.FUTURE_TIMESTAMP,
                symbol       = symbol,
                field_name   = "timestamp",
                message      = f"Future timestamp {ts:.0f} for {symbol} (now={now:.0f}).",
                severity     = "error",
                value        = ts,
            ))
        if (now - received_at) > self._stale_sec:
            issues.append(QualityIssue(
                anomaly_type = AnomalyType.STALE_TIMESTAMP,
                symbol       = symbol,
                field_name   = "received_at",
                message      = f"Stale record for {symbol} (age={(now-received_at):.0f}s).",
                severity     = "warning",
                value        = received_at,
            ))
        return issues

    def _tally(self, issues: list[QualityIssue]) -> None:
        self._total_validated += 1
        self._total_issues += len(issues)
