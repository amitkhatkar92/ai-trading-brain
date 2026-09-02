"""DTA-041 point-in-time discovery evidence capture.

Records immutable discovery observations and separate append-only pipeline
events. This module never participates in trading decisions or execution.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set

from audit.dta038_trace import get_trace_manager


_DATA_DIR = Path(__file__).parent.parent / "data" / "audit" / "dta041"
_SCHEMA_VERSION = "1.0"
_INSTANCE: Optional["PITDiscoveryEvidenceRecorder"] = None
_INSTANCE_LOCK = threading.Lock()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_value(value: Any) -> Any:
    """Keep only JSON-safe decision-time values; never persist secrets."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if hasattr(value, "value"):
        return _json_value(value.value)
    return str(value)


class PITDiscoveryEvidenceRecorder:
    """Append-only recorder for all symbols evaluated by the live scanner."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DATA_DIR
        self._lock = threading.Lock()
        self._lineages: Dict[tuple[str, str], str] = {}

    def record_evaluation(
        self,
        candidate: Dict[str, Any],
        snapshot: Any,
        *,
        universe_size: int,
        prepared_count: int,
        prepared_rank: Optional[int] = None,
        evaluation_source: Optional[str] = None,
    ) -> str:
        """Write one immutable PIT observation before scanner setup detection."""
        try:
            symbol = str(candidate.get("symbol", "UNKNOWN") or "UNKNOWN").strip()
            cycle_id = get_trace_manager().get_cycle_id()
            key = (cycle_id, symbol)
            with self._lock:
                existing = self._lineages.get(key)
                if not existing:
                    trading_date = datetime.now(timezone.utc).date().isoformat()
                    lineage_id = f"PIT:{trading_date.replace('-', '')}:{cycle_id}:{symbol}"
                    self._lineages[key] = lineage_id
            if existing:
                if evaluation_source:
                    self._event(existing, "DISCOVERY_EVALUATION", "OBSERVED", {
                        "evaluation_source": evaluation_source,
                    })
                return existing

            source = evaluation_source or (
                "PREPARED" if candidate.get("_prepared") else "STATIC_GAP_FILL"
            )
            record = {
                "record_type": "PIT_OBSERVATION",
                "schema_version": _SCHEMA_VERSION,
                "lineage_id": lineage_id,
                "decision_timestamp": _now_utc(),
                "trading_date": trading_date,
                "cycle_id": cycle_id,
                "symbol": symbol,
                "universe": {
                    "source": "NIFTY500_DERIVED",
                    "universe_size": universe_size,
                    "prepared_count": prepared_count,
                },
                "prepared_universe": {
                    "included": bool(candidate.get("_prepared")),
                    "rank": prepared_rank,
                    "score": candidate.get("score"),
                    "selection_reason": candidate.get("buckets", []),
                    "selection_state": candidate.get("_lifecycle_state", "NOT_PREPARED"),
                    "evaluation_source": source,
                },
                "market_properties": {
                    "price": candidate.get("ltp"),
                    "rsi": candidate.get("rsi"),
                    "volume_ratio": candidate.get("volume_ratio"),
                    "atr": candidate.get("_atr14"),
                    "support": candidate.get("support"),
                    "resistance": candidate.get("resistance"),
                    "sector": candidate.get("sector"),
                    "regime": getattr(getattr(snapshot, "regime", None), "value", getattr(snapshot, "regime", None)),
                    "vix": getattr(snapshot, "vix", None),
                    "breadth": getattr(snapshot, "market_breadth", None),
                },
                "scanner": {"evaluated": True},
            }
            self._append(record)
            return lineage_id
        except Exception:
            return ""

    def record_scanner_result(self, lineage_id: str, signal: Any, reason: str) -> None:
        try:
            self._event(lineage_id, "SCANNER", "PASSED" if signal else "REJECTED", {
                "signal": bool(signal),
                "direction": getattr(getattr(signal, "direction", None), "value", None) if signal else None,
                "confidence": getattr(signal, "confidence", None) if signal else None,
                "entry": getattr(signal, "entry_price", None) if signal else None,
                "rejection_reason": None if signal else reason,
            })
        except Exception:
            pass

    def record_stage_outcomes(
        self, signals: Iterable[Any], passed_symbols: Set[str], stage: str, reason: str
    ) -> None:
        for signal in signals:
            try:
                lineage_id = self._lineage_for(signal)
                symbol = str(getattr(signal, "symbol", "") or "").strip()
                passed = symbol in passed_symbols
                self._event(lineage_id, stage, "PASSED" if passed else "REJECTED", {
                    "rejection_reason": None if passed else reason,
                })
            except Exception:
                pass

    def record_kda_results(self, signals: Iterable[Any], results: Dict[str, Dict[str, Any]]) -> None:
        for signal in signals:
            try:
                symbol = str(getattr(signal, "symbol", "") or "").strip()
                result = results.get(symbol, {})
                self._event(self._lineage_for(signal), "KDA", "OBSERVED", {
                    "decision": result.get("kda_decision"),
                    "authority": result.get("kda_authority"),
                    "evidence_state": result.get("evidence_state"),
                    "evidence_level": result.get("evidence_level"),
                    "effective_sample_size": result.get("effective_sample_size") or result.get("hbe_ess"),
                    "evidence_confidence": result.get("evidence_confidence"),
                    "target": result.get("knowledge_target"),
                    "stop": result.get("knowledge_stop"),
                    "expected_move_p50": result.get("expected_move_p50"),
                    "expected_days_p50": result.get("expected_days_p50"),
                    "fallback_used": result.get("fallback_used"),
                })
            except Exception:
                pass

    def _lineage_for(self, signal: Any) -> str:
        symbol = str(getattr(signal, "symbol", "UNKNOWN") or "UNKNOWN").strip()
        cycle_id = get_trace_manager().get_cycle_id()
        return self._lineages.get((cycle_id, symbol), "")

    def _event(self, lineage_id: str, stage: str, status: str, details: Dict[str, Any]) -> None:
        if not lineage_id:
            return
        self._append({
            "record_type": "PIT_PIPELINE_EVENT",
            "schema_version": _SCHEMA_VERSION,
            "lineage_id": lineage_id,
            "event_timestamp": _now_utc(),
            "stage": stage,
            "status": status,
            "details": _json_value(details),
        })

    def _append(self, record: Dict[str, Any]) -> None:
        path = self._data_dir / f"PIT_DISCOVERY_{datetime.now(timezone.utc).date().isoformat()}.jsonl"
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(_json_value(record), sort_keys=True) + "\n")


def get_pit_discovery_evidence_recorder() -> PITDiscoveryEvidenceRecorder:
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = PITDiscoveryEvidenceRecorder()
    return _INSTANCE