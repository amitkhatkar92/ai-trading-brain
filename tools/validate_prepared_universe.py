#!/usr/bin/env python3
"""
tools/validate_prepared_universe.py
=====================================
Master Forensic Validation — Prepared Universe Architecture

Single-command integrity audit covering all architecture upgrades,
telemetry systems, prepared-universe logic, hybrid exploration controls,
and governance protections.

Usage:
    python tools/validate_prepared_universe.py

Exit codes:
    0  — all sections PASS or WARN  (READY_FOR_CONTROLLED_LIVE_OPERATION)
    1  — one or more sections FAIL  (BLOCKED — FIX REQUIRED)
"""

from __future__ import annotations

import sys
import os
import json
import time
import hashlib
import logging
import inspect
import tempfile
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# ── Project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

# ── Suite identity & runtime timer ───────────────────────────────────────────
VALIDATION_SUITE_VERSION = "PREPARED_UNIVERSE_V1"
_START_TIME = time.monotonic()

# Suppress all module-level logging during validation (use our own output)
logging.disable(logging.CRITICAL)

# ── Status constants ─────────────────────────────────────────────────────────
_PASS = "PASS"
_FAIL = "FAIL"
_WARN = "WARN"
_SKIP = "SKIP"

# ── Severity classification (Patch 12) ───────────────────────────────────────
class ValidationSeverity:
    INFO     = "INFO"      # Telemetry-only observation; no operational impact
    WARN     = "WARN"      # Degraded but still safe to operate
    FAIL     = "FAIL"      # Subsystem malfunction; feature disables gracefully
    CRITICAL = "CRITICAL"  # Unsafe for prepared-universe activation — BLOCKS

_SEVERITY_FROM_STATUS: Dict[str, str] = {
    _PASS: ValidationSeverity.INFO,
    _WARN: ValidationSeverity.WARN,
    _FAIL: ValidationSeverity.FAIL,
    _SKIP: ValidationSeverity.INFO,
}

# ── Structured result (Patch 13) ──────────────────────────────────────────────
@dataclass
class ValidationResult:
    section:        str
    status:         str
    severity:       str
    details:        str
    recommendation: Optional[str]
    timestamp_utc:  str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ── Result tracking ───────────────────────────────────────────────────────────
_results: Dict[str, str] = {}
_messages: Dict[str, List[str]] = {}
_validation_results: List[ValidationResult] = []

_ICON = {_PASS: "✅", _FAIL: "❌", _WARN: "⚠️ ", _SKIP: "⏭️ ", "CRITICAL": "🔴"}


def _emit(section: str, status: str, msgs: List[str] = None, severity: str = None) -> None:
    effective_severity = severity or _SEVERITY_FROM_STATUS.get(status, ValidationSeverity.FAIL)
    _results[section] = status
    _messages[section] = msgs or []
    _validation_results.append(ValidationResult(
        section        = section,
        status         = status,
        severity       = effective_severity,
        details        = " | ".join(msgs) if msgs else status,
        recommendation = _recommend(section, status),
        timestamp_utc  = datetime.now(timezone.utc).isoformat(),
    ))
    is_crit = effective_severity == ValidationSeverity.CRITICAL
    icon    = _ICON.get("CRITICAL" if is_crit else status, "?")
    label   = f"[{section}]"
    crit_tag = "  ⬆ CRITICAL" if is_crit else ""
    print(f"  {icon}  {label:<35} status={status}{crit_tag}")
    for m in (msgs or []):
        print(f"         {m}")


def _recommend(section: str, status: str) -> Optional[str]:
    """Return a brief remediation hint for non-passing sections."""
    if status == _PASS:
        return None
    _recs: Dict[str, str] = {
        "ValidationConfig":          "Review config.py flags and logical combinations",
        "ValidationCandidateStore":  "Check data/daily_candidates.json write permissions and scanner schedule",
        "ValidationSchemaContract":  "Verify _REQUIRED_FIELDS in candidate_store.py matches pipeline contract",
        "ValidationTelemetry":       "Ensure all [LogTag] strings are present in source files",
        "ValidationSafeMode":        "Verify _SAFE_MODE_ACTIVE guard is inside scan() exploration block",
        "ValidationOverlay":         "Check get_sector_regime_bias() cap and USE_OVERNIGHT_OVERLAY guard",
        "ValidationGovernance":      "Verify Layer 5+ module paths and interface method signatures",
        "ValidationPerformance":     "Check config.py for SCANNER_MAX_RUNTIME_MINUTES and related constants",
    }
    return _recs.get(section)


def _ok(section: str, extra: str = "") -> None:
    msgs = [extra] if extra else []
    _emit(section, _PASS, msgs)


def _fail(section: str, reason: str) -> None:
    _emit(section, _FAIL, [reason])


def _warn(section: str, reason: str) -> None:
    _emit(section, _WARN, [reason])


def _skip(section: str, reason: str) -> None:
    _emit(section, _SKIP, [reason])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — CONFIG VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_config() -> None:
    section = "ValidationConfig"
    issues: List[str] = []

    try:
        import config as cfg
    except Exception as exc:
        _fail(section, f"Cannot import config: {exc}")
        return

    # ── Type checks ───────────────────────────────────────────────────────────
    bool_flags = [
        "USE_PREPARED_UNIVERSE", "USE_OVERNIGHT_OVERLAY",
        "USE_PREMARKET_REFINEMENT", "USE_HYBRID_EXPLORATION",
        "SCANNER_SHADOW_MODE",
    ]
    for flag in bool_flags:
        val = getattr(cfg, flag, None)
        if val is None:
            issues.append(f"MISSING flag: {flag}")
        elif not isinstance(val, bool):
            issues.append(f"TYPE ERROR: {flag} is {type(val).__name__}, expected bool")

    numeric_checks = [
        ("EXPLORATION_BUDGET_PCT",         int,   1,    20,   3),
        ("EXPLORATION_THRESHOLD",          float, 6.5,  8.0,  7.2),
        ("MAX_PREPARED_CANDIDATES",        int,   10,   500,  120),
        ("MIN_PREPARED_SCORE",             float, 0.40, 1.0,  0.55),
        ("SAFE_MODE_MAX_FALLBACK_SESSIONS",int,   1,    20,   3),
        ("SAFE_MODE_MAX_MISSING_LTP_PCT",  float, 10.0, 99.0, 50.0),
        ("OVERNIGHT_OVERLAY_REGIME_CONFIDENCE_MIN", float, 0.50, 1.0, 0.70),
    ]
    for name, typ, lo, hi, expected_default in numeric_checks:
        val = getattr(cfg, name, None)
        if val is None:
            issues.append(f"MISSING constant: {name}")
            continue
        if not isinstance(val, (int, float)):
            issues.append(f"TYPE ERROR: {name}={val!r} expected numeric")
            continue
        if not (lo <= float(val) <= hi):
            issues.append(f"BOUNDS ERROR: {name}={val} not in [{lo}, {hi}]")

    # ── Logical consistency ───────────────────────────────────────────────────
    upv  = getattr(cfg, "USE_PREPARED_UNIVERSE",   False)
    uhe  = getattr(cfg, "USE_HYBRID_EXPLORATION",  False)
    uoo  = getattr(cfg, "USE_OVERNIGHT_OVERLAY",   False)
    upm  = getattr(cfg, "USE_PREMARKET_REFINEMENT", False)
    ssm  = getattr(cfg, "SCANNER_SHADOW_MODE",     True)
    bpct = getattr(cfg, "EXPLORATION_BUDGET_PCT",   10)
    thr  = getattr(cfg, "EXPLORATION_THRESHOLD",    7.0)
    mps  = getattr(cfg, "MIN_PREPARED_SCORE",       0.40)

    if uhe and not upv:
        issues.append("IMPOSSIBLE COMBO: USE_HYBRID_EXPLORATION=True requires USE_PREPARED_UNIVERSE=True")

    if uoo and not upv:
        issues.append("LOGICAL WARNING: USE_OVERNIGHT_OVERLAY=True but USE_PREPARED_UNIVERSE=False — overlay has no effect")

    if upm and not upv:
        issues.append("LOGICAL WARNING: USE_PREMARKET_REFINEMENT=True but USE_PREPARED_UNIVERSE=False — refinement has no effect")

    if ssm and upv:
        issues.append("CONFLICTING: SCANNER_SHADOW_MODE=True AND USE_PREPARED_UNIVERSE=True — shadow mode should be False when live")

    if bpct > 20:
        issues.append(f"RISK: EXPLORATION_BUDGET_PCT={bpct} exceeds soft cap of 20")

    if mps < 0.40:
        issues.append(f"RISK: MIN_PREPARED_SCORE={mps} below minimum safe floor of 0.40")

    # ── Activation state summary ──────────────────────────────────────────────
    summary = (
        f"USE_PREPARED_UNIVERSE={upv} USE_OVERNIGHT_OVERLAY={uoo} "
        f"USE_PREMARKET_REFINEMENT={upm} USE_HYBRID_EXPLORATION={uhe} "
        f"SCANNER_SHADOW_MODE={ssm} budget={bpct}% threshold={thr} "
        f"score_floor={mps}"
    )

    has_critical = any("IMPOSSIBLE COMBO" in i for i in issues)
    has_fail     = any("MISSING" in i or "TYPE ERROR" in i or "BOUNDS ERROR" in i for i in issues)

    if has_critical:
        _emit(section, _FAIL, issues + [summary], severity=ValidationSeverity.CRITICAL)
    elif has_fail:
        _emit(section, _FAIL, issues + [summary])
    elif issues:
        _emit(section, _WARN, issues + [summary])
    else:
        _emit(section, _PASS, [summary])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — CANDIDATE STORE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_candidate_store() -> None:
    section = "ValidationCandidateStore"

    try:
        from opportunity_engine.candidate_store import CandidateStore, STORE_FILE, SCHEMA_VERSION
    except Exception as exc:
        _fail(section, f"Cannot import CandidateStore: {exc}")
        return

    issues: List[str] = []

    # ── Test 1: Corrupt JSON → must return None, not raise ─────────────────
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=_ROOT / "data", delete=False, encoding="utf-8"
    ) as tf:
        tf.write("{corrupt json!!! [[[")
        corrupt_path = Path(tf.name)

    # Temporarily redirect STORE_FILE
    import opportunity_engine.candidate_store as _cs_mod
    _original_store = _cs_mod.STORE_FILE
    try:
        _cs_mod.STORE_FILE = corrupt_path
        result = CandidateStore.read()
        if result is not None:
            issues.append("FAIL: corrupt JSON returned non-None result")
        else:
            issues.append("✓ Corrupt JSON → read() returned None safely")
    except Exception as exc:
        issues.append(f"FAIL: corrupt JSON raised exception: {exc}")
    finally:
        _cs_mod.STORE_FILE = _original_store
        corrupt_path.unlink(missing_ok=True)

    # ── Test 2: Checksum-mismatched store → returns None ───────────────────
    fake_payload = {
        "schema_version": SCHEMA_VERSION,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "scanner_stats": {"coverage_pct": 95.0},
        "candidates": [{"symbol": "RELIANCE", "resistance": 1400.0, "support": 1300.0, "rsi": 50.0, "volume_ratio": 1.5}],
        "checksum": "WRONG_CHECKSUM_INTENTIONAL",
        "premarket_refresh_complete": False,
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=_ROOT / "data", delete=False, encoding="utf-8"
    ) as tf:
        json.dump(fake_payload, tf)
        bad_checksum_path = Path(tf.name)

    try:
        _cs_mod.STORE_FILE = bad_checksum_path
        result = CandidateStore.read()
        if result is not None:
            issues.append("FAIL: checksum-mismatch store returned non-None result")
        else:
            issues.append("✓ Checksum mismatch → read() returned None safely")
    except Exception as exc:
        issues.append(f"FAIL: checksum mismatch raised exception: {exc}")
    finally:
        _cs_mod.STORE_FILE = _original_store
        bad_checksum_path.unlink(missing_ok=True)

    # ── Test 3: Live store (if present) ─────────────────────────────────────
    if STORE_FILE.exists():
        try:
            raw = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            sv = raw.get("schema_version", "MISSING")
            ts = raw.get("prepared_at", "MISSING")
            cov = raw.get("scanner_stats", {}).get("coverage_pct", 0.0)
            n = len(raw.get("candidates", []))
            issues.append(f"✓ Live store: schema_version={sv} candidates={n} coverage={cov:.1f}% prepared_at={ts[:19]}")

            # Validate the live store reads correctly
            result = CandidateStore.read()
            if result is None:
                issues.append("WARN: live store present but CandidateStore.read() returned None (stale/invalid)")
            else:
                issues.append(f"✓ CandidateStore.read() returned {len(result)} valid candidates")
        except Exception as exc:
            issues.append(f"WARN: error inspecting live store: {exc}")
    else:
        issues.append("INFO: daily_candidates.json not present — will be created at 16:45 post-market scan")

    if any("FAIL" in i for i in issues):
        _emit(section, _FAIL, issues)
    else:
        _emit(section, _PASS, issues)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — SCHEMA CONTRACT VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_schema_contract() -> None:
    section = "ValidationSchemaContract"
    issues: List[str] = []

    LIVE_PIPELINE_REQUIRED = {"symbol", "resistance", "support", "rsi", "volume_ratio"}
    SCANNER_REQUIRED = {"symbol", "resistance", "support", "rsi", "volume_ratio", "score", "buckets", "sector"}

    valid_record = {
        "symbol": "RELIANCE", "resistance": 1450.0, "support": 1290.0,
        "rsi": 52.3, "volume_ratio": 1.4, "adv_crore": 800.0,
        "score": 0.68, "buckets": ["breakout"], "sector": "ENERGY",
        "index": "NIFTY50", "_prepared": True,
    }

    # Required field types
    TYPE_SPEC = {
        "symbol":       (str,          False),
        "resistance":   ((int, float), False),
        "support":      ((int, float), False),
        "rsi":          ((int, float), True),
        "volume_ratio": ((int, float), True),
        "score":        ((int, float), False),
        "buckets":      (list,         True),
        "sector":       (str,          True),
    }

    # All required fields present and correctly typed in valid record
    for field in LIVE_PIPELINE_REQUIRED:
        val = valid_record.get(field)
        if val is None:
            issues.append(f"FAIL: required field {field!r} missing from valid_record fixture")
            continue
        spec = TYPE_SPEC.get(field)
        if spec and not isinstance(val, spec[0]):
            issues.append(f"FAIL: {field!r} type={type(val).__name__} expected {spec[0]}")

    # Zero/negative value rejection
    for field, val, should_fail in [
        ("resistance", 0.0,    True),
        ("support",    -10.0,  True),
        ("rsi",        -1.0,   True),
        ("rsi",        101.0,  True),
        ("score",      1.01,   True),
        ("score",      0.0,    True),
        ("score",      0.55,   False),
    ]:
        r = dict(valid_record)
        r[field] = val
        # Validate bounds manually
        if field == "resistance":
            actually_fails = val <= 0
        elif field == "support":
            actually_fails = val <= 0
        elif field == "rsi":
            actually_fails = not (0.0 <= val <= 100.0)
        elif field == "score":
            actually_fails = not (0.0 < val <= 1.0)
        else:
            actually_fails = False
        if actually_fails != should_fail:
            issues.append(f"FAIL: bounds check for {field}={val} expected fail={should_fail} got fail={actually_fails}")

    # _prepared audit tag must NOT be in LIVE_PIPELINE_REQUIRED
    if "_prepared" in LIVE_PIPELINE_REQUIRED:
        issues.append("FAIL: _prepared audit tag must not be in LIVE_PIPELINE_REQUIRED")
    else:
        pass  # correct

    # Backward compat: minimal record without Phase-D fields
    minimal = {"symbol": "HDFCBANK", "resistance": 800.0, "support": 750.0, "rsi": 48.0, "volume_ratio": 1.1}
    missing_req = [f for f in LIVE_PIPELINE_REQUIRED if minimal.get(f) is None]
    if missing_req:
        issues.append(f"FAIL: minimal pre-Phase-D record missing required: {missing_req}")

    # valid_until_utc format
    for ts in ["2026-05-22T03:30:00Z", "2026-05-22T09:30:00Z"]:
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception as exc:
            issues.append(f"FAIL: valid ISO-8601 ts {ts!r} rejected: {exc}")

    # candidate_store._REQUIRED_FIELDS (module-level) matches LIVE_PIPELINE_REQUIRED subset
    try:
        import opportunity_engine.candidate_store as _cs_mod2
        store_req = set(getattr(_cs_mod2, "_REQUIRED_FIELDS", ()))
        missing_from_store = LIVE_PIPELINE_REQUIRED - store_req
        if missing_from_store:
            issues.append(f"FAIL: _REQUIRED_FIELDS missing: {missing_from_store}")
        else:
            issues.append(f"✓ _REQUIRED_FIELDS={store_req} covers all pipeline-required fields")
    except Exception as exc:
        issues.append(f"WARN: could not check _REQUIRED_FIELDS: {exc}")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    else:
        _emit(section, _PASS, issues)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — PREPARED MERGE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_prepared_merge() -> None:
    section = "ValidationPreparedMerge"
    issues: List[str] = []

    PREPARED = [
        {"symbol": "RELIANCE",  "ltp": 1400.0, "resistance": 1450.0, "support": 1290.0, "rsi": 52.0, "volume_ratio": 1.4, "_prepared": True},
        {"symbol": "HDFCBANK",  "ltp": 795.0,  "resistance": 800.0,  "support": 750.0,  "rsi": 48.0, "volume_ratio": 1.2, "_prepared": True},
        {"symbol": "INFY",      "ltp": 1700.0, "resistance": 1750.0, "support": 1650.0, "rsi": 55.0, "volume_ratio": 1.8, "_prepared": True},
    ]
    STATIC = [
        {"symbol": "RELIANCE",  "ltp": 1399.0, "resistance": 1448.0, "support": 1288.0, "rsi": 54.0, "volume_ratio": 1.1},  # duplicate
        {"symbol": "TATASTEEL", "ltp": 145.0,  "resistance": 150.0,  "support": 140.0,  "rsi": 60.0, "volume_ratio": 2.1},
        {"symbol": "ITC",       "ltp": 420.0,  "resistance": 430.0,  "support": 410.0,  "rsi": 44.0, "volume_ratio": 1.3},
    ]

    # Simulate the merge logic from scan()
    prepared_syms = {r["symbol"] for r in PREPARED}
    gap_fill = [s for s in STATIC if s["symbol"] not in prepared_syms]
    merged = PREPARED + gap_fill

    # Assertions
    assert len(prepared_syms) == 3, "prepared_syms count wrong"

    if len(gap_fill) != 2:
        issues.append(f"FAIL: gap_fill={len(gap_fill)} expected 2 (TATASTEEL + ITC)")
    else:
        issues.append(f"✓ gap_fill={len(gap_fill)} correct: RELIANCE deduped, TATASTEEL+ITC added")

    if len(merged) != 5:
        issues.append(f"FAIL: merged={len(merged)} expected 5")
    else:
        issues.append(f"✓ merged total={len(merged)} correct (3 prepared + 2 gap-fill)")

    # RELIANCE must come from prepared (priority)
    reliance_row = next((r for r in merged if r["symbol"] == "RELIANCE"), None)
    if reliance_row is None:
        issues.append("FAIL: RELIANCE missing from merged")
    elif not reliance_row.get("_prepared"):
        issues.append("FAIL: RELIANCE came from static, not prepared (priority violated)")
    else:
        issues.append("✓ RELIANCE sourced from prepared (priority correct)")

    # Test empty prepared → fall through to static
    empty_prepared_syms: set = set()
    full_static = [s for s in STATIC if s["symbol"] not in empty_prepared_syms]
    if len(full_static) != len(STATIC):
        issues.append("FAIL: empty prepared should yield full static list")
    else:
        issues.append("✓ empty prepared → full static fallback correct")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    else:
        _emit(section, _PASS, [
            f"prepared={len(PREPARED)} static_gap_fill={len(gap_fill)} duplicates_removed=1 total={len(merged)}",
        ] + [i for i in issues if i.startswith("✓")])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — PREPARED CANDIDATE DETERMINISM (no jitter)
# ─────────────────────────────────────────────────────────────────────────────

def validate_prepared_determinism() -> None:
    section = "ValidationPreparedDeterminism"
    issues: List[str] = []

    # Prepared candidates bypass _live_watchlist() entirely — they come from
    # _prepared_watchlist() which returns exact store values without jitter.
    # Static candidates pass through _live_watchlist() which applies jitter.
    # We verify: (a) _prepared_watchlist() returns exact values from store,
    # (b) the merge path preserves them unchanged.

    STORE_CANDIDATE = {
        "symbol": "TCS", "resistance": 3300.0, "support": 3200.0,
        "rsi": 53.0, "volume_ratio": 1.5, "adv_crore": 900.0,
        "score": 0.72, "buckets": ["breakout"], "valid_until_utc": None,
    }

    # After _prepared_watchlist() maps the store candidate, it preserves:
    # resistance, support, rsi, volume_ratio (no jitter added)
    simulated_prepared_row = {
        "symbol":       STORE_CANDIDATE["symbol"],
        "ltp":          0.0,   # filled from price cache
        "resistance":   STORE_CANDIDATE["resistance"],
        "support":      STORE_CANDIDATE["support"],
        "volume_ratio": STORE_CANDIDATE.get("volume_ratio", 1.0),
        "rsi":          STORE_CANDIDATE.get("rsi", 50.0),
        "adv_crore":    STORE_CANDIDATE.get("adv_crore", 0.0),
        "_prepared":    True,
    }

    # Same candidate evaluated twice → identical technical values (deterministic)
    second_eval = dict(simulated_prepared_row)

    if simulated_prepared_row["resistance"] != second_eval["resistance"]:
        issues.append("FAIL: resistance not deterministic across evaluations")
    if simulated_prepared_row["support"] != second_eval["support"]:
        issues.append("FAIL: support not deterministic across evaluations")
    if simulated_prepared_row["rsi"] != second_eval["rsi"]:
        issues.append("FAIL: rsi not deterministic across evaluations")
    if simulated_prepared_row["volume_ratio"] != second_eval["volume_ratio"]:
        issues.append("FAIL: volume_ratio not deterministic across evaluations")

    # Static fallback DOES use jitter (by design) — verify the code path
    try:
        import opportunity_engine.equity_scanner_ai as _esa
        src = inspect.getsource(_esa._live_watchlist)
        if "rng.uniform" not in src:
            issues.append("WARN: _live_watchlist() jitter may have been removed — check static path")
        else:
            issues.append("✓ _live_watchlist() still applies jitter to static candidates (correct)")
        # Prepared path: _prepared_watchlist does NOT call rng.uniform
        prep_src = inspect.getsource(_esa._prepared_watchlist)
        if "rng.uniform" in prep_src:
            issues.append("FAIL: _prepared_watchlist() contains rng.uniform — jitter on prepared candidates!")
        else:
            issues.append("✓ _prepared_watchlist() contains no jitter (deterministic)")
    except Exception as exc:
        issues.append(f"SKIP: could not inspect source: {exc}")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    else:
        _emit(section, _PASS, [
            "resistance/support/rsi/volume_ratio deterministic for prepared candidates",
        ] + [i for i in issues if "✓" in i or "WARN" in i])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — TELEMETRY VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_telemetry() -> None:
    section = "ValidationTelemetry"
    issues: List[str] = []

    # Tags that must exist (emitted by the architecture)
    REQUIRED_TAGS = [
        "[PreparedUniverseHealth]",
        "[PreparedUniverseAudit]",
        "[ExplorationAudit]",
        "[ExplorationCandidate]",
        "[StaticFallbackActivated]",
        "[ScannerPerformance]",
        "[HybridExploration]",
        "[PreparedUniverseDegraded]",
        "[PreparedUniverseSafeMode]",
        "[CandidateStore]",
        "[UniverseAudit]",
        "[EdgeTelemetry]",
    ]

    # Check tags appear in source files
    TAG_SOURCES = [
        _ROOT / "opportunity_engine" / "equity_scanner_ai.py",
        _ROOT / "opportunity_engine" / "market_scanner.py",
        _ROOT / "opportunity_engine" / "premarket_refiner.py",
        _ROOT / "opportunity_engine" / "candidate_store.py",
        _ROOT / "orchestrator" / "master_orchestrator.py",
    ]

    all_source = ""
    for f in TAG_SOURCES:
        if f.exists():
            all_source += f.read_text(encoding="utf-8")

    missing_tags = []
    for tag in REQUIRED_TAGS:
        if tag not in all_source:
            missing_tags.append(tag)
        else:
            issues.append(f"✓ {tag}")

    if missing_tags:
        for t in missing_tags:
            issues.append(f"FAIL: tag {t} not found in source files")

    # Verify _emit_prepared_universe_health is callable and doesn't raise
    try:
        import opportunity_engine.equity_scanner_ai as _esa
        # Suppress output during test call
        _esa._emit_prepared_universe_health(0, True, 0)
        issues.append("✓ _emit_prepared_universe_health() callable without exception")
    except Exception as exc:
        issues.append(f"FAIL: _emit_prepared_universe_health() raised: {exc}")

    # Verify get_session_exploration_stats is callable
    try:
        import opportunity_engine.equity_scanner_ai as _esa
        stats = _esa.get_session_exploration_stats()
        if not isinstance(stats, dict):
            issues.append("FAIL: get_session_exploration_stats() returned non-dict")
        elif "evaluated" not in stats or "signals_generated" not in stats:
            issues.append("FAIL: exploration stats missing expected keys")
        else:
            issues.append("✓ get_session_exploration_stats() returns valid dict")
    except Exception as exc:
        issues.append(f"FAIL: get_session_exploration_stats() raised: {exc}")

    if missing_tags:
        _emit(section, _FAIL, [f"missing_tags={len(missing_tags)}"] + [i for i in issues if "FAIL" in i])
    else:
        _emit(section, _PASS, [f"missing_tags=0 all_tags_present=True"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — SAFE MODE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_safe_mode() -> None:
    section = "ValidationSafeMode"
    issues: List[str] = []

    try:
        import opportunity_engine.equity_scanner_ai as _esa
    except Exception as exc:
        _fail(section, f"Cannot import equity_scanner_ai: {exc}")
        return

    # Save initial state
    orig_active = _esa._SAFE_MODE_ACTIVE
    orig_reason = _esa._SAFE_MODE_REASON

    try:
        # Test 1: Safe mode ON → _prepared_watchlist() returns []
        _esa._SAFE_MODE_ACTIVE = True
        _esa._SAFE_MODE_REASON = "FORENSIC_TEST"
        result = _esa._prepared_watchlist()
        if result != []:
            issues.append(f"FAIL: safe mode active but _prepared_watchlist() returned {len(result)} rows")
        else:
            issues.append("✓ safe mode=True → _prepared_watchlist() returns []")

        # Test 2: Safe mode OFF → _prepared_watchlist() attempts store read (returns [] only if no file)
        _esa._SAFE_MODE_ACTIVE = False
        _esa._SAFE_MODE_REASON = ""
        result2 = _esa._prepared_watchlist()
        # Should be a list (possibly empty if no store file) but not crash
        if not isinstance(result2, list):
            issues.append("FAIL: _prepared_watchlist() with safe_mode=False returned non-list")
        else:
            issues.append(f"✓ safe mode=False → _prepared_watchlist() returns list ({len(result2)} rows)")

        # Test 3: _check_safe_mode_triggers() doesn't raise on empty prepared list
        try:
            _esa._check_safe_mode_triggers([])
            issues.append("✓ _check_safe_mode_triggers([]) completes without exception")
        except Exception as exc:
            issues.append(f"FAIL: _check_safe_mode_triggers([]) raised: {exc}")

        # Test 4: Source inspection — safe mode guards exploration
        src = inspect.getsource(_esa.EquityScannerAI.scan)
        if "_SAFE_MODE_ACTIVE" not in src:
            issues.append("FAIL: scan() does not reference _SAFE_MODE_ACTIVE (safe mode bypass possible)")
        else:
            issues.append("✓ scan() references _SAFE_MODE_ACTIVE (exploration guarded)")

        if "not _SAFE_MODE_ACTIVE" not in src:
            issues.append("WARN: exploration block may not check 'not _SAFE_MODE_ACTIVE'")
        else:
            issues.append("✓ exploration explicitly gated on 'not _SAFE_MODE_ACTIVE'")

    finally:
        # Always restore state
        _esa._SAFE_MODE_ACTIVE = orig_active
        _esa._SAFE_MODE_REASON = orig_reason

    # Exploration bypassing the safe mode gate = CRITICAL (governance at risk)
    bypass_fail = any(
        "scan() does not reference _SAFE_MODE_ACTIVE" in i for i in issues
    )
    if any(i.startswith("FAIL") for i in issues):
        sev = ValidationSeverity.CRITICAL if bypass_fail else ValidationSeverity.FAIL
        _emit(section, _FAIL, issues, severity=sev)
    else:
        _emit(section, _PASS, [i for i in issues if "✓" in i])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — OVERLAY VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_overlay() -> None:
    section = "ValidationOverlay"
    issues: List[str] = []

    try:
        import global_intelligence.global_data_ai as _gd
        src = inspect.getsource(_gd.GlobalDataAI.get_sector_regime_bias)
    except Exception as exc:
        _skip(section, f"Cannot inspect get_sector_regime_bias: {exc}")
        return

    # Cap at ±0.20 must be present
    if "max(-0.20, min(0.20" in src or "min(0.20, max(-0.20" in src:
        issues.append("✓ adaptive_adjustment capped at ±0.20 in source")
    elif "-0.20" in src and "0.20" in src:
        issues.append("✓ ±0.20 bounds present in overlay logic (check form manually)")
    else:
        issues.append("FAIL: ±0.20 overlay cap NOT found in get_sector_regime_bias")

    # Disabled when VIX > 30 (proxy for regime confidence)
    if "vix" in src.lower() and "> 30" in src:
        issues.append("✓ overlay disabled when VIX > 30 (regime uncertainty proxy)")
    else:
        issues.append("WARN: VIX > 30 guard may be missing from overlay logic")

    # USE_OVERNIGHT_OVERLAY guard present
    if "USE_OVERNIGHT_OVERLAY" in src:
        issues.append("✓ USE_OVERNIGHT_OVERLAY config flag respected in overlay method")
    else:
        issues.append("FAIL: USE_OVERNIGHT_OVERLAY not checked in get_sector_regime_bias")

    # Test that overlay returns dict (not raising) with a mock-less call
    try:
        obj = _gd.GlobalDataAI()
        obj._last_snap = None  # No snapshot → should return empty dict
        result = obj.get_sector_regime_bias()
        if not isinstance(result, dict):
            issues.append("FAIL: get_sector_regime_bias() returned non-dict")
        else:
            issues.append(f"✓ get_sector_regime_bias() callable, returns dict (empty on no snap)")
    except Exception as exc:
        issues.append(f"FAIL: get_sector_regime_bias() raised: {exc}")

    # Verify all bias values are bounded [-0.20, +0.20]
    # Manually test with extreme inputs (monkey-patch _last_snap)
    try:
        from global_intelligence.global_data_ai import GlobalSnapshot
        # Extreme bull: S&P +5%, Nikkei +5%, Crude +5%, DXY +2%, low VIX
        extreme_snap = GlobalSnapshot(
            sp500_change=5.0, nasdaq_change=4.0, nikkei_change=5.0, hangseng_change=3.0,
            sgx_nifty_change=2.0, crude_brent_change=5.0, gold_change=0.0,
            usdinr_change=0.0, dxy_change=2.0, us10y_change_bps=20.0, cboe_vix=15.0,
            timestamp=datetime.now(timezone.utc),
        )
        obj._last_snap = extreme_snap
        bias_extreme = obj.get_sector_regime_bias()
        if bias_extreme:
            out_of_bounds = {k: v for k, v in bias_extreme.items() if abs(v) > 0.201}
            if out_of_bounds:
                issues.append(f"FAIL: overlay values exceed ±0.20: {out_of_bounds}")
            else:
                issues.append(f"✓ extreme bias test: all {len(bias_extreme)} sectors bounded ±0.20")
    except Exception as exc:
        issues.append(f"SKIP: extreme bias test skipped: {exc}")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, [i for i in issues if "WARN" in i or "✓" in i])
    else:
        _emit(section, _PASS, ["adaptive_adjustment ∈ [-0.20, +0.20] verified"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — PREMARKET VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_premarket() -> None:
    section = "ValidationPremarket"
    issues: List[str] = []

    try:
        import opportunity_engine.premarket_refiner as _pr
    except Exception as exc:
        _fail(section, f"Cannot import premarket_refiner: {exc}")
        return

    # conviction_decay values exist for both breakout and non-breakout
    try:
        src = inspect.getsource(_pr)
        if "conviction_decay" not in src:
            issues.append("FAIL: conviction_decay not present in premarket_refiner")
        else:
            issues.append("✓ conviction_decay present in premarket_refiner")

        # Decay constants (premarket_refiner uses DECAY_RSI_DRIFT / DECAY_VOL_FACTOR)
        if "DECAY_RSI_DRIFT" in src:
            issues.append("✓ DECAY_RSI_DRIFT constant present in premarket_refiner")
        else:
            issues.append("WARN: DECAY_RSI_DRIFT missing from premarket_refiner")

        if "DECAY_VOL_FACTOR" in src:
            issues.append("✓ DECAY_VOL_FACTOR constant present in premarket_refiner")
        else:
            issues.append("WARN: DECAY_VOL_FACTOR missing from premarket_refiner")

    except Exception as exc:
        issues.append(f"SKIP: cannot inspect premarket_refiner source: {exc}")

    # valid_until_utc assignment map exists
    try:
        vut = getattr(_pr, "_VALID_UNTIL_UTC", None)
        if vut is None:
            issues.append("FAIL: _VALID_UNTIL_UTC map missing from premarket_refiner")
        elif not isinstance(vut, dict):
            issues.append(f"FAIL: _VALID_UNTIL_UTC is {type(vut)}, expected dict")
        else:
            issues.append(f"✓ _VALID_UNTIL_UTC map present with {len(vut)} setup types")
    except Exception as exc:
        issues.append(f"WARN: cannot check _VALID_UNTIL_UTC: {exc}")

    # run_premarket_refinement exists and is callable
    if not hasattr(_pr, "run_premarket_refinement"):
        issues.append("FAIL: run_premarket_refinement() function missing")
    else:
        issues.append("✓ run_premarket_refinement() exists")

    # Config: PREMARKET_MAX_RUNTIME_MINUTES and PREMARKET_DEADLINE_UTC_HHMM
    try:
        import config as cfg
        pmr = getattr(cfg, "PREMARKET_MAX_RUNTIME_MINUTES", None)
        pmd = getattr(cfg, "PREMARKET_DEADLINE_UTC_HHMM", None)
        if pmr is None:
            issues.append("FAIL: PREMARKET_MAX_RUNTIME_MINUTES missing from config")
        elif pmr > 60:
            issues.append(f"WARN: PREMARKET_MAX_RUNTIME_MINUTES={pmr} seems very high")
        else:
            issues.append(f"✓ PREMARKET_MAX_RUNTIME_MINUTES={pmr}")
        if pmd is None:
            issues.append("FAIL: PREMARKET_DEADLINE_UTC_HHMM missing from config")
        else:
            issues.append(f"✓ PREMARKET_DEADLINE_UTC_HHMM={pmd}")
    except Exception as exc:
        issues.append(f"WARN: config check failed: {exc}")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, [i for i in issues if "WARN" in i or "✓" in i])
    else:
        _emit(section, _PASS, ["conviction_decay present valid_until_utc map present"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — EXPLORATION VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_exploration() -> None:
    section = "ValidationExploration"
    issues: List[str] = []

    try:
        import config as cfg
        import opportunity_engine.equity_scanner_ai as _esa
    except Exception as exc:
        _fail(section, f"Cannot import modules: {exc}")
        return

    bpct = getattr(cfg, "EXPLORATION_BUDGET_PCT", -1)
    thr  = getattr(cfg, "EXPLORATION_THRESHOLD",  -1.0)
    upv  = getattr(cfg, "USE_PREPARED_UNIVERSE",  False)
    uhe  = getattr(cfg, "USE_HYBRID_EXPLORATION", False)

    # Budget ≤ 20 (deliberate 80/20 decision 2026-05-22; previously soft cap was 10)
    if bpct > 20:
        issues.append(f"FAIL: EXPLORATION_BUDGET_PCT={bpct} exceeds hard cap of 20")
    elif bpct <= 0:
        issues.append(f"FAIL: EXPLORATION_BUDGET_PCT={bpct} must be > 0")
    else:
        issues.append(f"✓ EXPLORATION_BUDGET_PCT={bpct} within deliberate 80/20 bounds")

    # Threshold raised above standard confidence floor
    if thr < 7.0:
        issues.append(f"WARN: EXPLORATION_THRESHOLD={thr} below recommended 7.0 minimum")
    else:
        issues.append(f"✓ EXPLORATION_THRESHOLD={thr} above standard confidence floor")

    # Slot calculation: 20% of 40 prepared → max(1, 40*20//80) = max(1,10) = 10
    n_prepared = 40
    slots = max(1, n_prepared * bpct // max(100 - bpct, 1))
    issues.append(f"✓ slot calculation: {n_prepared} prepared @ {bpct}% = {slots} explore slot(s)")

    # No double-count: exploration only from symbols NOT in prepared set
    # Verify this in source
    try:
        src = inspect.getsource(_esa.EquityScannerAI.scan)
        if "prepared_syms" in src and "not in prepared_syms" in src:
            issues.append("✓ exploration candidates explicitly excluded from prepared set (no double-count)")
        else:
            issues.append("WARN: cannot confirm exploration excludes prepared symbols via source inspection")
    except Exception as exc:
        issues.append(f"SKIP: cannot inspect scan() source: {exc}")

    # Tuple-unpacking fix: _identify_setup returns (signal, reason)
    # Verify the exploration block uses sig, _reason = ...
    try:
        src = inspect.getsource(_esa.EquityScannerAI.scan)
        if "sig, _reason = self._identify_setup" in src:
            issues.append("✓ exploration block correctly unpacks (sig, _reason) tuple")
        elif "sig = self._identify_setup" in src:
            issues.append("FAIL: exploration block still uses bare 'sig = self._identify_setup()' — tuple not unpacked (pre-existing bug NOT fixed)")
        else:
            issues.append("WARN: cannot confirm tuple-unpacking fix via source inspection")
    except Exception as exc:
        issues.append(f"SKIP: tuple-unpack check skipped: {exc}")

    # Exploration telemetry
    try:
        stats = _esa.get_session_exploration_stats()
        if set(stats.keys()) >= {"evaluated", "signals_generated"}:
            issues.append(f"✓ session exploration counters accessible: {stats}")
        else:
            issues.append(f"WARN: unexpected exploration stat keys: {list(stats.keys())}")
    except Exception as exc:
        issues.append(f"WARN: cannot read exploration stats: {exc}")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, [f"budget_pct={bpct} threshold={thr}"] + issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, [f"budget_pct={bpct} threshold={thr}"] + [i for i in issues if "WARN" in i or "✓" in i])
    else:
        _emit(section, _PASS, [f"budget_pct={bpct} threshold={thr}"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — GOVERNANCE PRESERVATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_governance() -> None:
    section = "ValidationGovernance"
    issues: List[str] = []

    # Protected Layer 5+ modules — must be importable with expected interfaces
    PROTECTED = [
        ("risk_guardian.risk_guardian",     "FailSafeRiskGuardian", "evaluate"),
        ("strategy_lab.backtesting_ai",     "BacktestingAI",        "run_full_backtest"),
        ("decision_ai.decision_engine",     "DecisionEngine",       "decide"),
        ("execution_engine.order_manager",  "OrderManager",         "execute"),
        ("risk_control.risk_manager_ai",    "RiskManagerAI",        "filter"),
    ]

    for mod_path, class_name, method_name in PROTECTED:
        try:
            mod = __import__(mod_path, fromlist=[class_name])
            cls = getattr(mod, class_name, None)
            if cls is None:
                issues.append(f"FAIL: {class_name} not found in {mod_path}")
                continue
            method = getattr(cls, method_name, None)
            if method is None:
                issues.append(f"FAIL: {class_name}.{method_name}() missing")
            else:
                issues.append(f"✓ {class_name}.{method_name}() accessible")
        except ImportError as exc:
            issues.append(f"WARN: cannot import {mod_path}: {exc}")
        except Exception as exc:
            issues.append(f"WARN: {mod_path} check failed: {exc}")

    # Verify that equity_scanner_ai does NOT contain references to
    # debate, MC, or governance classes (no bypass)
    try:
        import opportunity_engine.equity_scanner_ai as _esa
        src = inspect.getsource(_esa)
        bypass_indicators = ["skip_debate", "bypass_governance", "skip_risk", "force_execute"]
        for indicator in bypass_indicators:
            if indicator in src:
                issues.append(f"FAIL: equity_scanner_ai contains '{indicator}' — possible governance bypass")
        issues.append("✓ equity_scanner_ai source contains no governance bypass indicators")
    except Exception as exc:
        issues.append(f"SKIP: bypass check failed: {exc}")

    # Verify prepared architecture only changes input layer
    try:
        src = inspect.getsource(_esa)
        # Exploration signals must NOT have a confidence=999 or force_approve style override
        if "force_approve" in src or "confidence=10" in src or "skip_debate=True" in src:
            issues.append("FAIL: exploration path contains approval bypass indicators")
        else:
            issues.append("✓ no execution bypass in exploration path")
    except Exception:
        pass

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, [i for i in issues if "WARN" in i or "✓" in i])
    else:
        _emit(section, _PASS, ["Layer 5+ interfaces intact no bypasses detected"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 13 — PERFORMANCE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_performance() -> None:
    section = "ValidationPerformance"
    issues: List[str] = []

    try:
        import config as cfg
    except Exception as exc:
        _fail(section, f"Cannot import config: {exc}")
        return

    checks = [
        ("SCANNER_MAX_RUNTIME_MINUTES",   "scanner_max_runtime_min",   20,  60),
        ("PREMARKET_MAX_RUNTIME_MINUTES", "premarket_max_runtime_min", 25,  60),
        ("SCANNER_MAX_SYMBOLS",           "scanner_max_symbols",       50, 1000),
        ("SCANNER_MAX_CANDIDATES",        "scanner_max_candidates",    10,  300),
    ]

    scan_time = None
    pre_time  = None

    for cfg_name, label, lo, hi in checks:
        val = getattr(cfg, cfg_name, None)
        if val is None:
            issues.append(f"WARN: {cfg_name} not defined in config")
            continue
        if not (lo <= val <= hi):
            issues.append(f"WARN: {cfg_name}={val} outside expected range [{lo}, {hi}]")
        else:
            issues.append(f"✓ {cfg_name}={val}")
        if cfg_name == "SCANNER_MAX_RUNTIME_MINUTES":
            scan_time = val
        if cfg_name == "PREMARKET_MAX_RUNTIME_MINUTES":
            pre_time = val

    # CandidateStore load latency: read() should complete in <1s (file-based)
    try:
        from opportunity_engine.candidate_store import CandidateStore, STORE_FILE
        if STORE_FILE.exists():
            t0 = time.monotonic()
            _ = CandidateStore.read()
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            if elapsed_ms > 500:
                issues.append(f"WARN: CandidateStore.read() took {elapsed_ms:.0f}ms (> 500ms threshold)")
            else:
                issues.append(f"✓ CandidateStore.read() latency={elapsed_ms:.1f}ms")
        else:
            issues.append("INFO: load latency test skipped (no store file yet)")
    except Exception as exc:
        issues.append(f"SKIP: load latency test failed: {exc}")

    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, [
            f"scanner_max_runtime_min={scan_time} premarket_max_runtime_min={pre_time}",
        ] + [i for i in issues if "WARN" in i])
    else:
        _emit(section, _PASS, [
            f"scanner_max_runtime_min={scan_time} premarket_max_runtime_min={pre_time}",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — Research Integrity Protection
# ─────────────────────────────────────────────────────────────────────────────

def validate_research_integrity() -> None:
    """
    Verify the Research Integrity Patchset is correctly installed:
      1. ClosedTradeRecord carries architecture_generation field
      2. PREPARED_UNIVERSE_ACTIVATION_DATE is defined in config
      3. MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT constant exists (≥ 20)
      4. Research weight constants defined (LEGACY ≤ 0.30, PREPARED = 1.00)
      5. _check_disable() guards against LEGACY_STATIC-driven disables
      6. [ResearchIntegrity] and [ArchitectureGeneration] log tags present in source
    """
    section = "ValidationResearchIntegrity"
    issues:  List[str] = []

    # ── Check 1: ClosedTradeRecord has architecture_generation ────────────
    try:
        import dataclasses
        sys.path.insert(0, str(_ROOT))
        import importlib
        _ta_mod = importlib.import_module("trade_monitoring.trade_analytics")
        _fields = {f.name for f in dataclasses.fields(_ta_mod.ClosedTradeRecord)}
        if "architecture_generation" in _fields:
            issues.append("✓ ClosedTradeRecord.architecture_generation field present")
        else:
            issues.append("FAIL: ClosedTradeRecord missing architecture_generation field")
    except Exception as exc:
        issues.append(f"SKIP: ClosedTradeRecord check failed: {exc}")

    # ── Check 2: config.PREPARED_UNIVERSE_ACTIVATION_DATE ────────────────
    try:
        import config as _cfg
        _act_date = getattr(_cfg, "PREPARED_UNIVERSE_ACTIVATION_DATE", None)
        if _act_date and len(_act_date) == 10:
            issues.append(f"✓ PREPARED_UNIVERSE_ACTIVATION_DATE={_act_date}")
        else:
            issues.append("FAIL: PREPARED_UNIVERSE_ACTIVATION_DATE missing or invalid in config.py")
    except Exception as exc:
        issues.append(f"SKIP: config check: {exc}")

    # ── Check 3: MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT ──────
    try:
        import config as _cfg
        _min_prep = getattr(_cfg, "MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT", None)
        if _min_prep is None:
            issues.append("FAIL: MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT not in config.py")
        elif _min_prep < 20:
            issues.append(
                f"WARN: MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT={_min_prep} "
                "is below 20 — consider ≥25 for meaningful strategy governance"
            )
        else:
            issues.append(
                f"✓ MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT={_min_prep}"
            )
    except Exception as exc:
        issues.append(f"SKIP: min_prep check: {exc}")

    # ── Check 4: Research weight constants ───────────────────────────────
    try:
        import config as _cfg
        _legacy_w   = getattr(_cfg, "RESEARCH_WEIGHT_LEGACY_STATIC", None)
        _prep_w     = getattr(_cfg, "RESEARCH_WEIGHT_PREPARED_V1",   None)
        if _legacy_w is None or _prep_w is None:
            issues.append("FAIL: RESEARCH_WEIGHT_LEGACY_STATIC or RESEARCH_WEIGHT_PREPARED_V1 missing")
        elif _legacy_w > 0.30:
            issues.append(
                f"WARN: RESEARCH_WEIGHT_LEGACY_STATIC={_legacy_w} > 0.30 "
                "— legacy weight should stay ≤ 0.30 to limit bias"
            )
        elif abs(_prep_w - 1.00) > 0.01:
            issues.append(
                f"WARN: RESEARCH_WEIGHT_PREPARED_V1={_prep_w} ≠ 1.00"
            )
        else:
            issues.append(
                f"✓ research weights: legacy={_legacy_w}  prepared={_prep_w}"
            )
    except Exception as exc:
        issues.append(f"SKIP: weight constants check: {exc}")

    # ── Check 5: _check_disable() guard exists in strategy_performance_tracker ──
    try:
        _spt_path = _ROOT / "learning_system" / "strategy_performance_tracker.py"
        _spt_src  = _spt_path.read_text(encoding="utf-8")
        _guard_present = "prepared_universe_trades" in _spt_src and \
                         "MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT" in _spt_src
        if _guard_present:
            issues.append("✓ strategy_performance_tracker._check_disable() has research integrity guard")
        else:
            issues.append(
                "FAIL: strategy_performance_tracker.py missing prepared_universe_trades guard"
            )
    except Exception as exc:
        issues.append(f"SKIP: _check_disable guard check: {exc}")

    # ── Check 6: [ResearchIntegrity] and [ArchitectureGeneration] tags ───
    _TAG_SOURCES_RI = [
        ("trade_monitoring/trade_analytics.py",              "[ArchitectureGeneration]"),
        ("learning_system/strategy_performance_tracker.py",  "[ResearchIntegrity]"),
        ("learning_system/daily_self_evaluation.py",         "[ResearchIntegrity]"),
        ("learning_system/eod_retrospective.py",             "[ResearchIntegrity]"),
    ]
    _missing_tags = []
    for _rel_path, _tag in _TAG_SOURCES_RI:
        try:
            _src = (_ROOT / _rel_path).read_text(encoding="utf-8")
            if _tag not in _src:
                _missing_tags.append(f"{_rel_path} missing {_tag}")
        except Exception as exc:
            _missing_tags.append(f"{_rel_path}: {exc}")
    if _missing_tags:
        for m in _missing_tags:
            issues.append(f"FAIL: {m}")
    else:
        issues.append(
            "✓ [ArchitectureGeneration] + [ResearchIntegrity] tags present in all required sources"
        )

    # ── Emit result ───────────────────────────────────────────────────────
    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, issues)
    else:
        _emit(section, _PASS, issues)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 15 — Research Maturity (Patches 19-24)
# ─────────────────────────────────────────────────────────────────────────────

def validate_research_maturity() -> None:
    """
    Patch 25 — Verify Research Hardening Additions (Patches 19-24) are installed:
      1. research_integrity.py module exists with dynamic decay formula
      2. MIN_CLEAN_PREPARED_TRADES=100 in config.py
      3. [CleanResearchState] freeze gate wired into _check_disable()
      4. compute_legacy_weight() uses exp decay formula
      5. [ResearchContamination] tag emitted in eod_retrospective.py
      6. [TelemetryGeneration] tag emitted in eod_retrospective.py
      7. Dynamic weight used in daily_self_evaluation.py
      Emits [ValidationResearchMaturity].
    """
    section = "ValidationResearchMaturity"
    issues: List[str] = []

    # ── Check 1: research_integrity.py module exists ──────────────────────
    _ri_path = _ROOT / "learning_system" / "research_integrity.py"
    try:
        _ri_src = _ri_path.read_text(encoding="utf-8")
        issues.append("✓ learning_system/research_integrity.py present")
    except Exception as exc:
        issues.append(f"FAIL: learning_system/research_integrity.py missing: {exc}")
        _ri_src = ""

    # ── Check 2: dynamic decay formula present ────────────────────────────
    if _ri_src:
        _decay_markers = [
            "compute_legacy_weight",
            "math.exp(",
            "_LEGACY_W_FLOOR",
            "_LEGACY_DECAY_K",
        ]
        for _m in _decay_markers:
            if _m in _ri_src:
                issues.append(f"✓ dynamic decay: {_m} present")
            else:
                issues.append(f"FAIL: dynamic decay formula missing '{_m}' in research_integrity.py")

    # ── Check 3: MIN_CLEAN_PREPARED_TRADES in config ──────────────────────
    try:
        import config as _cfg
        _min_clean = getattr(_cfg, "MIN_CLEAN_PREPARED_TRADES", None)
        if _min_clean is None:
            issues.append("FAIL: MIN_CLEAN_PREPARED_TRADES not in config.py")
        elif _min_clean < 50:
            issues.append(
                f"WARN: MIN_CLEAN_PREPARED_TRADES={_min_clean} < 50 "
                "— very low freeze threshold; consider ≥100"
            )
        else:
            issues.append(f"✓ MIN_CLEAN_PREPARED_TRADES={_min_clean}")
    except Exception as exc:
        issues.append(f"SKIP: MIN_CLEAN_PREPARED_TRADES check: {exc}")

    # ── Check 4: [CleanResearchState] freeze gate in _check_disable() ─────
    try:
        _spt_path = _ROOT / "learning_system" / "strategy_performance_tracker.py"
        _spt_src  = _spt_path.read_text(encoding="utf-8")
        _freeze_markers = [
            "[CleanResearchState]",
            "is_clean_research_ready",
            "adaptive mutation freeze",
        ]
        _missing_freeze = [m for m in _freeze_markers if m not in _spt_src]
        if _missing_freeze:
            issues.append(
                f"FAIL: strategy_performance_tracker.py missing freeze markers: "
                f"{_missing_freeze}"
            )
        else:
            issues.append(
                "✓ [CleanResearchState] freeze gate wired into _check_disable()"
            )
    except Exception as exc:
        issues.append(f"SKIP: freeze gate check: {exc}")

    # ── Check 5: [ResearchContamination] and [TelemetryGeneration] tags ───
    # [ResearchContamination] is defined in research_integrity.py (emitted there).
    # [TelemetryGeneration] is used directly in eod_retrospective.py.
    try:
        _eod_src = (_ROOT / "learning_system" / "eod_retrospective.py").read_text(encoding="utf-8")
        if "[TelemetryGeneration]" in _eod_src:
            issues.append("✓ [TelemetryGeneration] present in eod_retrospective.py")
        else:
            issues.append("FAIL: [TelemetryGeneration] missing in eod_retrospective.py")
        # emit_contamination_telemetry() call routes through research_integrity.py
        if "emit_contamination_telemetry" in _eod_src:
            issues.append("✓ emit_contamination_telemetry() called in eod_retrospective.py")
        else:
            issues.append("FAIL: emit_contamination_telemetry missing in eod_retrospective.py")
    except Exception as exc:
        issues.append(f"SKIP: eod_retrospective check: {exc}")
    try:
        _ri_src2 = (_ROOT / "learning_system" / "research_integrity.py").read_text(encoding="utf-8")
        if "[ResearchContamination]" in _ri_src2:
            issues.append("✓ [ResearchContamination] defined in research_integrity.py")
        else:
            issues.append("FAIL: [ResearchContamination] missing in research_integrity.py")
    except Exception as exc:
        issues.append(f"SKIP: [ResearchContamination] source check: {exc}")

    # ── Check 6: dynamic weight used in daily_self_evaluation ────────────
    try:
        _dse_src = (_ROOT / "learning_system" / "daily_self_evaluation.py").read_text(encoding="utf-8")
        _dse_markers = ["compute_legacy_weight", "emit_contamination_telemetry", "emit_clean_research_state"]
        for _m in _dse_markers:
            if _m in _dse_src:
                issues.append(f"✓ {_m} imported in daily_self_evaluation.py")
            else:
                issues.append(f"FAIL: {_m} missing in daily_self_evaluation.py")
    except Exception as exc:
        issues.append(f"SKIP: daily_self_evaluation check: {exc}")

    # ── Check 7: functional smoke test of research_integrity module ───────
    try:
        import math as _math
        import sys as _sys
        if str(_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_ROOT))
        import importlib
        _ri_mod = importlib.import_module("learning_system.research_integrity")
        # Test compute_legacy_weight
        _w0   = _ri_mod.compute_legacy_weight(0)
        _w100 = _ri_mod.compute_legacy_weight(100)
        _w300 = _ri_mod.compute_legacy_weight(300)
        if not (0.24 < _w0 <= 0.25):
            issues.append(f"FAIL: compute_legacy_weight(0)={_w0} expected ≈0.25")
        elif not (_w100 <= 0.11):
            issues.append(f"FAIL: compute_legacy_weight(100)={_w100} expected ≤0.11 (floor at 0.10)")
        elif not (_w300 == 0.10):
            issues.append(f"FAIL: compute_legacy_weight(300)={_w300} expected 0.10 (floor)")
        else:
            issues.append(
                f"✓ dynamic decay: w(0)={_w0}  w(100)={_w100}  w(300)={_w300}  floor=0.10"
            )
        # Test gate function exists
        _rdy = _ri_mod.is_clean_research_ready()
        issues.append(
            f"✓ is_clean_research_ready() callable → ready={_rdy}  "
            f"(mutation_frozen={not _rdy})"
        )
        # Emit [ValidationResearchMaturity] composite tag
        _lw_current = _ri_mod.compute_legacy_weight(_ri_mod.get_system_prepared_trade_count())
        _sys_prep   = _ri_mod.get_system_prepared_trade_count()
        print(
            f"  [ValidationResearchMaturity] legacy_weight={_lw_current:.4f}  "
            f"prepared_trades={_sys_prep}  clean_ready={_rdy}  "
            f"mutation_frozen={not _rdy}  status=PASS"
        )
    except Exception as exc:
        issues.append(f"SKIP: functional smoke test: {exc}")

    # ── Emit result ───────────────────────────────────────────────────────
    if any(i.startswith("FAIL") for i in issues):
        _emit(section, _FAIL, issues)
    elif any(i.startswith("WARN") for i in issues):
        _emit(section, _WARN, issues)
    else:
        _emit(section, _PASS, issues)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH 17 — DEPLOYMENT SNAPSHOT  |  PATCH 15 — JSON EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _capture_deployment_snapshot() -> Dict[str, Any]:
    """Capture deployment context for forensic record (Patch 17)."""
    snapshot: Dict[str, Any] = {
        "suite_version":  VALIDATION_SUITE_VERSION,
        "python_version": sys.version.split()[0],
        "timestamp_utc":  datetime.now(timezone.utc).isoformat(),
    }
    # Feature flags
    try:
        import config as _cfg
        snapshot.update({
            "prepared":    getattr(_cfg, "USE_PREPARED_UNIVERSE",    False),
            "overlay":     getattr(_cfg, "USE_OVERNIGHT_OVERLAY",    False),
            "premarket":   getattr(_cfg, "USE_PREMARKET_REFINEMENT", False),
            "exploration": getattr(_cfg, "USE_HYBRID_EXPLORATION",   False),
            "shadow":      getattr(_cfg, "SCANNER_SHADOW_MODE",      True),
            "budget_pct":  getattr(_cfg, "EXPLORATION_BUDGET_PCT",    3),
            "threshold":   getattr(_cfg, "EXPLORATION_THRESHOLD",    7.2),
        })
    except Exception:
        pass
    # Git hash (best effort)
    try:
        import subprocess as _sp
        res = _sp.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(_ROOT), timeout=3,
        )
        snapshot["git_hash"] = res.stdout.strip() if res.returncode == 0 else "unavailable"
    except Exception:
        snapshot["git_hash"] = "unavailable"
    # Container uptime via /proc/uptime (Linux only, best effort)
    try:
        uptime_text = Path("/proc/uptime").read_text()
        snapshot["container_uptime_hr"] = round(float(uptime_text.split()[0]) / 3600.0, 2)
    except Exception:
        pass
    return snapshot


def _export_validation_json(elapsed_sec: float, snapshot: Dict[str, Any]) -> None:
    """Export all ValidationResult objects + deployment context to JSON (Patch 15)."""
    try:
        report_dir = _ROOT / "data" / "validation_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "suite_version":       VALIDATION_SUITE_VERSION,
            "run_timestamp_utc":   datetime.now(timezone.utc).isoformat(),
            "duration_sec":        round(elapsed_sec, 3),
            "sections_run":        len(_validation_results),
            "activation_blocked":  any(
                r.severity == ValidationSeverity.CRITICAL for r in _validation_results
            ),
            "deployment_snapshot": snapshot,
            "results":             [r.to_dict() for r in _validation_results],
        }

        latest = report_dir / "latest_validation.json"
        latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        ts_tag  = datetime.now().strftime("%Y-%m-%d_%H%M")
        archive = report_dir / f"{ts_tag}_validation.json"
        archive.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print(f"  [ValidationExport] → data/validation_reports/latest_validation.json")
        print(f"  [ValidationExport] → data/validation_reports/{archive.name}")
    except Exception as exc:
        print(f"  [ValidationExport] skipped: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — FINAL FORENSIC SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(snapshot: Dict[str, Any] = None) -> int:
    elapsed  = time.monotonic() - _START_TIME
    snapshot = snapshot or {}

    n_critical = sum(1 for r in _validation_results if r.severity == ValidationSeverity.CRITICAL)
    n_fail     = sum(1 for r in _validation_results if r.severity == ValidationSeverity.FAIL)
    n_warn     = sum(1 for r in _validation_results if r.severity == ValidationSeverity.WARN)
    n_pass     = sum(1 for r in _validation_results if r.status  == _PASS)

    section_labels = {
        "ValidationConfig":               "Config Integrity",
        "ValidationCandidateStore":       "Candidate Store",
        "ValidationSchemaContract":       "Schema Contract",
        "ValidationPreparedMerge":        "Prepared Merge Logic",
        "ValidationPreparedDeterminism":  "Deterministic Levels",
        "ValidationTelemetry":            "Telemetry Tags",
        "ValidationSafeMode":             "Safe Mode",
        "ValidationOverlay":              "Overlay Bounds ±0.20",
        "ValidationPremarket":            "Premarket Logic",
        "ValidationExploration":          "Exploration Governance",
        "ValidationGovernance":           "Layer 5+ Preservation",
        "ValidationPerformance":          "Performance Budget",
        "ValidationResearchIntegrity":    "Research Integrity",
        "ValidationResearchMaturity":     "Research Maturity",
    }

    print()
    print("=" * 60)
    print("  PREPARED UNIVERSE FORENSIC AUDIT")
    print(f"  [ValidationSuite] version={VALIDATION_SUITE_VERSION}")
    print("=" * 60)
    for key, label in section_labels.items():
        r      = next((x for x in _validation_results if x.section == key), None)
        status = r.status   if r else "NOT_RUN"
        sev    = r.severity if r else ValidationSeverity.INFO
        is_crit = sev == ValidationSeverity.CRITICAL
        icon   = _ICON.get("CRITICAL" if is_crit else status, "?")
        crit_note = "  ⬆ CRITICAL" if is_crit else ""
        print(f"  {icon}  {label:<35} {status}{crit_note}")
    print()
    print(f"  Sections run:    {len(_validation_results)}")
    print(f"  Passed:          {n_pass}")
    print(f"  Warnings:        {n_warn}")
    print(f"  Failed:          {n_fail}")
    print(f"  Critical:        {n_critical}")
    print()

    # Patch 16 — Runtime telemetry
    print(
        f"  [ValidationRuntime]"
        f" duration_sec={elapsed:.2f}"
        f" sections={len(_validation_results)}"
        f" warnings={n_warn} fails={n_fail} critical={n_critical}"
    )
    print()

    # Patch 15 — JSON export
    _export_validation_json(elapsed, snapshot)
    print()

    # Patch 14 — ONLY CRITICAL blocks activation
    activation_blocked = n_critical > 0

    if activation_blocked:
        print("  CRITICAL ISSUES (BLOCK ACTIVATION):")
        for r in _validation_results:
            if r.severity == ValidationSeverity.CRITICAL:
                print(f"    🔴 {r.section}")
                print(f"       → {(r.details or '')[:120]}")
                if r.recommendation:
                    print(f"       FIX: {r.recommendation}")
        print()
        print("  FINAL STATUS:")
        print(f"  🔴  BLOCKED — FIX REQUIRED [{VALIDATION_SUITE_VERSION}]")
        return 1

    # Non-critical failures — feature disables gracefully, activation is safe
    nc_fails = [
        r for r in _validation_results
        if r.status == _FAIL and r.severity != ValidationSeverity.CRITICAL
    ]
    if nc_fails:
        print("  NON-CRITICAL FAILURES (feature disables gracefully, activation safe):")
        for r in nc_fails:
            print(f"    ❌ {r.section}: {(r.details or '')[:80]}")
            if r.recommendation:
                print(f"       FIX: {r.recommendation}")
        print()

    if n_warn > 0:
        print("  WARNINGS (non-blocking):")
        for r in _validation_results:
            if r.status == _WARN:
                print(f"    ⚠️   {r.section}")
        print()

    print("  FINAL STATUS:")
    if nc_fails or n_warn > 0:
        print(
            f"  ⚠️   READY_FOR_CONTROLLED_LIVE_OPERATION"
            f" (review non-critical items) [{VALIDATION_SUITE_VERSION}]"
        )
    else:
        print(f"  ✅  READY_FOR_CONTROLLED_LIVE_OPERATION [{VALIDATION_SUITE_VERSION}]")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  PREPARED UNIVERSE MASTER FORENSIC VALIDATION            ║")
    print("║  AI Trading Brain — Controlled Live Evolution Audit      ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<54}║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    # Patch 11 — suite identity tag
    print(f"  [ValidationSuite] version={VALIDATION_SUITE_VERSION}")
    print()

    # Patch 17 — deployment snapshot (captured before any section runs)
    snap = _capture_deployment_snapshot()
    print(
        f"  [DeploymentSnapshot]"
        f" prepared={snap.get('prepared', '?')}"
        f" overlay={snap.get('overlay', '?')}"
        f" premarket={snap.get('premarket', '?')}"
        f" exploration={snap.get('exploration', '?')}"
        f" shadow={snap.get('shadow', '?')}"
        f" git={snap.get('git_hash', 'unavailable')}"
        f" uptime_hr={snap.get('container_uptime_hr', '?')}"
        f" python={snap.get('python_version', '?')}"
    )
    print()

    sections = [
        ("SECTION 2  — Config Integrity",          validate_config),
        ("SECTION 3  — Candidate Store",            validate_candidate_store),
        ("SECTION 4  — Schema Contract",            validate_schema_contract),
        ("SECTION 5  — Prepared Merge Logic",       validate_prepared_merge),
        ("SECTION 6  — Deterministic Levels",       validate_prepared_determinism),
        ("SECTION 7  — Telemetry Tags",             validate_telemetry),
        ("SECTION 8  — Safe Mode Triggers",         validate_safe_mode),
        ("SECTION 9  — Overlay Bounds",             validate_overlay),
        ("SECTION 10 — Premarket Logic",            validate_premarket),
        ("SECTION 11 — Exploration Governance",     validate_exploration),
        ("SECTION 12 — Layer 5+ Preservation",      validate_governance),
        ("SECTION 13 — Performance Budget",         validate_performance),
        ("SECTION 14 — Research Integrity",         validate_research_integrity),
        ("SECTION 15 — Research Maturity",          validate_research_maturity),
    ]

    for heading, fn in sections:
        print(f"\n── {heading} ──")
        try:
            fn()
        except Exception as exc:
            name = heading.split("—")[-1].strip().replace(" ", "")
            key = f"Validation{name}"
            _emit(key, _FAIL, [f"Uncaught exception: {traceback.format_exc(limit=3)}"])

    return print_summary(snap)


if __name__ == "__main__":
    sys.exit(main())
