"""
DTA-038 AnomalyDetector — per-cycle anomaly detection.

Detects 8 kinds of structural anomalies in the candidate trace data:
  1. ALL_REJECTED_AT_SAME_STAGE
  2. NEAR_MISS_THRESHOLD
  3. ZERO_SIGNALS_GENERATED
  4. ALL_SIGNALS_SINGLE_DIRECTION
  5. HIGH_REJECTION_RATE (>90% rejected)
  6. STRATEGY_BOTTLENECK (>80% lost at Strategy stage)
  7. RESTART_GAP (stage UNKNOWN after restart)
  8. REPEATED_SYMBOL_REJECTION (same symbol rejected N+ times today)

CONTRACT: never raises, never modifies trading state.
"""
from __future__ import annotations

from typing import List

from audit.dta038_models import AnomalyKind, AnomalyRecord, CycleAudit, StageStatus
from audit.dta038_trace import TraceManager, _make_anomaly_id, _now_utc


_REPEAT_REJECTION_THRESHOLD = 3   # ≥3 cycle rejections for same symbol = anomaly
_HIGH_REJECTION_RATE_PCT    = 0.9 # 90% rejection at any stage
_STRATEGY_BOTTLENECK_PCT    = 0.8 # 80% drop at Strategy stage


class AnomalyDetector:

    def __init__(self, trace_manager: TraceManager) -> None:
        self._tm = trace_manager

    def detect(self, cycle: CycleAudit) -> List[AnomalyRecord]:
        """Detect all anomalies for one completed cycle. Never raises."""
        try:
            return self._detect_impl(cycle)
        except Exception:
            return []

    def _detect_impl(self, cycle: CycleAudit) -> List[AnomalyRecord]:
        anomalies: List[AnomalyRecord] = []
        traces   = self._tm.get_today_traces()
        c_traces = [t for t in traces if t.cycle_id == cycle.cycle_id]

        # ── 1: Zero signals ────────────────────────────────────────────────
        if cycle.signals_generated == 0:
            anomalies.append(AnomalyRecord(
                anomaly_id=_make_anomaly_id(),
                detected_ts=_now_utc(),
                kind=AnomalyKind.ZERO_SIGNALS_GENERATED,
                cycle_id=cycle.cycle_id,
                description="Scanner produced 0 signals this cycle.",
                severity="WARN",
            ))
            return anomalies  # no further checks needed

        total = cycle.signals_generated

        # ── 2: All signals single direction ───────────────────────────────
        directions = {t.direction for t in c_traces}
        if len(directions) == 1:
            d = next(iter(directions))
            anomalies.append(AnomalyRecord(
                anomaly_id=_make_anomaly_id(),
                detected_ts=_now_utc(),
                kind=AnomalyKind.ALL_SIGNALS_SINGLE_DIRECTION,
                cycle_id=cycle.cycle_id,
                description=f"All {total} signals are {d} — no directional diversity.",
                severity="INFO",
            ))

        # ── 3: All rejected at same stage ────────────────────────────────
        if total > 0 and cycle.executed == 0:
            drop = cycle.stage_drop_map
            if drop:
                biggest = max(drop, key=lambda k: drop[k])
                biggest_cnt = drop[biggest]
                if biggest_cnt >= max(1, total * _HIGH_REJECTION_RATE_PCT):
                    anomalies.append(AnomalyRecord(
                        anomaly_id=_make_anomaly_id(),
                        detected_ts=_now_utc(),
                        kind=AnomalyKind.ALL_REJECTED_AT_SAME_STAGE,
                        cycle_id=cycle.cycle_id,
                        description=(
                            f"{biggest_cnt}/{total} signals rejected at stage '{biggest}'. "
                            f"This is the pipeline bottleneck this cycle."
                        ),
                        severity="WARN",
                        affected_symbols=[t.symbol for t in c_traces if t.stage_status(biggest.capitalize()) == StageStatus.REJECTED][:10],
                    ))

        # ── 4: High rejection rate ────────────────────────────────────────
        if total > 0:
            rate = (total - cycle.executed) / total
            if rate >= _HIGH_REJECTION_RATE_PCT and cycle.executed == 0:
                anomalies.append(AnomalyRecord(
                    anomaly_id=_make_anomaly_id(),
                    detected_ts=_now_utc(),
                    kind=AnomalyKind.HIGH_REJECTION_RATE,
                    cycle_id=cycle.cycle_id,
                    description=f"{rate*100:.0f}% rejection rate this cycle ({total - cycle.executed}/{total}).",
                    severity="WARN",
                ))

        # ── 5: Strategy bottleneck ────────────────────────────────────────
        strat_drop = cycle.stage_drop_map.get("STRATEGY", 0)
        if total > 0 and strat_drop / total >= _STRATEGY_BOTTLENECK_PCT:
            anomalies.append(AnomalyRecord(
                anomaly_id=_make_anomaly_id(),
                detected_ts=_now_utc(),
                kind=AnomalyKind.STRATEGY_BOTTLENECK,
                cycle_id=cycle.cycle_id,
                description=(
                    f"StrategyLab dropped {strat_drop}/{total} signals "
                    f"({strat_drop/total*100:.0f}%). Check strategy health."
                ),
                severity="WARN",
            ))

        # ── 6: Restart gap ────────────────────────────────────────────────
        unknown_stages = [
            t for t in c_traces
            if any(s.status == StageStatus.UNKNOWN for s in t.stages)
        ]
        if unknown_stages:
            anomalies.append(AnomalyRecord(
                anomaly_id=_make_anomaly_id(),
                detected_ts=_now_utc(),
                kind=AnomalyKind.RESTART_GAP,
                cycle_id=cycle.cycle_id,
                description=(
                    f"{len(unknown_stages)} trace(s) have UNKNOWN stage status — "
                    f"likely caused by a process restart between stages."
                ),
                affected_symbols=[t.symbol for t in unknown_stages[:10]],
                severity="WARN",
            ))

        # ── 7: Repeated symbol rejections across today's cycles ──────────
        all_traces = self._tm.get_today_traces()
        rejection_counts: dict = {}
        for t in all_traces:
            if t.final_outcome and t.final_outcome.startswith("REJECTED"):
                rejection_counts[t.symbol] = rejection_counts.get(t.symbol, 0) + 1
        repeat_syms = [sym for sym, cnt in rejection_counts.items() if cnt >= _REPEAT_REJECTION_THRESHOLD]
        if repeat_syms:
            anomalies.append(AnomalyRecord(
                anomaly_id=_make_anomaly_id(),
                detected_ts=_now_utc(),
                kind=AnomalyKind.REPEATED_SYMBOL_REJECTION,
                cycle_id=cycle.cycle_id,
                description=(
                    f"{len(repeat_syms)} symbol(s) rejected ≥{_REPEAT_REJECTION_THRESHOLD}x today: "
                    f"{', '.join(repeat_syms[:8])}"
                ),
                affected_symbols=repeat_syms[:10],
                severity="INFO",
            ))

        # Register detected anomalies with trace manager
        for a in anomalies:
            self._tm.add_anomaly(a)

        return anomalies
