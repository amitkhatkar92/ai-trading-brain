"""
DTA-038 TraceManager — restart-safe, append-only candidate lifecycle tracing.

CONTRACT
--------
• Never raises — all public methods swallow exceptions internally.
• Append-only: every stage transition is written to JSONL before the next stage.
• Restart-safe: on process start, today's JSONL is loaded and in-memory state rebuilt.
• Zero effect on trading decisions, thresholds, or execution.
• Thread-safe via threading.Lock.

STORAGE
-------
  data/audit/dta038/DTA038_TRACE_YYYY-MM-DD.jsonl   — candidate stage events
  data/audit/dta038/DTA038_CYCLE_YYYY-MM-DD.jsonl   — cycle aggregate events
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from audit.dta038_models import (
    AnomalyKind, AnomalyRecord, CandidateTrace, CycleAudit, StageResult,
    StageStatus,
)

# ── Storage ─────────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data" / "audit" / "dta038"

# ── Module-level current cycle ID (set by orchestrator) ────────────────────
_CURRENT_CYCLE_ID: Optional[str] = None
_CURRENT_CYCLE_ID_LOCK = threading.Lock()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _make_trace_id(cycle_id: str, symbol: str, direction: str) -> str:
    date_part = cycle_id.split("_")[0] if "_" in cycle_id else cycle_id[:8]
    payload = f"{cycle_id}:{symbol}:{direction}"
    h = hashlib.md5(payload.encode()).hexdigest()[:6]
    return f"DTA038:{date_part}:{cycle_id}:{symbol}:{direction}:{h}"


def _make_anomaly_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"ANO:{ts}"


def _trace_file(date_str: str) -> Path:
    return _DATA_DIR / f"DTA038_TRACE_{date_str}.jsonl"


def _cycle_file(date_str: str) -> Path:
    return _DATA_DIR / f"DTA038_CYCLE_{date_str}.jsonl"


def _append_line(path: Path, record: dict) -> None:
    """Atomic line append; creates directory/file as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── TraceManager ─────────────────────────────────────────────────────────────

class TraceManager:
    """
    Singleton per process. Created once, loaded from daily file on first use.

    Thread-safe: all state mutations are guarded by _lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._traces: Dict[str, CandidateTrace] = {}    # trace_id → CandidateTrace
        self._cycles: Dict[str, CycleAudit] = {}        # cycle_id → CycleAudit
        self._anomalies: List[AnomalyRecord] = []
        # lookup: (cycle_id, symbol, direction) → trace_id
        self._key_map: Dict[tuple, str] = {}
        self._loaded_date: Optional[str] = None
        self._restart_recorded = False

    # ── Init / reload ──────────────────────────────────────────────────────

    def _ensure_loaded(self, date_str: str) -> None:
        """Load today's JSONL if not yet loaded, marking restart boundary."""
        with self._lock:
            if self._loaded_date == date_str:
                return
            self._load_from_file(date_str)
            self._loaded_date = date_str
            if not self._restart_recorded:
                self._write_restart_boundary(date_str)
                self._restart_recorded = True

    def _load_from_file(self, date_str: str) -> None:
        """Rebuild in-memory state from today's JSONL (called under _lock)."""
        path = _trace_file(date_str)
        if not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        evt = json.loads(raw)
                    except Exception:
                        continue
                    self._apply_event(evt)
        except Exception:
            pass

        # Load cycle file
        cpath = _cycle_file(date_str)
        if not cpath.exists():
            return
        try:
            with cpath.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        evt = json.loads(raw)
                    except Exception:
                        continue
                    if evt.get("event") == "CYCLE_START":
                        ca = CycleAudit(
                            cycle_id=evt.get("cycle_id", ""),
                            trading_date=evt.get("trading_date", date_str),
                            start_ts=evt.get("ts", ""),
                            regime=evt.get("regime", ""),
                            vix=float(evt.get("vix", 0.0)),
                        )
                        self._cycles[ca.cycle_id] = ca
                    elif evt.get("event") == "CYCLE_END":
                        cid = evt.get("cycle_id", "")
                        if cid in self._cycles:
                            ca = self._cycles[cid]
                            ca.end_ts = evt.get("ts")
                            ca.signals_generated = evt.get("signals_generated", ca.signals_generated)
                            ca.strategy_passed   = evt.get("strategy_passed", ca.strategy_passed)
                            ca.cre_passed        = evt.get("cre_passed", ca.cre_passed)
                            ca.risk_passed       = evt.get("risk_passed", ca.risk_passed)
                            ca.guardian_passed   = evt.get("guardian_passed", ca.guardian_passed)
                            ca.debate_input      = evt.get("debate_input", ca.debate_input)
                            ca.executed          = evt.get("executed", ca.executed)
                            ca.stage_drop_map    = evt.get("stage_drop_map", ca.stage_drop_map)
        except Exception:
            pass

    def _apply_event(self, evt: dict) -> None:
        """Apply one TRACE event to in-memory state (called under _lock)."""
        etype = evt.get("event")
        if etype == "TRACE_INIT":
            tid = evt.get("trace_id", "")
            if not tid or tid in self._traces:
                return
            ct = CandidateTrace(
                trace_id=tid,
                trading_date=evt.get("trading_date", ""),
                cycle_id=evt.get("cycle_id", ""),
                symbol=evt.get("symbol", ""),
                direction=evt.get("direction", ""),
                entry_price=float(evt.get("entry_price", 0.0)),
                scanner_rsi=float(evt.get("scanner_rsi", 0.0)),
                scanner_volume_ratio=float(evt.get("scanner_volume_ratio", 0.0)),
                scanner_score=float(evt.get("scanner_score", 0.0)),
                scanner_regime=evt.get("scanner_regime", ""),
            )
            self._traces[tid] = ct
            key = (ct.cycle_id, ct.symbol, ct.direction)
            self._key_map[key] = tid

        elif etype == "STAGE_UPDATE":
            tid = evt.get("trace_id", "")
            if tid not in self._traces:
                return
            ct = self._traces[tid]
            # Don't duplicate stages
            existing = {s.stage for s in ct.stages}
            stage = evt.get("stage", "")
            if stage in existing:
                return
            sr = StageResult(
                stage=stage,
                status=StageStatus(evt.get("status", "UNKNOWN")),
                timestamp_utc=evt.get("ts", ""),
                details=evt.get("details", {}),
                rejection_reason=evt.get("rejection_reason"),
            )
            ct.stages.append(sr)
            ct.final_outcome = evt.get("final_outcome", ct.final_outcome)

    def _write_restart_boundary(self, date_str: str) -> None:
        """Write a RESTART_BOUNDARY marker to both files."""
        ts = _now_utc()
        rec = {"event": "RESTART_BOUNDARY", "ts": ts, "trading_date": date_str}
        try:
            _append_line(_trace_file(date_str), rec)
            _append_line(_cycle_file(date_str), rec)
        except Exception:
            pass

    # ── Cycle ID management ────────────────────────────────────────────────

    def set_cycle_id(self, cycle_id: str) -> None:
        global _CURRENT_CYCLE_ID
        with _CURRENT_CYCLE_ID_LOCK:
            _CURRENT_CYCLE_ID = cycle_id
        self._ensure_loaded(_today_str())

    def get_cycle_id(self) -> str:
        with _CURRENT_CYCLE_ID_LOCK:
            cid = _CURRENT_CYCLE_ID
        if cid:
            return cid
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    # ── Lookup ─────────────────────────────────────────────────────────────

    def _get_trace(self, cycle_id: str, symbol: str, direction: str) -> Optional[CandidateTrace]:
        """Return existing trace for (cycle, symbol, direction) or None."""
        key = (cycle_id, symbol, direction)
        tid = self._key_map.get(key)
        return self._traces.get(tid) if tid else None

    # ── Stage recording ────────────────────────────────────────────────────

    def record_scanner_stage(self, sig: Any, candidate: dict) -> None:
        """
        Called from equity_scanner_ai.scan() for each accepted signal.
        sig: TradeSignal object
        candidate: stock dict from watchlist
        """
        try:
            self._record_scanner_impl(sig, candidate)
        except Exception:
            pass

    def _record_scanner_impl(self, sig: Any, candidate: dict) -> None:
        date_str  = _today_str()
        self._ensure_loaded(date_str)
        cycle_id  = self.get_cycle_id()
        symbol    = str(getattr(sig, "symbol", "UNKNOWN") or "UNKNOWN").strip()
        direction = str(
            getattr(getattr(sig, "direction", None), "value", None)
            or getattr(sig, "direction", "BUY")
            or "BUY"
        )
        entry     = float(getattr(sig, "entry_price", 0.0) or 0.0)
        regime    = str(getattr(sig, "_obs_regime", "") or "")

        with self._lock:
            existing = self._get_trace(cycle_id, symbol, direction)
            if existing is not None:
                return  # already recorded this cycle

            tid = _make_trace_id(cycle_id, symbol, direction)
            ct  = CandidateTrace(
                trace_id=tid,
                trading_date=date_str,
                cycle_id=cycle_id,
                symbol=symbol,
                direction=direction,
                entry_price=entry,
                scanner_rsi=float(candidate.get("rsi", 0.0) or 0.0),
                scanner_volume_ratio=float(candidate.get("volume_ratio", 0.0) or 0.0),
                scanner_score=float(candidate.get("score", 0.0) or 0.0),
                scanner_regime=regime,
            )
            # Add SCANNER stage as PASSED
            sr = StageResult(
                stage="SCANNER",
                status=StageStatus.PASSED,
                timestamp_utc=_now_utc(),
                details={"rsi": ct.scanner_rsi, "vol_ratio": ct.scanner_volume_ratio},
            )
            ct.stages.append(sr)
            self._traces[tid] = ct
            self._key_map[(cycle_id, symbol, direction)] = tid

        # Persist
        init_rec = {
            "event": "TRACE_INIT",
            "trace_id": tid,
            "trading_date": date_str,
            "cycle_id": cycle_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry,
            "scanner_rsi": ct.scanner_rsi,
            "scanner_volume_ratio": ct.scanner_volume_ratio,
            "scanner_score": ct.scanner_score,
            "scanner_regime": regime,
            "ts": _now_utc(),
        }
        stage_rec = {
            "event": "STAGE_UPDATE",
            "trace_id": tid,
            "stage": "SCANNER",
            "status": StageStatus.PASSED.value,
            "ts": _now_utc(),
            "details": {"rsi": ct.scanner_rsi, "vol_ratio": ct.scanner_volume_ratio},
        }
        _append_line(_trace_file(date_str), init_rec)
        _append_line(_trace_file(date_str), stage_rec)

    def record_strategy_outcomes(
        self, all_signals: List[Any], enriched_signals: List[Any]
    ) -> None:
        """
        Record STRATEGY stage outcome for each signal.
        all_signals: list of TradeSignal from scanner
        enriched_signals: subset approved by StrategyLab
        """
        try:
            self._record_stage_outcomes(
                all_signals, enriched_signals, "STRATEGY", "STRATEGY_REJECTED"
            )
        except Exception:
            pass

    def record_cre_outcomes(
        self, enriched_signals: List[Any], cre_signals: List[Any]
    ) -> None:
        """Record CRE stage outcome."""
        try:
            self._record_stage_outcomes(
                enriched_signals, cre_signals, "CRE", "CRE_QTY_ZERO"
            )
        except Exception:
            pass

    def record_risk_outcomes(
        self, cre_signals: List[Any], approved_signals: List[Any]
    ) -> None:
        """Record RISK_CONTROL stage outcome."""
        try:
            self._record_stage_outcomes(
                cre_signals, approved_signals, "RISK_CONTROL", "RR_BELOW_THRESHOLD"
            )
        except Exception:
            pass

    def record_guardian_outcome(
        self, pre_signals: List[Any], passed: bool, reason: str = ""
    ) -> None:
        """Record RISK_GUARDIAN stage: either all pass or all fail."""
        try:
            date_str  = _today_str()
            cycle_id  = self.get_cycle_id()
            status    = StageStatus.PASSED if passed else StageStatus.REJECTED
            for sig in pre_signals:
                self._record_one_stage(
                    date_str, cycle_id, sig, "RISK_GUARDIAN", status,
                    rejection_reason=reason if not passed else None,
                    final_outcome=("REJECTED_AT_RISK_GUARDIAN" if not passed else None),
                )
        except Exception:
            pass

    def record_kda_authority_gate(self, sig: Any, *, granted: bool) -> None:
        """Record whether a StrategyLab-rejected, KDA-authorized candidate was
        let through to CRE (granted) or still blocked (denied). Observability
        only — never gates or influences the decision itself.
        """
        try:
            date_str = _today_str()
            cycle_id = self.get_cycle_id()
            self._record_one_stage(
                date_str, cycle_id, sig, "KDA_AUTHORITY_GATE",
                StageStatus.PASSED if granted else StageStatus.REJECTED,
                rejection_reason=None if granted else "CONFIDENCE_BELOW_THRESHOLD",
                final_outcome=None if granted else "REJECTED_AT_KDA_AUTHORITY_GATE",
            )
        except Exception:
            pass

    def record_debate_outcome(
        self, signals_for_debate: List[Any], executed: List[dict]
    ) -> None:
        """Record DEBATE stage outcome per signal."""
        try:
            date_str  = _today_str()
            cycle_id  = self.get_cycle_id()
            exec_syms: Set[str] = {
                str(r.get("symbol", "")) for r in executed if r
            }
            for sig in signals_for_debate:
                symbol    = str(getattr(sig, "symbol", "") or "").strip()
                direction = str(
                    getattr(getattr(sig, "direction", None), "value", None)
                    or getattr(sig, "direction", "BUY")
                    or "BUY"
                )
                passed    = symbol in exec_syms
                score     = float(getattr(sig, "confidence_score", 0.0) or 0.0)
                status    = StageStatus.PASSED if passed else StageStatus.REJECTED
                outcome   = "EXECUTED" if passed else "REJECTED_AT_DEBATE"
                self._record_one_stage(
                    date_str, cycle_id, sig, "DEBATE", status,
                    details={"confidence_score": score},
                    rejection_reason=(None if passed else "CONFIDENCE_BELOW_THRESHOLD"),
                    final_outcome=outcome,
                )
        except Exception:
            pass

    def record_cycle_start(
        self, regime: str = "", vix: float = 0.0
    ) -> None:
        """Called at cycle start to record cycle metadata."""
        try:
            date_str = _today_str()
            self._ensure_loaded(date_str)
            cycle_id = self.get_cycle_id()
            ts       = _now_utc()
            with self._lock:
                if cycle_id not in self._cycles:
                    self._cycles[cycle_id] = CycleAudit(
                        cycle_id=cycle_id,
                        trading_date=date_str,
                        start_ts=ts,
                        regime=regime,
                        vix=vix,
                    )
            _append_line(_cycle_file(date_str), {
                "event": "CYCLE_START",
                "cycle_id": cycle_id,
                "trading_date": date_str,
                "ts": ts,
                "regime": regime,
                "vix": vix,
            })
        except Exception:
            pass

    def record_cycle_end(
        self,
        signals_generated: int = 0,
        strategy_passed: int = 0,
        cre_passed: int = 0,
        risk_passed: int = 0,
        guardian_passed: int = 0,
        debate_input: int = 0,
        executed: int = 0,
    ) -> None:
        """Called at cycle end to flush aggregate counts."""
        try:
            date_str = _today_str()
            cycle_id = self.get_cycle_id()
            ts       = _now_utc()
            stage_drop_map = {
                "STRATEGY": signals_generated - strategy_passed,
                "CRE":      strategy_passed  - cre_passed,
                "RISK":     cre_passed       - risk_passed,
                "GUARDIAN": risk_passed      - guardian_passed,
                "DEBATE":   debate_input     - executed,
            }
            with self._lock:
                ca = self._cycles.get(cycle_id)
                if ca:
                    ca.end_ts            = ts
                    ca.signals_generated = signals_generated
                    ca.strategy_passed   = strategy_passed
                    ca.cre_passed        = cre_passed
                    ca.risk_passed       = risk_passed
                    ca.guardian_passed   = guardian_passed
                    ca.debate_input      = debate_input
                    ca.executed          = executed
                    ca.stage_drop_map    = stage_drop_map
            _append_line(_cycle_file(date_str), {
                "event": "CYCLE_END",
                "cycle_id": cycle_id,
                "trading_date": date_str,
                "ts": ts,
                "signals_generated": signals_generated,
                "strategy_passed":   strategy_passed,
                "cre_passed":        cre_passed,
                "risk_passed":       risk_passed,
                "guardian_passed":   guardian_passed,
                "debate_input":      debate_input,
                "executed":          executed,
                "stage_drop_map":    stage_drop_map,
            })
        except Exception:
            pass

    # ── Internal helpers ───────────────────────────────────────────────────

    def _record_stage_outcomes(
        self,
        in_signals: List[Any],
        out_signals: List[Any],
        stage: str,
        default_rejection_reason: str,
    ) -> None:
        date_str  = _today_str()
        cycle_id  = self.get_cycle_id()
        out_syms: Set[str] = {
            str(getattr(s, "symbol", "") or "").strip()
            for s in out_signals
        }
        for sig in in_signals:
            symbol = str(getattr(sig, "symbol", "") or "").strip()
            passed = symbol in out_syms
            status = StageStatus.PASSED if passed else StageStatus.REJECTED
            outcome_suffix = stage.replace("_", "")
            final_outcome  = None if passed else f"REJECTED_AT_{outcome_suffix}"
            self._record_one_stage(
                date_str, cycle_id, sig, stage, status,
                rejection_reason=(default_rejection_reason if not passed else None),
                final_outcome=final_outcome,
            )

    def _record_one_stage(
        self,
        date_str: str,
        cycle_id: str,
        sig: Any,
        stage: str,
        status: StageStatus,
        details: Optional[dict] = None,
        rejection_reason: Optional[str] = None,
        final_outcome: Optional[str] = None,
    ) -> None:
        symbol    = str(getattr(sig, "symbol", "") or "").strip()
        direction = str(
            getattr(getattr(sig, "direction", None), "value", None)
            or getattr(sig, "direction", "BUY")
            or "BUY"
        )
        ts  = _now_utc()
        sr  = StageResult(
            stage=stage,
            status=status,
            timestamp_utc=ts,
            details=details or {},
            rejection_reason=rejection_reason,
        )

        tid: Optional[str] = None
        with self._lock:
            ct = self._get_trace(cycle_id, symbol, direction)
            if ct is None:
                return   # not in our trace set (e.g. options signal)
            existing_stages = {s.stage for s in ct.stages}
            if stage in existing_stages:
                return   # already recorded
            ct.stages.append(sr)
            if final_outcome:
                ct.final_outcome = final_outcome
            tid = ct.trace_id

        if tid:
            rec = {
                "event": "STAGE_UPDATE",
                "trace_id": tid,
                "stage": stage,
                "status": status.value,
                "ts": ts,
                "details": details or {},
                "rejection_reason": rejection_reason,
                "final_outcome": final_outcome,
            }
            _append_line(_trace_file(date_str), rec)

    # ── Query helpers ──────────────────────────────────────────────────────

    def get_today_traces(self) -> List[CandidateTrace]:
        """Return a snapshot of all traces for today (thread-safe copy)."""
        try:
            date_str = _today_str()
            self._ensure_loaded(date_str)
            with self._lock:
                return list(self._traces.values())
        except Exception:
            return []

    def get_today_cycles(self) -> List[CycleAudit]:
        """Return a snapshot of all cycle audits for today."""
        try:
            date_str = _today_str()
            self._ensure_loaded(date_str)
            with self._lock:
                return list(self._cycles.values())
        except Exception:
            return []

    def get_traces_for_date(self, date_str: str) -> List[CandidateTrace]:
        """Return traces for a past date (read from file)."""
        try:
            tm = TraceManager.__new__(TraceManager)
            tm._lock = threading.Lock()
            tm._traces = {}
            tm._cycles = {}
            tm._anomalies = []
            tm._key_map = {}
            tm._loaded_date = None
            tm._restart_recorded = True
            with tm._lock:
                tm._load_from_file(date_str)
            return list(tm._traces.values())
        except Exception:
            return []

    def get_terminal_stage_drop_map(self, cycle_id: str) -> Dict[str, int]:
        """Count only each trace's latest terminal rejection for reporting."""
        try:
            stage_names = {
                "RISKCONTROL": "RISK",
                "GUARDIAN": "GUARDIAN",
                "DEBATE": "DEBATE",
                "CRE": "CRE",
                "STRATEGY": "STRATEGY",
            }
            drops: Dict[str, int] = {}
            with self._lock:
                traces = [t for t in self._traces.values() if t.cycle_id == cycle_id]
                for trace in traces:
                    outcome = trace.final_outcome or ""
                    if not outcome.startswith("REJECTED_AT_"):
                        continue
                    stage = stage_names.get(outcome.removeprefix("REJECTED_AT_"))
                    if stage:
                        drops[stage] = drops.get(stage, 0) + 1
            return drops
        except Exception:
            return {}

    def get_anomalies(self) -> List[AnomalyRecord]:
        with self._lock:
            return list(self._anomalies)

    def add_anomaly(self, anomaly: AnomalyRecord) -> None:
        try:
            with self._lock:
                self._anomalies.append(anomaly)
        except Exception:
            pass


# ── Module-level singleton ──────────────────────────────────────────────────

_INSTANCE: Optional[TraceManager] = None
_INSTANCE_LOCK = threading.Lock()


def get_trace_manager() -> TraceManager:
    """Return the process-singleton TraceManager, creating it on first call."""
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = TraceManager()
    return _INSTANCE
