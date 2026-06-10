"""
FORENSIC REFINEMENT — Priority 7: TelemetryCoverageAudit
=========================================================

Meta-audit: probes all six Forensic Refinement audit modules to confirm they
are receiving data.  If any module has session_cycles == 0 (or equivalent zero
activity), it is reported as "dark" — meaning its code path is unreachable or
its wiring was silently skipped.

Also calls emit_eod_report() on every registered audit module so the EOD
retrospective only needs ONE call to this module.

Emits:
  [TelemetryCoverageAudit]  — per probe: coverage summary across all modules
  [TelemetryCoverageDark]   — WARNING for each module with zero activity
  Individual audit EOD reports ([FallbackSourceReport], [FilterFunnelReport],
    [RankingInstabilityReport], [LifecycleTransitionReport],
    [SimulationCalibrationReport]) fired from within this module.

Registered audit modules:
  1. ScalarNormalizationAudit  — utils.scalar_audit
  2. FallbackContaminationAudit— data_feeds.fallback_contamination_audit
  3. FilterFunnelAudit         — opportunity_engine.filter_funnel_audit
  4. RankingInstabilityAudit   — opportunity_engine.ranking_instability_audit
  5. LifecycleTransitionAudit  — opportunity_engine.lifecycle_transition_audit
  6. SimulationCalibrationAudit— market_simulation.simulation_calibration_audit
  7. IntegrityPersistenceAudit — opportunity_engine.integrity_persistence_audit

Thread-safe; auto-resets at midnight UTC.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── Module-level singleton ────────────────────────────────────────────────────
_AUDIT_LOCK:     threading.Lock                    = threading.Lock()
_AUDIT_INSTANCE: "Optional[TelemetryCoverageAudit]" = None


def get_telemetry_coverage_audit() -> "TelemetryCoverageAudit":
    """Return the session-scoped singleton (thread-safe, lazily created)."""
    global _AUDIT_INSTANCE
    if _AUDIT_INSTANCE is None:
        with _AUDIT_LOCK:
            if _AUDIT_INSTANCE is None:
                _AUDIT_INSTANCE = TelemetryCoverageAudit()
    return _AUDIT_INSTANCE


# ── Registry: (display_name, import_path, getter_fn_name, activity_fn) ───────
# activity_fn(stats_dict) → int activity count (0 means dark)
_REGISTRY: List[Tuple[str, str, str, Callable[[Dict[str, Any]], int]]] = [
    (
        "ScalarNormalizationAudit",
        "utils.scalar_audit",
        "get_scalar_audit",
        lambda s: (s.get("total_clean", 0) or 0) + (s.get("total_coercions", 0) or 0),
    ),
    (
        "FallbackContaminationAudit",
        "data_feeds.fallback_contamination_audit",
        "get_fallback_audit",
        lambda s: s.get("total_events", 0) or 0,
    ),
    (
        "FilterFunnelAudit",
        "opportunity_engine.filter_funnel_audit",
        "get_filter_funnel_audit",
        lambda s: s.get("session_cycles", 0) or 0,
    ),
    (
        "RankingInstabilityAudit",
        "opportunity_engine.ranking_instability_audit",
        "get_ranking_audit",
        lambda s: s.get("session_cycles", 0) or 0,
    ),
    (
        "LifecycleTransitionAudit",
        "opportunity_engine.lifecycle_transition_audit",
        "get_lifecycle_audit",
        lambda s: s.get("session_cycles", 0) or 0,
    ),
    (
        "SimulationCalibrationAudit",
        "market_simulation.simulation_calibration_audit",
        "get_simulation_audit",
        lambda s: s.get("session_cycles", 0) or 0,
    ),
    (
        "IntegrityPersistenceAudit",
        "opportunity_engine.integrity_persistence_audit",
        "get_integrity_audit",
        lambda s: s.get("session_attempted", 0) or 0,
    ),
]


class TelemetryCoverageAudit:
    """
    Meta-audit singleton that probes all Forensic Refinement audit modules.

    Usage (from EOD learning):
        from control_tower.telemetry_coverage_audit import get_telemetry_coverage_audit
        get_telemetry_coverage_audit().emit_coverage_report()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_day = datetime.now(timezone.utc).date()

    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._reset_day:
            self._reset_day = today

    # ── Core: probe all registered modules ────────────────────────────────────
    def _probe_all(self) -> List[Dict[str, Any]]:
        """
        Probe each registered audit module.

        Returns list of result dicts:
          {name, active, activity_count, error}
        """
        results = []
        for name, module_path, getter_name, activity_fn in _REGISTRY:
            entry: Dict[str, Any] = {
                "name":           name,
                "active":         False,
                "activity_count": 0,
                "error":          None,
            }
            try:
                import importlib
                mod    = importlib.import_module(module_path)
                getter = getattr(mod, getter_name)
                inst   = getter()
                stats  = inst.get_stats()
                count  = activity_fn(stats)
                entry["active"]         = count > 0
                entry["activity_count"] = count
            except Exception as exc:
                entry["error"] = str(exc)
            results.append(entry)
        return results

    # ── Emit EOD reports on all registered modules ────────────────────────────
    def emit_all_eod_reports(self) -> None:
        """
        Call emit_eod_report() on every registered audit module that has it.
        Silent on any failure.
        """
        for name, module_path, getter_name, _ in _REGISTRY:
            try:
                import importlib
                mod    = importlib.import_module(module_path)
                getter = getattr(mod, getter_name)
                inst   = getter()
                if hasattr(inst, "emit_eod_report"):
                    inst.emit_eod_report()
            except Exception as exc:
                log.debug("[TelemetryCoverageAudit] EOD report failed for %s: %s", name, exc)

    # ── Public: probe + emit coverage summary ─────────────────────────────────
    def emit_coverage_report(self) -> None:
        """
        Probe all audit modules and emit:
          [TelemetryCoverageAudit] — summary line
          [TelemetryCoverageDark]  — one WARNING per dark (zero-activity) module
        Then calls emit_eod_report() on every module.
        """
        with self._lock:
            self._maybe_reset()

        results    = self._probe_all()
        total      = len(results)
        active     = [r for r in results if r["active"]]
        dark       = [r for r in results if not r["active"] and r["error"] is None]
        errored    = [r for r in results if r["error"] is not None]

        active_names = ",".join(r["name"] for r in active) or "none"
        dark_names   = ",".join(r["name"] for r in dark) or "none"
        err_names    = ",".join(r["name"] for r in errored) or "none"

        # Coverage summary
        coverage_pct = round(len(active) / total * 100) if total > 0 else 0

        log.info(
            "[TelemetryCoverageAudit] modules=%d active=%d dark=%d errored=%d"
            " coverage=%d%% | active=[%s] dark=[%s] errored=[%s]",
            total,
            len(active),
            len(dark),
            len(errored),
            coverage_pct,
            active_names,
            dark_names,
            err_names,
        )

        # Warn about each dark module (zero activity — code path unreachable)
        for r in dark:
            log.warning(
                "[TelemetryCoverageDark] %s has ZERO activity this session —"
                " its wiring may be broken or its code path was never reached.",
                r["name"],
            )

        # Emit each module's EOD summary report
        self.emit_all_eod_reports()

    def get_stats(self) -> dict:
        """Return a snapshot dict (for unit tests and smoke checks)."""
        results = self._probe_all()
        return {
            "total":   len(results),
            "active":  sum(1 for r in results if r["active"]),
            "dark":    sum(1 for r in results if not r["active"] and not r["error"]),
            "errored": sum(1 for r in results if r["error"]),
            "details": results,
        }
