"""iios/integration/history/analytics/history_analytics.py

Computes descriptive statistics over a set of HistoricalRecord objects.

Deliberately lightweight — no Pandas/NumPy dependency.
Consumers that need advanced analytics can import results and process further.
"""
from __future__ import annotations

import math
import time
from typing import Any

from iios.integration.history.core.historical_record import HistoricalRecord


class HistoryAnalytics:
    """
    Computes basic statistics for a list of historical records.
    """

    def compute(self, records: list[HistoricalRecord]) -> dict[str, Any]:
        """
        Return a summary dict with count, time span, value stats,
        and per-symbol breakdowns.
        """
        if not records:
            return {
                "count": 0,
                "start_ts": 0.0,
                "end_ts":   0.0,
                "span_days": 0.0,
                "symbols":  {},
                "computed_at": time.time(),
            }

        start_ts = min(r.timestamp for r in records)
        end_ts   = max(r.timestamp for r in records)
        span_sec = end_ts - start_ts

        # Per-symbol record counts
        sym_counts: dict[str, int] = {}
        for r in records:
            sym_counts[r.symbol or ""] = sym_counts.get(r.symbol or "", 0) + 1

        # Numeric value stats (if records have a "value" key in data)
        values = [r.data["value"] for r in records if isinstance(r.data.get("value"), (int, float))]

        return {
            "count":     len(records),
            "start_ts":  start_ts,
            "end_ts":    end_ts,
            "span_days": span_sec / 86_400,
            "symbols":   sym_counts,
            "value_stats": self._describe(values),
            "computed_at": time.time(),
        }

    @staticmethod
    def _describe(values: list[float]) -> dict[str, float]:
        if not values:
            return {}
        n   = len(values)
        mu  = sum(values) / n
        var = sum((x - mu) ** 2 for x in values) / n
        return {
            "count": n,
            "min":   min(values),
            "max":   max(values),
            "mean":  round(mu, 6),
            "std":   round(math.sqrt(var), 6),
        }

    def records_per_day(
        self,
        records: list[HistoricalRecord],
    ) -> dict[str, int]:
        """
        Return a {YYYY-MM-DD → count} dict.
        """
        from datetime import datetime, timezone
        result: dict[str, int] = {}
        for r in records:
            day = datetime.fromtimestamp(r.timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
            result[day] = result.get(day, 0) + 1
        return result
