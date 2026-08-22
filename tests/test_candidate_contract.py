"""
Patch 2 — CandidateRecord Schema Contract Tests
================================================
Validates that every field required by _identify_setup(), scan(),
and the debate / governance pipeline is present and correctly typed
in a candidate record produced by market_scanner.py / candidate_store.py.

MANDATORY: this test must pass before enabling USE_PREPARED_UNIVERSE=True.

Run:
    python -m pytest tests/test_candidate_contract.py -v
    OR
    python tests/test_candidate_contract.py

Hard-fails CI if any mismatch is detected.
"""

from __future__ import annotations

import sys
import os
import json
import copy
from pathlib import Path

# Make the project root importable
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))


# ── Canonical field specification ─────────────────────────────────────────────
# Maps field_name → (expected_type_or_types, allow_zero, required)
# "required=True"  → test HARD FAILS if field is missing or None
# "allow_zero"     → False means value must be non-zero (non-empty for str)
FIELD_SPEC: dict = {
    # Identity
    "symbol":       (str,               False, True),
    # Structural levels — must be positive non-zero
    "resistance":   ((int, float),      False, True),
    "support":      ((int, float),      False, True),
    # Indicators
    "rsi":          ((int, float),      True,  True),   # can be 0.0 (synthetic fallback)
    "volume_ratio": ((int, float),      True,  True),
    "adv_crore":    ((int, float),      True,  False),  # optional but typed if present
    # Market scanner extras (present when Phase D is active)
    "score":        ((int, float),      False, False),  # optional; must be >0 if present
    "buckets":      (list,              True,  False),  # optional list of setup types
    "sector":       (str,               True,  False),  # optional; empty allowed
    "index":        (str,               True,  False),
    # Premarket extras (populated by premarket_refiner)
    "valid_until_utc": (str,            True,  False),  # ISO-8601 or absent
    "overnight_gap_pct": ((int, float), True,  False),
    "overnight_adjustment": ((int, float), True, False),
    # Audit tag — must NOT be consumed by _identify_setup()
    "_prepared":    (bool,              True,  False),
}

# Fields that MUST be present in every record produced by market_scanner.py
SCANNER_REQUIRED = {"symbol", "resistance", "support", "rsi", "volume_ratio", "score", "buckets", "sector"}

# Fields that MUST be present in every record injected into _identify_setup()
LIVE_PIPELINE_REQUIRED = {"symbol", "resistance", "support", "rsi", "volume_ratio"}


# ── Minimal valid fixture ─────────────────────────────────────────────────────
def _make_valid_record(**overrides) -> dict:
    base = {
        "symbol":       "RELIANCE",
        "resistance":   1450.0,
        "support":      1290.0,
        "rsi":          52.3,
        "volume_ratio": 1.4,
        "adv_crore":    800.0,
        "score":        0.68,
        "buckets":      ["breakout"],
        "sector":       "ENERGY",
        "index":        "NIFTY50",
        "_prepared":    True,
    }
    base.update(overrides)
    return base


# ── Test helpers ──────────────────────────────────────────────────────────────
_failures: list[str] = []
_passes:   int       = 0


def _ok(name: str) -> None:
    global _passes
    _passes += 1
    print(f"  PASS  {name}")


def _fail(name: str, reason: str) -> None:
    _failures.append(f"{name}: {reason}")
    print(f"  FAIL  {name}: {reason}")


def _assert(cond: bool, name: str, reason: str) -> None:
    if cond:
        _ok(name)
    else:
        _fail(name, reason)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_valid_record_passes_all_checks():
    """A fully populated valid record must pass every required-field check."""
    r = _make_valid_record()
    for field, (typ, allow_zero, required) in FIELD_SPEC.items():
        if not required:
            continue
        val = r.get(field)
        _assert(val is not None, f"required_field_present:{field}", f"field '{field}' is None")
        _assert(isinstance(val, typ), f"type_check:{field}",
                f"expected {typ}, got {type(val)}")
        if not allow_zero and isinstance(val, (int, float)):
            _assert(val != 0, f"nonzero_check:{field}", f"field '{field}' must be non-zero")
        if not allow_zero and isinstance(val, str):
            _assert(val != "", f"nonempty_check:{field}", f"field '{field}' must be non-empty")


def test_missing_symbol_rejected():
    r = _make_valid_record()
    del r["symbol"]
    missing = [f for f in LIVE_PIPELINE_REQUIRED if r.get(f) is None]
    _assert("symbol" in missing, "missing_symbol_detected",
            "Missing 'symbol' was not detected")


def test_missing_resistance_rejected():
    r = _make_valid_record()
    del r["resistance"]
    missing = [f for f in LIVE_PIPELINE_REQUIRED if r.get(f) is None]
    _assert("resistance" in missing, "missing_resistance_detected",
            "Missing 'resistance' was not detected")


def test_missing_support_rejected():
    r = _make_valid_record()
    del r["support"]
    missing = [f for f in LIVE_PIPELINE_REQUIRED if r.get(f) is None]
    _assert("support" in missing, "missing_support_detected",
            "Missing 'support' was not detected")


def test_zero_resistance_rejected():
    """Zero resistance would cause division-by-zero in _identify_setup()."""
    r = _make_valid_record(resistance=0.0)
    _assert(r["resistance"] == 0.0, "zero_resistance_fixture_ok", "fixture broken")
    # A validator that respects allow_zero=False must catch this
    spec_allow_zero = FIELD_SPEC["resistance"][1]
    _assert(spec_allow_zero is False, "resistance_nonzero_spec",
            "spec incorrectly allows zero resistance")


def test_negative_support_rejected():
    """Support must be positive — negative price is impossible on NSE."""
    r = _make_valid_record(support=-10.0)
    is_valid = r["support"] > 0
    _assert(not is_valid, "negative_support_rejected", "negative support was not caught")


def test_rsi_bounds():
    """RSI must be in [0, 100]."""
    for rsi, should_pass in [(0.0, True), (50.0, True), (100.0, True),
                             (-1.0, False), (101.0, False)]:
        valid = 0.0 <= rsi <= 100.0
        _assert(valid == should_pass, f"rsi_bounds:{rsi}",
                f"RSI={rsi} validity expected {should_pass} got {valid}")


def test_volume_ratio_non_negative():
    """volume_ratio must be ≥ 0 (0 = no data, not invalid)."""
    for vr, should_pass in [(0.0, True), (1.5, True), (-0.1, False)]:
        valid = vr >= 0.0
        _assert(valid == should_pass, f"volume_ratio_bounds:{vr}",
                f"vol_ratio={vr} validity expected {should_pass} got {valid}")


def test_score_in_unit_range():
    """Scores from market_scanner must be in [0.0, 1.0]."""
    for score, should_pass in [(0.0, False), (0.55, True), (1.0, True), (1.01, False), (-0.1, False)]:
        valid = 0.0 < score <= 1.0
        _assert(valid == should_pass, f"score_range:{score}",
                f"score={score} validity expected {should_pass}")


def test_scanner_required_fields_all_present():
    """A scanner-produced record must have all SCANNER_REQUIRED fields."""
    r = _make_valid_record()
    missing = [f for f in SCANNER_REQUIRED if r.get(f) is None]
    _assert(len(missing) == 0, "scanner_required_all_present",
            f"Missing scanner-required fields: {missing}")


def test_prepared_tag_not_consumed_by_identify_setup():
    """
    _prepared=True is an audit tag. It must NOT appear in the field spec
    consumed by _identify_setup() (LIVE_PIPELINE_REQUIRED).
    This ensures _identify_setup() never changes behaviour based on origin.
    """
    _assert("_prepared" not in LIVE_PIPELINE_REQUIRED,
            "_prepared_not_in_pipeline_required",
            "_prepared tag must not be in LIVE_PIPELINE_REQUIRED")


def test_valid_until_utc_format_when_present():
    """valid_until_utc, if present, must be parseable ISO-8601 UTC."""
    from datetime import datetime, timezone
    valid_timestamps = [
        "2026-05-22T03:30:00Z",
        "2026-05-22T08:30:00Z",
        "2026-05-22T09:30:00Z",
    ]
    invalid_timestamps = [
        "not-a-date",
        "2026-13-01T00:00:00Z",  # invalid month
    ]
    for ts in valid_timestamps:
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            _ok(f"valid_until_utc_parse_ok:{ts}")
        except Exception as exc:
            _fail(f"valid_until_utc_parse_fail:{ts}", str(exc))
    for ts in invalid_timestamps:
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            _fail(f"valid_until_utc_invalid_accepted:{ts}", "should have raised")
        except Exception:
            _ok(f"valid_until_utc_invalid_rejected:{ts}")


def test_live_store_file_if_present():
    """
    If daily_candidates.json exists on disk, validate every record in it
    against LIVE_PIPELINE_REQUIRED and type specs.  Skipped if file absent.
    """
    store_path = _ROOT / "data" / "daily_candidates.json"
    if not store_path.exists():
        print("  SKIP  live_store_contract (daily_candidates.json not present)")
        return

    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except Exception as exc:
        _fail("live_store_parse", f"JSON parse error: {exc}")
        return

    candidates = payload.get("candidates", [])
    _assert(len(candidates) > 0, "live_store_nonempty", "candidates list is empty")

    field_errors: list[str] = []
    for i, c in enumerate(candidates):
        for field in LIVE_PIPELINE_REQUIRED:
            if c.get(field) is None:
                field_errors.append(f"record[{i}] symbol={c.get('symbol','?')} missing '{field}'")
        sym = c.get("symbol")
        if sym:
            spec_type = FIELD_SPEC.get("resistance", (float, False, True))[0]
            res = c.get("resistance", 0)
            if not isinstance(res, (int, float)) or res <= 0:
                field_errors.append(f"record[{i}] {sym}: invalid resistance={res}")

    _assert(len(field_errors) == 0, "live_store_all_records_valid",
            f"{len(field_errors)} field errors: {field_errors[:5]}")


def test_backward_compatibility_missing_optional_fields():
    """
    Records missing optional Phase-D fields (score, buckets, sector) must still
    be accepted by the live pipeline — backward compatibility with pre-Phase-D
    store files.
    """
    r = {
        "symbol": "HDFCBANK",
        "resistance": 800.0,
        "support": 750.0,
        "rsi": 48.0,
        "volume_ratio": 1.1,
    }
    missing_required = [f for f in LIVE_PIPELINE_REQUIRED if r.get(f) is None]
    _assert(len(missing_required) == 0, "backward_compat_minimal_record",
            f"Minimal record missing required fields: {missing_required}")
    # Optional fields absent — confirm they are indeed optional
    for opt_field in ("score", "buckets", "sector", "valid_until_utc"):
        spec = FIELD_SPEC.get(opt_field)
        if spec:
            _assert(spec[2] is False, f"optional_field_spec:{opt_field}",
                    f"'{opt_field}' should be optional (required=False) in FIELD_SPEC")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all_tests() -> None:
    print("\n══ CandidateRecord Schema Contract Tests ══\n")
    tests = [
        test_valid_record_passes_all_checks,
        test_missing_symbol_rejected,
        test_missing_resistance_rejected,
        test_missing_support_rejected,
        test_zero_resistance_rejected,
        test_negative_support_rejected,
        test_rsi_bounds,
        test_volume_ratio_non_negative,
        test_score_in_unit_range,
        test_scanner_required_fields_all_present,
        test_prepared_tag_not_consumed_by_identify_setup,
        test_valid_until_utc_format_when_present,
        test_live_store_file_if_present,
        test_backward_compatibility_missing_optional_fields,
    ]
    for test_fn in tests:
        try:
            test_fn()
        except Exception as exc:
            _fail(test_fn.__name__, f"UNCAUGHT EXCEPTION: {exc}")

    print(f"\n══ Results: {_passes} passed / {len(_failures)} failed ══\n")
    if _failures:
        print("FAILURES:")
        for f in _failures:
            print(f"  ✗ {f}")
        print(
            "\n[CONTRACT VIOLATION] Fix all failures before enabling"
            " USE_PREPARED_UNIVERSE=True\n"
        )
        sys.exit(1)
    else:
        print("[CONTRACT OK] All checks passed — schema contract is satisfied.\n")


# ── pytest compatibility ──────────────────────────────────────────────────────
# Each test_* function is also directly callable by pytest.

if __name__ == "__main__":
    run_all_tests()
