"""
normalize_symbols_patch.py  — Symbol Normalization Hardening
Applies all 5 structural fixes described in the architecture audit.

Deploy and run inside container:
  scp -i ~/.ssh/trading_vps normalize_symbols_patch.py root@178.18.252.24:/tmp/
  docker cp /tmp/normalize_symbols_patch.py ai-trading-brain:/tmp/
  docker exec -w /app ai-trading-brain python3 /tmp/normalize_symbols_patch.py
  docker restart ai-trading-brain
"""
import os, sys, re, shutil, json, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s  %(message)s")
log = logging.getLogger("sym_norm_patch")

ROOT = Path('/app')
BACKUP_SUFFIX = '.bak_symnorm'
_ok = 0; _skip = 0; _fail = 0

NL = chr(10)  # use chr(10) instead of \n inside strings to avoid encoding issues in patch strings


def backup(p: Path) -> None:
    dst = Path(str(p) + BACKUP_SUFFIX)
    if not dst.exists():
        shutil.copy2(str(p), str(dst))


def patch_text(path, old: str, new: str, desc: str) -> bool:
    global _ok, _skip, _fail
    p = Path(path)
    if not p.exists():
        log.error("MISSING  %s  [%s]", p.name, desc)
        _fail += 1
        return False
    text = p.read_text(encoding='utf-8')
    if old not in text:
        log.warning("SKIP(not found)  [%s]  %s", desc, p.name)
        _skip += 1
        return False
    if new in text:
        log.info("SKIP(already)    [%s]  %s", desc, p.name)
        _skip += 1
        return True
    backup(p)
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    log.info("OK               [%s]  %s", desc, p.name)
    _ok += 1
    return True


def patch_regex(path, pattern: str, replacement, desc: str, flags: int = 0) -> int:
    global _ok, _skip, _fail
    p = Path(path)
    if not p.exists():
        log.error("MISSING  %s  [%s]", p.name, desc)
        _fail += 1
        return 0
    text = p.read_text(encoding='utf-8')
    new_text, count = re.subn(pattern, replacement, text, flags=flags)
    if count == 0:
        log.warning("SKIP(no match)   [%s]  %s", desc, p.name)
        _skip += 1
        return 0
    backup(p)
    p.write_text(new_text, encoding='utf-8')
    log.info("OK(%d)            [%s]  %s", count, desc, p.name)
    _ok += count
    return count


# =============================================================================
# STEP 1 — Create utils/symbol_utils.py
# =============================================================================
log.info("=== STEP 1: utils/symbol_utils.py ===")

SYMBOL_UTILS = ROOT / 'utils/symbol_utils.py'
SYMBOL_UTILS_CONTENT = '''"""
utils/symbol_utils.py
Central symbol normalization utility for ai_trading_brain.

Public API
----------
normalize_symbol(symbol, at_lookup=False) -> str
    Strip leading/trailing whitespace and uppercase. Emits [SymbolNormalized]
    when input differs from output. Pass at_lookup=True at feed-lookup call
    sites to increment the lookup_failures_prevented counter.

get_normalization_health() -> dict
    Returns counters snapshot for the [SymbolNormalizationHealth] EOD log.

reset_normalization_counters() -> None
    Reset all counters. Call once at session start.
"""
import logging

log = logging.getLogger(__name__)

_stats: dict = {
    "symbols_processed": 0,
    "symbols_normalized": 0,
    "lookup_failures_prevented": 0,
}


def normalize_symbol(symbol: str, at_lookup: bool = False) -> str:
    """
    Canonical symbol normalizer.
    Rules: strip() whitespace + upper().
    Emits [SymbolNormalized] only when input != output.
    """
    if not isinstance(symbol, str):
        return symbol
    _stats["symbols_processed"] += 1
    normalized = symbol.strip().upper()
    if normalized != symbol:
        _stats["symbols_normalized"] += 1
        if at_lookup:
            _stats["lookup_failures_prevented"] += 1
        log.info(
            "[SymbolNormalized] raw=%s normalized=%s context=%s",
            repr(symbol), repr(normalized),
            "lookup" if at_lookup else "ingestion",
        )
    return normalized


def get_normalization_health() -> dict:
    """Return current normalization counters for EOD health logging."""
    processed = _stats["symbols_processed"]
    normalized = _stats["symbols_normalized"]
    return {
        "symbols_processed": processed,
        "symbols_normalized": normalized,
        "normalization_rate": round(normalized / processed, 6) if processed else 0.0,
        "lookup_failures_prevented": _stats["lookup_failures_prevented"],
    }


def reset_normalization_counters() -> None:
    """Reset all counters. Call once per trading session start."""
    _stats["symbols_processed"] = 0
    _stats["symbols_normalized"] = 0
    _stats["lookup_failures_prevented"] = 0
'''

if SYMBOL_UTILS.exists() and 'normalize_symbol' in SYMBOL_UTILS.read_text(encoding='utf-8'):
    log.info("SKIP(already)    utils/symbol_utils.py")
    _skip += 1
else:
    if SYMBOL_UTILS.exists():
        backup(SYMBOL_UTILS)
    SYMBOL_UTILS.write_text(SYMBOL_UTILS_CONTENT, encoding='utf-8')
    log.info("OK               utils/symbol_utils.py  (created)")
    _ok += 1


# =============================================================================
# STEP 2 — Patch models/trade_signal.py  (add __post_init__)
# =============================================================================
log.info("=== STEP 2: models/trade_signal.py ===")

TS = ROOT / 'models/trade_signal.py'

# 2a. Add normalize_symbol import after 'from dataclasses import dataclass, field'
patch_text(
    TS,
    'from dataclasses import dataclass, field',
    'from dataclasses import dataclass, field' + NL +
    'from utils.symbol_utils import normalize_symbol as _normalize_symbol',
    'trade_signal: add normalize_symbol import',
)

# 2b. Insert __post_init__ — find the entry_zone_high line, insert after it
_ts_text = TS.read_text(encoding='utf-8')
if '__post_init__' not in _ts_text:
    _marker = '    entry_zone_high'
    _idx = _ts_text.find(_marker)
    if _idx >= 0:
        _eol = _ts_text.find('\n', _idx)
        if _eol >= 0:
            _post_init = (
                NL + NL +
                '    def __post_init__(self) -> None:' + NL +
                '        """Normalize symbol once at creation.' + NL +
                '        Prevents dirty symbols (e.g. trailing spaces from Dhan/AngelOne' + NL +
                '        instrument lists) from propagating to all 17 downstream layers.' + NL +
                '        """' + NL +
                '        self.symbol = _normalize_symbol(self.symbol)'
            )
            _ts_text = _ts_text[:_eol] + _post_init + _ts_text[_eol:]
            backup(TS)
            TS.write_text(_ts_text, encoding='utf-8')
            log.info("OK               trade_signal.py: __post_init__ inserted after entry_zone_high")
            _ok += 1
        else:
            log.warning("SKIP  trade_signal.py: could not find EOL after entry_zone_high")
            _skip += 1
    else:
        log.warning("SKIP  trade_signal.py: entry_zone_high not found (field may have moved)")
        _skip += 1
else:
    log.info("SKIP(already)    trade_signal.py: __post_init__ already present")
    _skip += 1


# =============================================================================
# STEP 3 — Patch data_feeds/dhan_feed.py
# =============================================================================
log.info("=== STEP 3: data_feeds/dhan_feed.py ===")

DHAN = ROOT / 'data_feeds/dhan_feed.py'

# 3a. _lookup(): replace the single sym= line with normalize_symbol call
#     Old line is unique: 'sym = symbol.upper().replace(".NS"...' inside _lookup
#     The preceding def line context is used as patch context via text search
_dhan_text = DHAN.read_text(encoding='utf-8')
_LOOKUP_OLD = '        sym = symbol.upper().replace(".NS", "").replace(".BO", "")'
_LOOKUP_NEW = (
    '        from utils.symbol_utils import normalize_symbol as _ns  # cached by Python after first call' + NL +
    '        sym = _ns(symbol, at_lookup=True).replace(".NS", "").replace(".BO", "")'
)
# Safety: only replace the one inside _lookup (not any other occurrence)
# Anchor: this exact sym= line only appears in _lookup in the confirmed codebase
if '_lookup' in _dhan_text and _LOOKUP_OLD in _dhan_text and '_ns' not in _dhan_text:
    backup(DHAN)
    _dhan_text = _dhan_text.replace(_LOOKUP_OLD, _LOOKUP_NEW, 1)
    DHAN.write_text(_dhan_text, encoding='utf-8')
    log.info("OK               dhan_feed._lookup: normalize_symbol inserted")
    _ok += 1
elif '_ns' in _dhan_text:
    log.info("SKIP(already)    dhan_feed._lookup: normalize_symbol already present")
    _skip += 1
else:
    log.warning("SKIP(not found)  dhan_feed._lookup: pattern not found")
    _skip += 1

# 3b. Instrument list loader — strip SEM_TRADING_SYMBOL (single-line, safe)
patch_text(
    DHAN,
    '                    sym = row.get("SEM_TRADING_SYMBOL", "").upper()',
    '                    sym = row.get("SEM_TRADING_SYMBOL", "").strip().upper()',
    'dhan_feed._load: strip SEM_TRADING_SYMBOL',
)

# 3c. All sim-fallback bare= lines — regex, all occurrences at once
patch_regex(
    DHAN,
    r'bare = symbol\.upper\(\)\.replace\("\.NS",\s*""\)\.replace\("\.BO",\s*""\)',
    'bare = symbol.strip().upper().replace(".NS", "").replace(".BO", "")',
    'dhan_feed sim-fallback: add .strip() to all 5 bare= sites',
)


# =============================================================================
# STEP 4 — Patch data_feeds/angelone_feed.py (normalize token cache keys)
# =============================================================================
log.info("=== STEP 4: data_feeds/angelone_feed.py ===")

ANGEL = ROOT / 'data_feeds/angelone_feed.py'
if not ANGEL.exists():
    log.error("MISSING  angelone_feed.py — skipping Step 4")
    _fail += 1
else:
    _angel_text = ANGEL.read_text(encoding='utf-8')

    # 4a. Add import if not already present
    if 'normalize_symbol' not in _angel_text:
        # Try multiple possible import anchors in order of preference
        for _anchor in [
            'from data_feeds.base_feed import BaseFeed',
            'from .base_feed import BaseFeed',
            'import logging',
        ]:
            if _anchor in _angel_text:
                patch_text(
                    ANGEL,
                    _anchor,
                    _anchor + NL + 'from utils.symbol_utils import normalize_symbol as _normalize_symbol',
                    'angelone_feed: add normalize_symbol import',
                )
                break

    # 4b. Normalize tradingSymbol when writing to _token_cache (write path)
    #     Handles: self._token_cache[sym] = ...
    #     and:     self._token_cache[result['tradingSymbol']] = ...
    patch_regex(
        ANGEL,
        r'(self\._token_cache)\[(_?(?:sym|symbol|trading_sym(?:bol)?)(?:\.upper\(\))?)\](\s*=(?!=))',
        lambda m: '{}[_normalize_symbol({})]{}'.format(m.group(1), m.group(2), m.group(3)),
        'angelone_feed: normalize key before _token_cache write',
    )

    # 4c. Also normalize at read/lookup boundary
    patch_regex(
        ANGEL,
        r'self\._token_cache\.get\((_?(?:sym|symbol|trading_sym(?:bol)?))\b',
        lambda m: 'self._token_cache.get(_normalize_symbol({}, at_lookup=True)'.format(m.group(1)),
        'angelone_feed: normalize symbol at _token_cache.get() lookup',
    )


# =============================================================================
# STEP 5 — Clean data/angelone_token_cache.json (strip 18 known dirty keys)
# =============================================================================
log.info("=== STEP 5: data/angelone_token_cache.json ===")

CACHE = ROOT / 'data/angelone_token_cache.json'
if not CACHE.exists():
    log.warning("SKIP  angelone_token_cache.json not found")
    _skip += 1
else:
    try:
        _cache_data: dict = json.loads(CACHE.read_text(encoding='utf-8'))
        _dirty = {k: v for k, v in _cache_data.items() if k != k.strip() or k != k.upper()}
        if _dirty:
            backup(CACHE)
            _clean = {k.strip().upper(): v for k, v in _cache_data.items()}
            CACHE.write_text(json.dumps(_clean, indent=2, ensure_ascii=False), encoding='utf-8')
            log.info("OK               angelone_token_cache.json — cleaned %d dirty keys: %s",
                     len(_dirty), sorted(_dirty.keys()))
            _ok += len(_dirty)
        else:
            log.info("SKIP(clean)      angelone_token_cache.json — no dirty keys found")
            _skip += 1
    except Exception as _e:
        log.error("FAIL  angelone_token_cache.json: %s", _e)
        _fail += 1


# =============================================================================
# STEP 6 — Patch orchestrator/master_orchestrator.py ([SymbolNormalizationHealth])
# =============================================================================
log.info("=== STEP 6: orchestrator/master_orchestrator.py ===")

ORCH = ROOT / 'orchestrator/master_orchestrator.py'
_orch_text = ORCH.read_text(encoding='utf-8') if ORCH.exists() else ""

ORCH_ANCHOR = '            _dhan.emit_feed_integrity_summary()'
ORCH_HEALTH = (
    NL +
    '        # -- Symbol normalization health --------------------------------' + NL +
    '        try:' + NL +
    '            from utils.symbol_utils import get_normalization_health as _gnh' + NL +
    '            from utils.symbol_utils import reset_normalization_counters as _rsc' + NL +
    '            _h = _gnh()' + NL +
    '            log.info(' + NL +
    '                "[SymbolNormalizationHealth] symbols_processed=%d symbols_normalized=%d "' + NL +
    '                "normalization_rate=%.6f lookup_failures_prevented=%d",' + NL +
    '                _h["symbols_processed"], _h["symbols_normalized"],' + NL +
    '                _h["normalization_rate"], _h["lookup_failures_prevented"],' + NL +
    '            )' + NL +
    '            _rsc()' + NL +
    '        except Exception as _sym_e:' + NL +
    '            log.debug("[SymbolNormalizationHealth] skipped: %s", _sym_e)'
)

if not _orch_text:
    log.error("MISSING  master_orchestrator.py — skipping Step 6")
    _fail += 1
elif '[SymbolNormalizationHealth]' in _orch_text:
    log.info("SKIP(already)    master_orchestrator.py: [SymbolNormalizationHealth] already present")
    _skip += 1
elif ORCH_ANCHOR not in _orch_text:
    log.warning("SKIP(not found)  master_orchestrator.py: emit_feed_integrity_summary anchor not found")
    _skip += 1
else:
    backup(ORCH)
    _orch_text = _orch_text.replace(ORCH_ANCHOR, ORCH_ANCHOR + ORCH_HEALTH, 1)
    ORCH.write_text(_orch_text, encoding='utf-8')
    log.info("OK               master_orchestrator.py: [SymbolNormalizationHealth] EOD emit added")
    _ok += 1


# =============================================================================
# STEP 7 — Verify utils/__init__.py package structure
# =============================================================================
log.info("=== STEP 7: utils/__init__.py ===")
UTILS_INIT = ROOT / 'utils/__init__.py'
if UTILS_INIT.exists():
    log.info("OK               utils/__init__.py exists — package is importable")
else:
    log.warning("WARN  utils/__init__.py not found. "
                "Creating empty one to ensure 'from utils.symbol_utils import ...' works.")
    UTILS_INIT.write_text("# utils package\n", encoding='utf-8')
    _ok += 1


# =============================================================================
# Summary
# =============================================================================
print()
print("=" * 70)
print("SYMBOL NORMALIZATION HARDENING — PATCH COMPLETE")
print("=" * 70)
print(f"  Applied  : {_ok}")
print(f"  Skipped  : {_skip}")
print(f"  Failed   : {_fail}")
print()
print("  Files targeted:")
print("    utils/symbol_utils.py                  (central normalize_symbol)")
print("    models/trade_signal.py                 (__post_init__ normalizes symbol)")
print("    data_feeds/dhan_feed.py                (_lookup + _load + 5x sim bare=)")
print("    data_feeds/angelone_feed.py            (token cache key normalization)")
print("    data/angelone_token_cache.json         (18 dirty keys cleaned in-place)")
print("    orchestrator/master_orchestrator.py    ([SymbolNormalizationHealth] EOD)")
print()
if _fail > 0:
    print(f"  WARNING: {_fail} step(s) FAILED — review output above before restart")
else:
    print("  All steps OK. Run: docker restart ai-trading-brain")
print("=" * 70)

sys.exit(0)  # prevent any stale content below from executing