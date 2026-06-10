"""
Scalar Normalization Audit
===========================
Session-scoped (in-memory) tracker for scalar coercion quality across the
entire pipeline.

Problem it detects:
    ``float() argument must be a string or real number, not 'Series'``
    This error fires when a pandas Series reaches a bare float() call.
    Without this tracker the failure is caught by the enclosing try/except and
    silently drops the symbol — it is NEVER visible in normal logs.

Emitted log tags:
    [ScalarNormalizationFailure]   per event, when Series/DataFrame/ndarray
                                   reaches a point that expected a scalar.
    [SafeScalarCoverageAudit]      periodic or on-demand summary of coercion
                                   coverage (rate, top symbols, top columns).
    [ScalarCoverageReport]         EOD or explicit call summary.

Governance: strictly observational.
    - Never blocks execution.
    - Never modifies thresholds or strategy logic.
    - All writes are to log only; no shared mutable state affects trading.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from typing import Dict, Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)


class ScalarNormalizationAudit:
    """
    Thread-safe, session-scoped tracker for safe_scalar coercion events.

    Auto-resets at date rollover (midnight).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_date: date = date.today()
        self._reset()

    # ── Internal lifecycle ────────────────────────────────────────────────────

    def _reset(self) -> None:
        self._total_clean: int = 0          # inputs that were already plain scalars
        self._total_coercions: int = 0      # inputs that required Series/DF/array coercion
        self._unresolved: int = 0           # coercions that fell back to default (bad data)
        self._by_symbol: Dict[str, int] = defaultdict(int)
        self._by_column: Dict[str, int] = defaultdict(int)
        self._by_context: Dict[str, int] = defaultdict(int)
        # [Audit 2] extended coverage fields
        self._by_file: Dict[str, int] = defaultdict(int)
        self._by_method: Dict[str, int] = defaultdict(int)
        self._by_exc_type: Dict[str, int] = defaultdict(int)
        self._by_shape: Dict[str, int] = defaultdict(int)

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._reset_date:
            with self._lock:
                if today != self._reset_date:
                    self._reset_date = today
                    self._reset()

    # ── Public API ────────────────────────────────────────────────────────────

    def record_clean(self) -> None:
        """Input was already a plain Python scalar — no coercion needed."""
        self._ensure_today()
        with self._lock:
            self._total_clean += 1

    def record_coercion(
        self,
        name: str,
        type_name: str,
        fallback_used: bool = False,
        context: str = "",
        file_ctx: str = "",
        method_ctx: str = "",
        shape_info: str = "",
        exc_type: str = "",
    ) -> None:
        """
        Called when safe_scalar() had to coerce a non-scalar value.

        Args:
            name:         'symbol.column' label e.g. 'RELIANCE.close'
            type_name:    type(value).__name__ — 'Series', 'DataFrame', etc.
            fallback_used: True when coercion failed and the default was returned
            context:      optional free-text calling context
            file_ctx:     [Audit 2] source file path that triggered coercion
            method_ctx:   [Audit 2] function/method name that triggered coercion
            shape_info:   [Audit 2] shape of offending Series/DataFrame e.g. 'shape=(14,)'
            exc_type:     [Audit 2] exception class name if coercion raised
        """
        self._ensure_today()
        with self._lock:
            self._total_coercions += 1
            if fallback_used:
                self._unresolved += 1

            # Parse symbol.column from name
            if "." in name:
                sym, col = name.split(".", 1)
            else:
                sym, col = (name or "UNKNOWN"), "UNKNOWN"

            self._by_symbol[sym.upper()] += 1
            self._by_column[col] += 1
            if context:
                self._by_context[context] += 1
            if file_ctx:
                self._by_file[file_ctx] += 1
            if method_ctx:
                self._by_method[method_ctx] += 1
            if shape_info:
                self._by_shape[shape_info] += 1
            if exc_type:
                self._by_exc_type[exc_type] += 1

        # Emit per-event forensic log at INFO so it appears in container logs
        log.info(
            "[ScalarNormalizationFailure] name=%s type=%s fallback=%s"
            " file=%s method=%s shape=%s exc_type=%s context=%s",
            name or "?",
            type_name,
            fallback_used,
            file_ctx or "N/A",
            method_ctx or "N/A",
            shape_info or "N/A",
            exc_type or "N/A",
            context or "N/A",
        )

    # ── Audit emission ────────────────────────────────────────────────────────

    def emit_coverage_audit(self) -> None:
        """Emit [SafeScalarCoverageAudit] summary to logs (call after each scan)."""
        self._ensure_today()
        with self._lock:
            total       = self._total_clean + self._total_coercions
            coerce_rate = (self._total_coercions / total * 100.0) if total > 0 else 0.0
            unresolve_rate = (
                self._unresolved / self._total_coercions * 100.0
            ) if self._total_coercions > 0 else 0.0
            top_symbols  = sorted(self._by_symbol.items(), key=lambda x: -x[1])[:5]
            top_columns  = sorted(self._by_column.items(), key=lambda x: -x[1])[:5]
            top_contexts = sorted(self._by_context.items(), key=lambda x: -x[1])[:3]
            # [Audit 2] extended fields
            top_files    = sorted(self._by_file.items(),   key=lambda x: -x[1])[:3]
            top_methods  = sorted(self._by_method.items(), key=lambda x: -x[1])[:3]
            top_exc      = sorted(self._by_exc_type.items(), key=lambda x: -x[1])[:3]

        log.info(
            "[SafeScalarCoverageAudit] total=%d clean=%d coercions=%d"
            " coerce_rate=%.1f%% unresolved=%d unresolved_rate=%.1f%%"
            " top_symbols=%s top_columns=%s top_contexts=%s"
            " top_files=%s top_methods=%s top_exc_types=%s",
            total,
            self._total_clean,
            self._total_coercions,
            coerce_rate,
            self._unresolved,
            unresolve_rate,
            top_symbols,
            top_columns,
            top_contexts,
            top_files,
            top_methods,
            top_exc,
        )

    def emit_eod_report(self) -> None:
        """Emit [ScalarCoverageReport] EOD summary."""
        self._ensure_today()
        with self._lock:
            total      = self._total_clean + self._total_coercions
            corruption = self._unresolved

        log.info(
            "[ScalarCoverageReport] total_scalar_coercions=%d"
            " total_clean=%d unresolved=%d"
            " corruption_rate=%.2f%% symbols_affected=%d columns_affected=%d",
            self._total_coercions,
            self._total_clean,
            corruption,
            (corruption / max(total, 1)) * 100.0,
            len(self._by_symbol),
            len(self._by_column),
        )

    def get_stats(self) -> dict:
        """Return current stats dict (for programmatic access / Telegram)."""
        self._ensure_today()
        with self._lock:
            return {
                "total_clean":     self._total_clean,
                "total_coercions": self._total_coercions,
                "unresolved":      self._unresolved,
                "top_symbols": dict(
                    sorted(self._by_symbol.items(), key=lambda x: -x[1])[:10]
                ),
                "top_columns": dict(
                    sorted(self._by_column.items(), key=lambda x: -x[1])[:10]
                ),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
_INSTANCE: Optional[ScalarNormalizationAudit] = None
_INSTANCE_LOCK = threading.Lock()


def get_scalar_audit() -> ScalarNormalizationAudit:
    """Thread-safe singleton accessor."""
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = ScalarNormalizationAudit()
    return _INSTANCE
