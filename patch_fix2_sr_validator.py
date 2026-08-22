"""
Fix 2: Add validate_and_refresh_sr_levels() to equity_scanner_ai.py.

This function:
  1. Fetches current LTPs for all watchlist symbols (yfinance batch call)
  2. Detects any entry where resistance <= LTP or support >= LTP
  3. For each broken entry: downloads 30d history, computes ATR(14),
     rebuilds resistance/support at LTP ± 2×ATR
  4. Rewrites _BASE_WATCHLIST and _EXTENDED_WATCHLIST in equity_scanner_ai.py in-place
  5. Updates the last_level_update date in the ScannerBaseline log line
  6. Returns a summary dict {repaired: int, total: int, broken_symbols: list}

Called from orchestrator._premarket_init() at 08:00 each trading day.
"""

SCANNER = "/app/opportunity_engine/equity_scanner_ai.py"

with open(SCANNER, "r") as f:
    src = f.read()

# Guard: don't double-patch
if "def validate_and_refresh_sr_levels" in src:
    print("Fix 2 already applied — skipping.")
    import sys; sys.exit(0)

NEW_FUNC = '''

# ── Fix 2: Pre-market S/R Level Validator ──────────────────────────────────
def validate_and_refresh_sr_levels() -> dict:
    """
    Validate all watchlist S/R levels against current LTPs and auto-repair
    any broken entries (resistance < LTP or support > LTP).

    Returns dict: {repaired: int, total: int, broken_symbols: list, error: str|None}
    Called by orchestrator._premarket_init() at 08:00 each trading day.
    """
    import yfinance as _yf
    import re as _re
    from datetime import date as _date, datetime as _datetime
    from pathlib import Path as _Path

    _scanner_path = _Path(__file__)
    _log_prefix   = "[SR_Validator]"

    try:
        all_entries = _BASE_WATCHLIST + _EXTENDED_WATCHLIST
        symbols_ns  = [e["symbol"].strip() + ".NS" for e in all_entries]

        # Batch LTP fetch (single yfinance call)
        log.info("%s Fetching LTPs for %d watchlist symbols…", _log_prefix, len(all_entries))
        _data = _yf.download(
            " ".join(symbols_ns),
            period="2d", interval="1d",
            auto_adjust=True, progress=False, timeout=15,
        )
        if _data.empty:
            return {"repaired": 0, "total": len(all_entries), "broken_symbols": [], "error": "yfinance returned empty"}

        # Extract last close per symbol
        _ltps: dict = {}
        if isinstance(_data.columns, _pd_MultiIndex if hasattr(_data.columns, "levels") else type(None)):
            pass  # handled below

        try:
            import pandas as _pd
            if isinstance(_data.columns, _pd.MultiIndex):
                _close = _data["Close"]
                for ns_sym in symbols_ns:
                    if ns_sym in _close.columns:
                        _v = _close[ns_sym].dropna()
                        if not _v.empty:
                            _ltps[ns_sym.replace(".NS", "")] = float(_v.iloc[-1])
            else:
                _close = _data["Close"]
                _v = _close.dropna()
                if not _v.empty:
                    sym = symbols_ns[0].replace(".NS", "")
                    _ltps[sym] = float(_v.iloc[-1])
        except Exception as _pe:
            log.warning("%s LTP parse error: %s", _log_prefix, _pe)

        if not _ltps:
            return {"repaired": 0, "total": len(all_entries), "broken_symbols": [], "error": "no LTPs parsed"}

        # Detect broken entries
        _broken: list = []
        for entry in all_entries:
            sym   = entry["symbol"].strip()
            ltp   = _ltps.get(sym)
            if ltp is None:
                continue
            res = entry["resistance"]
            sup = entry["support"]
            if res <= ltp or sup >= ltp:
                _broken.append((sym, ltp, res, sup))

        if not _broken:
            log.info("%s All %d S/R levels valid — no repair needed.", _log_prefix, len(all_entries))
            return {"repaired": 0, "total": len(all_entries), "broken_symbols": [], "error": None}

        log.warning(
            "%s Found %d broken S/R entries: %s — rebuilding with ATR(14)…",
            _log_prefix, len(_broken), [b[0] for b in _broken],
        )

        # Rebuild ATR-anchored levels for broken symbols
        _new_levels: dict = {}  # symbol -> (resistance, support)
        for sym, ltp, _old_res, _old_sup in _broken:
            try:
                _hist = _yf.download(
                    sym + ".NS", period="30d", interval="1d",
                    auto_adjust=True, progress=False, timeout=12,
                )
                if _hist.empty or len(_hist) < 10:
                    log.warning("%s %s: insufficient history — skipping", _log_prefix, sym)
                    continue
                _hi  = _hist["High"].values
                _lo  = _hist["Low"].values
                _cl  = _hist["Close"].values
                _tr  = [max(_hi[i] - _lo[i],
                            abs(_hi[i] - _cl[i-1]),
                            abs(_lo[i] - _cl[i-1]))
                        for i in range(1, len(_cl))]
                _atr = sum(_tr[-14:]) / min(14, len(_tr))
                _new_res = round(ltp + 2.0 * _atr, 2)
                _new_sup = round(ltp - 2.0 * _atr, 2)
                _new_levels[sym] = (_new_res, _new_sup, round(ltp, 2))
                log.info(
                    "%s %s: LTP=%.2f ATR=%.2f → res=%.2f sup=%.2f",
                    _log_prefix, sym, ltp, _atr, _new_res, _new_sup,
                )
            except Exception as _exc:
                log.warning("%s %s rebuild failed: %s", _log_prefix, sym, _exc)

        if not _new_levels:
            return {
                "repaired": 0, "total": len(all_entries),
                "broken_symbols": [b[0] for b in _broken],
                "error": "all rebuilds failed",
            }

        # Patch the source file — replace individual lines matching each symbol
        _src = _scanner_path.read_text(encoding="utf-8")
        _repaired = 0
        for sym, (new_res, new_sup, new_ltp) in _new_levels.items():
            # Match lines like:  {"symbol": "RELIANCE    ", "base_ltp":..., "resistance":..., "support":...,...}
            _pattern = (
                r'(\{"symbol":\s*"' + _re.escape(sym) + r'\s*"'
                r',\s*"base_ltp":\s*)[\d.]+(\s*,\s*"resistance":\s*)[\d.]+'
                r'(\s*,\s*"support":\s*)[\d.]+'
            )
            _repl = (
                r'\g<1>' + f'{new_ltp:.2f}' +
                r'\g<2>' + f'{new_res:.2f}' +
                r'\g<3>' + f'{new_sup:.2f}'
            )
            _new_src, _count = _re.subn(_pattern, _repl, _src)
            if _count:
                _src  = _new_src
                _repaired += 1
            else:
                log.warning("%s Could not patch %s in source — regex miss", _log_prefix, sym)

        # Update last_level_update date
        _today = _date.today().isoformat()
        _src = _re.sub(
            r'last_level_update=\d{4}-\d{2}-\d{2}',
            f'last_level_update={_today}',
            _src,
        )

        _scanner_path.write_text(_src, encoding="utf-8")
        log.info(
            "%s Repair complete: %d/%d symbols patched. last_level_update=%s",
            _log_prefix, _repaired, len(_broken), _today,
        )
        return {
            "repaired": _repaired,
            "total": len(all_entries),
            "broken_symbols": [b[0] for b in _broken],
            "error": None,
        }

    except Exception as _exc:
        log.exception("%s Unexpected error: %s", _log_prefix, _exc)
        return {"repaired": 0, "total": 0, "broken_symbols": [], "error": str(_exc)}

'''

# Append to end of file
with open(SCANNER, "a") as f:
    f.write(NEW_FUNC)

print("Fix 2 applied: validate_and_refresh_sr_levels() added to equity_scanner_ai.py")

# Syntax check
import py_compile, tempfile, shutil, os
tmp = tempfile.mktemp(suffix=".py")
shutil.copy2(SCANNER, tmp)
try:
    py_compile.compile(tmp, doraise=True)
    print("Syntax check: PASSED")
except py_compile.PyCompileError as e:
    print(f"Syntax check: FAILED — {e}")
finally:
    os.unlink(tmp)
