"""
Safe scalar extraction utility.
================================
Converts pandas Series / DataFrame / numpy arrays / lists to deterministic
Python floats without raising exceptions.

Primary purpose: Defence-in-depth against yfinance ≥ 0.2.28/1.x MultiIndex
column DataFrames where ``row["Close"]`` returns a one-element Series instead
of a scalar.

The PRIMARY fix is column normalisation (droplevel) in yahoo_feed.py.
This module is the **fallback layer** that catches anything that slips through.

Usage::
    from utils.safe_scalar import safe_scalar
    price = safe_scalar(row["Close"], default=0.0, name="RELIANCE.close")

Governance: observational only — no threshold mutations, no strategy changes.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from utils.logger import get_logger

log = get_logger(__name__)

# Lazy integration with ScalarNormalizationAudit — import at call time
# to avoid any circular-import risk at module load.
def _get_audit():  # type: ignore[return]
    try:
        from utils.scalar_audit import get_scalar_audit  # noqa: PLC0415
        return get_scalar_audit()
    except Exception:
        return None


def _caller_ctx() -> tuple[str, str]:
    """
    [Audit 2] Capture the immediate external caller's file and function name.
    Returns (file_basename, function_name). Falls back to ('', '') on any error.
    Uses a lazy import of inspect to avoid top-level overhead.
    """
    try:
        import inspect as _inspect
        # stack[0]=_caller_ctx, stack[1]=safe_scalar, stack[2]=actual caller
        frame = _inspect.stack()[2]
        _file = frame.filename.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]  # basename only
        _func = frame.function
        return _file, _func
    except Exception:
        return "", ""


def safe_scalar(
    value: Any,
    default: Optional[float] = 0.0,
    name: str = "",
) -> float:
    """
    Safely coerce any numeric container to a Python ``float``.

    Handles:
    * Python int / float            → pass through
    * numpy scalar                  → ``float()``
    * pandas Series (one element)   → ``.iloc[-1]``
    * pandas DataFrame              → ``.iloc[-1, -1]``
    * list / tuple                  → ``[-1]``
    * anything else                 → ``float()`` fallback

    Registers coercion events with ScalarNormalizationAudit for forensic
    observability.  Emits [ScalarNormalizationFailure] when non-trivial
    coercion is required.  Never raises — returns *default* on any failure.
    """
    _def = default if default is not None else 0.0

    if value is None:
        return _def

    # ── Fast-path: plain Python scalars ──────────────────────────────────────
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else _def

    # ── numpy scalars ─────────────────────────────────────────────────────────
    try:
        import numpy as np
        if isinstance(value, np.generic):
            f = float(value)
            return f if math.isfinite(f) else _def
    except ImportError:
        pass

    # ── pandas types ──────────────────────────────────────────────────────────
    try:
        import pandas as pd
        import numpy as np

        if isinstance(value, pd.Series):
            _audit = _get_audit()
            _shape = f"shape={value.shape}"
            _file, _func = _caller_ctx()
            if value.empty:
                _audit and _audit.record_coercion(
                    name, "Series", fallback_used=True,
                    file_ctx=_file, method_ctx=_func, shape_info=_shape,
                )
                return _def
            log.debug("[SafeScalarFallback] %s: Series→iloc[-1] (len=%d)", name, len(value))
            _audit and _audit.record_coercion(
                name, "Series", fallback_used=False,
                file_ctx=_file, method_ctx=_func, shape_info=_shape,
            )
            return safe_scalar(value.iloc[-1], _def, "")

        if isinstance(value, pd.DataFrame):
            _audit = _get_audit()
            _shape = f"shape={value.shape}"
            _file, _func = _caller_ctx()
            if value.empty:
                _audit and _audit.record_coercion(
                    name, "DataFrame", fallback_used=True,
                    file_ctx=_file, method_ctx=_func, shape_info=_shape,
                )
                return _def
            log.debug("[SafeScalarFallback] %s: DataFrame→iloc[-1,-1]", name)
            _audit and _audit.record_coercion(
                name, "DataFrame", fallback_used=False,
                file_ctx=_file, method_ctx=_func, shape_info=_shape,
            )
            return safe_scalar(value.iloc[-1, -1], _def, "")

        if isinstance(value, np.ndarray):
            _audit = _get_audit()
            _shape = f"shape={value.shape}"
            _file, _func = _caller_ctx()
            if value.size == 0:
                _audit and _audit.record_coercion(
                    name, "ndarray", fallback_used=True,
                    file_ctx=_file, method_ctx=_func, shape_info=_shape,
                )
                return _def
            log.debug("[SafeScalarFallback] %s: ndarray→flat[-1]", name)
            _audit and _audit.record_coercion(
                name, "ndarray", fallback_used=False,
                file_ctx=_file, method_ctx=_func, shape_info=_shape,
            )
            return float(value.flat[-1])

    except ImportError:
        pass
    except Exception as exc:
        _file, _func = _caller_ctx()
        log.debug("[SafeScalarFallback] %s extraction failed (type=%s): %s",
                  name or "?", type(value).__name__, exc)
        _get_audit() and _get_audit().record_coercion(
            name, type(value).__name__, fallback_used=True,
            file_ctx=_file, method_ctx=_func, exc_type=type(exc).__name__,
        )
        return _def

    # ── list / tuple ──────────────────────────────────────────────────────────
    if isinstance(value, (list, tuple)):
        _audit = _get_audit()
        _file, _func = _caller_ctx()
        if not value:
            _audit and _audit.record_coercion(
                name, "list", fallback_used=True,
                file_ctx=_file, method_ctx=_func,
            )
            return _def
        log.debug("[SafeScalarFallback] %s: list→[-1]", name)
        _audit and _audit.record_coercion(
            name, "list", fallback_used=False,
            file_ctx=_file, method_ctx=_func,
        )
        return safe_scalar(value[-1], _def, "")

    # ── Last resort: direct float() ───────────────────────────────────────────
    try:
        f = float(value)
        return f if math.isfinite(f) else _def
    except (TypeError, ValueError) as exc:
        _file, _func = _caller_ctx()
        log.debug("[SafeScalarFallback] %s: float() failed (type=%s): %s",
                  name or "?", type(value).__name__, exc)
        _get_audit() and _get_audit().record_coercion(
            name, type(value).__name__, fallback_used=True,
            file_ctx=_file, method_ctx=_func, exc_type=type(exc).__name__,
        )
        return _def
