"""
orchestrator/scheduler_health.py
==================================
Persistent scheduler health tracker.

Records every slot success, failure, and missed cycle across container
restarts.  Acts as the single durable source of truth for:

  - last_successful_slot
  - last_failed_slot
  - missed_slots_on_restart
  - container start/stop timestamps

File: data/scheduler_health.json
Thread-safe.  Never raises — all public methods swallow exceptions.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_HEALTH_FILE = Path("data") / "scheduler_health.json"
_LOCK = threading.Lock()
_MAX_HISTORY = 200  # keep last N slot events


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class SchedulerHealth:
    """
    Persistent scheduler health tracker.

    Call record_startup() once when start_scheduler() begins.
    Call record_slot_success/failure() from _guarded_cycle() and EOD wrapper.
    """

    def __init__(self) -> None:
        self._state: Dict[str, Any] = self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def record_startup(self, container_id: Optional[str] = None) -> None:
        """Record container/scheduler start and detect missed slots since last run."""
        try:
            with _LOCK:
                prev = self._state.get("container_id")
                prev_slot = self._state.get("last_successful_slot")
                missed = self._detect_missed_slots()
                self._state.update({
                    "container_start": _now_iso(),
                    "container_id": container_id or _now_iso(),
                    "previous_container_id": prev,
                    "restart_detected": True,
                    "missed_slots_on_restart": missed,
                })
                if missed:
                    for m in missed:
                        self._append_history({
                            "slot": m, "status": "MISSED",
                            "at": _now_iso(), "reason": "container_not_running",
                        })
                self._save()
            log.info(
                "[SchedulerHealth] RUNTIME_RESTART_DETECTED  "
                "prev_container=%s  last_successful_slot=%s  missed=%s",
                prev, prev_slot, missed,
            )
        except Exception as exc:
            log.debug("[SchedulerHealth] record_startup error: %s", exc)

    def record_slot_success(self, slot: str) -> None:
        """Record a successfully completed trading/learning cycle slot."""
        try:
            with _LOCK:
                self._state["last_successful_slot"] = slot
                self._state["last_successful_at"] = _now_iso()
                self._append_history({"slot": slot, "status": "SUCCESS", "at": _now_iso()})
                self._save()
        except Exception as exc:
            log.debug("[SchedulerHealth] record_slot_success error: %s", exc)

    def record_slot_failure(self, slot: str, error: str) -> None:
        """Record a failed cycle slot with error summary."""
        try:
            with _LOCK:
                self._state["last_failed_slot"] = slot
                self._state["last_failed_at"] = _now_iso()
                self._state["last_failure_error"] = error[:500]
                self._append_history({
                    "slot": slot, "status": "FAILED",
                    "at": _now_iso(), "error": error[:200],
                })
                self._save()
        except Exception as exc:
            log.debug("[SchedulerHealth] record_slot_failure error: %s", exc)

    def record_eod_start(self) -> None:
        try:
            with _LOCK:
                self._state["last_eod_start"] = _now_iso()
                self._save()
        except Exception as exc:
            log.debug("[SchedulerHealth] record_eod_start error: %s", exc)

    def record_eod_success(self) -> None:
        try:
            with _LOCK:
                self._state["last_eod_success"] = _now_iso()
                self._append_history({"slot": "EOD", "status": "SUCCESS", "at": _now_iso()})
                self._save()
        except Exception as exc:
            log.debug("[SchedulerHealth] record_eod_success error: %s", exc)

    def record_eod_failure(self, error: str) -> None:
        try:
            with _LOCK:
                self._state["last_eod_failure"] = _now_iso()
                self._state["last_eod_error"] = error[:500]
                self._append_history({
                    "slot": "EOD", "status": "FAILED",
                    "at": _now_iso(), "error": error[:200],
                })
                self._save()
        except Exception as exc:
            log.debug("[SchedulerHealth] record_eod_failure error: %s", exc)

    def record_heartbeat(self) -> None:
        try:
            with _LOCK:
                self._state["last_heartbeat"] = _now_iso()
                self._save()
        except Exception as exc:
            log.debug("[SchedulerHealth] record_heartbeat error: %s", exc)

    def get_state(self) -> Dict[str, Any]:
        with _LOCK:
            return dict(self._state)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _detect_missed_slots(self) -> List[str]:
        """Return intraday slots that should have fired between last run and now."""
        try:
            from config import SCHEDULE
            _slots = [
                SCHEDULE.get("trade_decision",        "09:45"),
                SCHEDULE.get("mid_morning_scan",      "10:30"),
                SCHEDULE.get("mid_session_scan",      "11:30"),
                SCHEDULE.get("afternoon_scan",        "13:00"),
                SCHEDULE.get("early_afternoon_scan",  "14:00"),
                SCHEDULE.get("closing_analysis",      "15:00"),
                SCHEDULE.get("eod_learning",          "15:35"),
            ]
            now_hm   = datetime.now().strftime("%H:%M")
            last_ok  = self._state.get("last_successful_slot", "00:00")
            return [s for s in _slots if last_ok < s <= now_hm]
        except Exception:
            return []

    def _append_history(self, entry: Dict[str, Any]) -> None:
        """Append to slot_history, capped at _MAX_HISTORY entries (no lock — caller holds it)."""
        hist = self._state.setdefault("slot_history", [])
        hist.append(entry)
        if len(hist) > _MAX_HISTORY:
            self._state["slot_history"] = hist[-_MAX_HISTORY:]

    def _load(self) -> Dict[str, Any]:
        try:
            if _HEALTH_FILE.exists():
                with open(_HEALTH_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as exc:
            log.debug("[SchedulerHealth] Load failed: %s", exc)
        return {}

    def _save(self) -> None:
        try:
            _HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = str(_HEALTH_FILE) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            os.replace(tmp, _HEALTH_FILE)
        except Exception as exc:
            log.debug("[SchedulerHealth] Save failed: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────
_SINGLETON: Optional[SchedulerHealth] = None
_SINGLETON_LOCK = threading.Lock()


def get_scheduler_health() -> SchedulerHealth:
    """Return the process-wide SchedulerHealth singleton."""
    global _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            _SINGLETON = SchedulerHealth()
    return _SINGLETON
