import sys, os
sys.path.insert(0, "/app")
os.chdir("/app")

errors = []

# Audit 1: FilterFunnelAudit
try:
    from opportunity_engine.filter_funnel_audit import get_filter_funnel_audit, SCANNER_STAGES
    ffa = get_filter_funnel_audit()
    assert hasattr(ffa, "record_scanner_stage"), "missing record_scanner_stage"
    assert hasattr(ffa, "emit_funnelcompression"), "missing emit_funnelcompression"
    assert "sector_cap_removed" in SCANNER_STAGES, "missing sector_cap_removed"
    assert "score_floor_removed" in SCANNER_STAGES, "missing score_floor_removed"
    # Test record_scanner_stage call
    ffa.record_scanner_stage(symbols_attempted=230, data_ok=165, after_sector_cap=120, after_score_floor=59)
    print("[Audit1] FilterFunnelAudit OK — SCANNER_STAGES:", SCANNER_STAGES)
except Exception as e:
    errors.append(f"[Audit1] FAIL: {e}")

# Audit 2: ScalarAudit
try:
    import inspect
    from utils.scalar_audit import get_scalar_audit
    a = get_scalar_audit()
    sig = inspect.signature(a.record_coercion)
    params = list(sig.parameters.keys())
    for p in ("file_ctx", "method_ctx", "shape_info", "exc_type"):
        assert p in params, f"missing param {p}"
    print("[Audit2] scalar_audit.record_coercion params:", params)
except Exception as e:
    errors.append(f"[Audit2] scalar_audit FAIL: {e}")

try:
    from utils.safe_scalar import safe_scalar, _caller_ctx
    import pandas as pd
    s = pd.Series([42.5, 43.0])
    result = safe_scalar(s, name="TEST.close")
    assert result == 43.0, f"expected 43.0 got {result}"
    print("[Audit2] safe_scalar Series coercion OK, result:", result)
except Exception as e:
    errors.append(f"[Audit2] safe_scalar FAIL: {e}")

# Audit 3: market_scanner freshness function
try:
    from opportunity_engine.market_scanner import _emit_freshness_validation
    cands = [
        {"symbol": "RELIANCE", "freshness_age_minutes": 0,
         "last_refresh_time": "2026-06-01T10:00:00+00:00",
         "valid_until_utc":   "2026-06-01T10:00:00+00:00",
         "prepared_at": "2026-06-01T09:00:00+00:00"},
    ]
    _emit_freshness_validation(cands)
    print("[Audit3] _emit_freshness_validation OK")
except Exception as e:
    errors.append(f"[Audit3] FAIL: {e}")

if errors:
    print("\nFAILED:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
else:
    print("\nALL AUDITS PASSED")
