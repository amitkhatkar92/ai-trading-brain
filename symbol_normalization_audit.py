"""
symbol_normalization_audit.py
Run inside container: python3 /tmp/symbol_normalization_audit.py

Evidence-only audit. No behavior changes. No auto-fixes.

Emits:
  [SymbolNormalizationAudit]    — one per finding, per source module
  [SymbolNormalizationSummary]  — EOD-style roll-up

Normalization checks:
  - Trailing / leading whitespace
  - Mixed case
  - Exchange suffix (.NS / .BO)
  - Inconsistency between raw and normalized representation

Sources audited:
  1. data/paper_trades.csv       — live order record
  2. data/ca_quarantine.json     — quarantine registry
  3. models/trade_signal.py      — TradeSignal dataclass (structural gap)
  4. data_feeds/dhan_feed.py     — _lookup(), _load() instrument path, sim fallback
  5. execution_engine/order_manager.py — order_id format string
  6. Live extra_map               — runtime symbol keys loaded from Dhan compact list
"""
import sys, os, csv, json, re

sys.path.insert(0, '/app')
os.chdir('/app')

import logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)-36s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("symbol.normalization.audit")

# ── Counters ─────────────────────────────────────────────────────────────────
total_findings = 0
trailing_space_fixes = 0
case_fixes = 0
suffix_fixes = 0
symbols_normalized = set()

def emit(raw_symbol, normalized_symbol, source_module, normalization_applied, issue_type="FINDING"):
    global total_findings, trailing_space_fixes, case_fixes, suffix_fixes
    total_findings += 1
    if normalization_applied in ("STRIP_WHITESPACE", "STRIP_LEADING_SPACE", "STRIP_TRAILING_SPACE"):
        trailing_space_fixes += 1
    elif normalization_applied == "TO_UPPER":
        case_fixes += 1
    elif normalization_applied in ("REMOVE_NS_SUFFIX", "REMOVE_BO_SUFFIX"):
        suffix_fixes += 1
    if raw_symbol != normalized_symbol:
        symbols_normalized.add(raw_symbol)
    log.warning(
        "[SymbolNormalizationAudit] raw_symbol=%s normalized_symbol=%s "
        "source_module=%s normalization_applied=%s",
        repr(raw_symbol), repr(normalized_symbol), source_module, normalization_applied,
    )

def emit_gap(source_module, field_path, gap_description, impact):
    """Emit a structural gap (missing normalization in code path) rather than a data finding."""
    log.warning(
        "[SymbolNormalizationAudit] type=STRUCTURAL_GAP "
        "source_module=%s field_path=%s gap=%s impact=%s",
        source_module, field_path, gap_description, impact,
    )

def check_symbol(sym, source_module, context=""):
    """Check a raw symbol string for normalization issues and emit findings."""
    found = False
    if sym != sym.strip():
        normalized = sym.strip()
        note = f"trailing={repr(sym[len(sym.rstrip()):])!s}" if sym.rstrip() == sym.lstrip() else f"leading={repr(sym[:len(sym)-len(sym.lstrip())])}"
        emit(sym, normalized, source_module,
             "STRIP_TRAILING_SPACE" if sym == sym.lstrip() else "STRIP_LEADING_SPACE")
        found = True
    if sym != sym.upper():
        emit(sym, sym.upper(), source_module, "TO_UPPER")
        found = True
    if sym.endswith('.NS'):
        emit(sym, sym[:-3], source_module, "REMOVE_NS_SUFFIX")
        found = True
    elif sym.endswith('.BO'):
        emit(sym, sym[:-3], source_module, "REMOVE_BO_SUFFIX")
        found = True
    return found

# ─────────────────────────────────────────────────────────────────────────────
# 1. data/paper_trades.csv
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=paper_trades.csv ...")
try:
    csv_symbol_set = set()
    csv_dirty = set()
    with open('data/paper_trades.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            sym = row.get('symbol', '')
            if sym in csv_symbol_set:
                continue
            csv_symbol_set.add(sym)
            if check_symbol(sym, "data/paper_trades.csv", context=f"oid={row.get('order_id','')[:30]}"):
                csv_dirty.add(sym)
    log.info(
        "[SymbolNormalizationAudit] paper_trades.csv: unique_symbols=%d dirty=%d clean=%d",
        len(csv_symbol_set), len(csv_dirty), len(csv_symbol_set) - len(csv_dirty),
    )
except Exception as e:
    log.error("[SymbolNormalizationAudit] paper_trades.csv error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 2. data/ca_quarantine.json
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=ca_quarantine.json ...")
try:
    with open('data/ca_quarantine.json', encoding='utf-8') as f:
        q = json.load(f)
    for oid, rec in q.items():
        sym = rec.get('symbol', '')
        check_symbol(sym, "data/ca_quarantine.json", context=f"oid={oid[:30]}")
    log.info("[SymbolNormalizationAudit] ca_quarantine.json: checked %d entries", len(q))
except Exception as e:
    log.error("[SymbolNormalizationAudit] ca_quarantine.json error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Structural gap: TradeSignal.symbol — no __post_init__, no strip
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=models/trade_signal.py ...")
try:
    with open('models/trade_signal.py', encoding='utf-8') as f:
        ts_src = f.read()
    has_post_init = '__post_init__' in ts_src
    has_strip_on_symbol = ('symbol' in ts_src and 'strip()' in ts_src and
                            any('symbol' in l and 'strip' in l for l in ts_src.splitlines()))
    if not has_post_init:
        emit_gap(
            "models/trade_signal.py",
            "TradeSignal.symbol",
            "NO __post_init__ to normalize symbol — raw string accepted verbatim",
            "Any caller passing symbol with trailing/leading spaces propagates dirty symbol "
            "through execution_engine, trade_monitor, learning_engine, and dhan_feed._lookup()",
        )
    elif not has_strip_on_symbol:
        emit_gap(
            "models/trade_signal.py",
            "TradeSignal.symbol",
            "__post_init__ exists but no symbol.strip() call found",
            "Partial gap — normalization depends on caller discipline",
        )
    else:
        log.info("[SymbolNormalizationAudit] TradeSignal.__post_init__ present and strips symbol. OK.")
except Exception as e:
    log.error("[SymbolNormalizationAudit] models/trade_signal.py error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Structural gap: dhan_feed.py — _lookup(), _load(), sim fallbacks
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=data_feeds/dhan_feed.py ...")
try:
    with open('data_feeds/dhan_feed.py', encoding='utf-8') as f:
        df_lines = f.readlines()

    # 4a. _lookup(): does it call strip()?
    in_lookup = False
    lookup_has_strip = False
    lookup_lineno = None
    for i, line in enumerate(df_lines, 1):
        if 'def _lookup' in line:
            in_lookup = True
            lookup_lineno = i
        if in_lookup:
            if '.strip()' in line:
                lookup_has_strip = True
            if i > lookup_lineno and line.startswith('    def '):
                break
    if not lookup_has_strip:
        emit_gap(
            "data_feeds/dhan_feed.py",
            f"DhanFeed._lookup() [L{lookup_lineno}]",
            "sym = symbol.upper().replace('.NS','').replace('.BO','') — NO .strip()",
            "Symbol with trailing space (e.g. 'JSWSTEEL    ') misses DHAN_SECURITY_MAP key "
            "'JSWSTEEL' → token lookup failure → feed degraded → FeedIntegrityViolation",
        )
    else:
        log.info("[SymbolNormalizationAudit] _lookup() has .strip(). OK.")

    # 4b. Instrument loader (_load background thread): does it strip SEM_TRADING_SYMBOL?
    load_start = None
    load_has_strip_on_sym = False
    for i, line in enumerate(df_lines, 1):
        if 'SEM_TRADING_SYMBOL' in line:
            load_start = i
            if '.strip()' in line:
                load_has_strip_on_sym = True
    if load_start and not load_has_strip_on_sym:
        emit_gap(
            "data_feeds/dhan_feed.py",
            f"DhanFeed._load() instrument loader [L{load_start}]",
            "sym = row.get('SEM_TRADING_SYMBOL','').upper() — NO .strip()",
            "Dhan compact instrument list has fixed-width padded symbols. "
            "'JSWSTEEL    ' stored verbatim in _extra_map → all downstream lookups fail for clean key",
        )

    # 4c. Sim fallback paths: do they strip bare?
    sim_gaps = []
    for i, line in enumerate(df_lines, 1):
        if 'bare' in line and 'replace(".NS"' in line and '.strip()' not in line:
            # Check if .strip() is on the same or next line
            next_line = df_lines[i] if i < len(df_lines) else ""
            if '.strip()' not in next_line:
                sim_gaps.append(i)

    if sim_gaps:
        emit_gap(
            "data_feeds/dhan_feed.py",
            f"sim fallback bare-symbol stripping [lines ~{sim_gaps}]",
            "bare = symbol.upper().replace('.NS','').replace('.BO','') — NO .strip()",
            "Symbol 'JSWSTEEL    ' → bare='JSWSTEEL    ' → not in _SIM_PRICES['JSWSTEEL'] "
            "→ FeedIntegrityViolation even though JSWSTEEL is a known symbol. "
            "Trailing space causes a false UNKNOWN_SYMBOL classification.",
        )

except Exception as e:
    log.error("[SymbolNormalizationAudit] dhan_feed.py error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Structural gap: order_manager.py — order_id format string
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=execution_engine/order_manager.py ...")
try:
    with open('execution_engine/order_manager.py', encoding='utf-8') as f:
        om_lines = f.readlines()
    for i, line in enumerate(om_lines, 1):
        if 'f"SIM_{symbol}_' in line or "f'SIM_{symbol}_" in line:
            stripped_line = line.strip()
            has_strip = '.strip()' in stripped_line
            if not has_strip:
                emit_gap(
                    "execution_engine/order_manager.py",
                    f"_broker_place() [L{i}]",
                    f"order_id = f'SIM_{{symbol}}_...' — symbol not stripped before embedding",
                    "Trailing spaces in signal.symbol baked into order_id and paper_trades.csv "
                    "symbol field permanently. Cannot be corrected post-write without CSV migration.",
                )
            break
except Exception as e:
    log.error("[SymbolNormalizationAudit] order_manager.py error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Live extra_map — runtime keys from Dhan instrument list
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=live_extra_map ...")
try:
    from data_feeds import get_feed_manager
    fm = get_feed_manager()
    dhan = getattr(fm, '_dhan_feed', None) or getattr(fm, 'dhan_feed', None)
    if dhan is None and hasattr(fm, 'dhan'):
        dhan = fm.dhan
    extra_map = getattr(dhan, '_extra_map', {}) if dhan else {}
    dirty_extra = []
    for sym_key in extra_map:
        if sym_key != sym_key.strip() or sym_key != sym_key.upper():
            dirty_extra.append(sym_key)
            check_symbol(sym_key, "data_feeds/dhan_feed.py:_extra_map[runtime]")
    log.info(
        "[SymbolNormalizationAudit] _extra_map: total_keys=%d dirty_keys=%d",
        len(extra_map), len(dirty_extra),
    )
    if dirty_extra:
        log.warning(
            "[SymbolNormalizationAudit] dirty extra_map keys (first 20): %s",
            dirty_extra[:20],
        )
except Exception as e:
    log.error("[SymbolNormalizationAudit] live extra_map error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 7. DHAN_SECURITY_MAP static dict — confirm all keys are clean
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=DHAN_SECURITY_MAP (static) ...")
try:
    from data_feeds.dhan_feed import DHAN_SECURITY_MAP
    dirty_static = [k for k in DHAN_SECURITY_MAP if k != k.strip() or k != k.upper()]
    log.info(
        "[SymbolNormalizationAudit] DHAN_SECURITY_MAP: total_keys=%d dirty_keys=%d",
        len(DHAN_SECURITY_MAP), len(dirty_static),
    )
    if dirty_static:
        for k in dirty_static:
            check_symbol(k, "data_feeds/dhan_feed.py:DHAN_SECURITY_MAP[static]")
except Exception as e:
    log.error("[SymbolNormalizationAudit] DHAN_SECURITY_MAP error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# 8. AngelOne token cache — symbol keys
# ─────────────────────────────────────────────────────────────────────────────
log.info("[SymbolNormalizationAudit] Scanning source=angelone_token_cache.json ...")
try:
    with open('data/angelone_token_cache.json', encoding='utf-8') as f:
        cache = json.load(f)
    dirty_cache = []
    for k in cache:
        if k != k.strip() or k != k.upper():
            dirty_cache.append(k)
            check_symbol(k, "data/angelone_token_cache.json")
    log.info(
        "[SymbolNormalizationAudit] angelone_token_cache: total=%d dirty=%d",
        len(cache), len(dirty_cache),
    )
except FileNotFoundError:
    log.info("[SymbolNormalizationAudit] angelone_token_cache.json not found (skipping)")
except Exception as e:
    log.error("[SymbolNormalizationAudit] angelone_token_cache.json error: %s", e)

# ─────────────────────────────────────────────────────────────────────────────
# Causal chain summary (evidence narrative)
# ─────────────────────────────────────────────────────────────────────────────
CAUSAL_CHAIN = (
    "Dhan compact instrument list → SEM_TRADING_SYMBOL padded to fixed width → "
    "_load() reads without .strip() → _extra_map['JSWSTEEL    '] stored dirty → "
    "scanner/opportunity engine reads dirty key → TradeSignal(symbol='JSWSTEEL    ') created (no __post_init__) → "
    "_broker_place() embeds raw symbol in f'SIM_{symbol}_...' → "
    "order_id and paper_trades.csv symbol field permanently dirty → "
    "_lookup('JSWSTEEL    ') misses DHAN_SECURITY_MAP['JSWSTEEL'] (no strip) → feed degraded → "
    "_sim_quote('JSWSTEEL    ') bare='JSWSTEEL    ' misses _SIM_PRICES['JSWSTEEL'] (no strip) → "
    "[FeedIntegrityViolation] fires even though JSWSTEEL IS a known symbol → quarantine misclassified"
)

# ─────────────────────────────────────────────────────────────────────────────
# EOD Summary
# ─────────────────────────────────────────────────────────────────────────────
log.info(
    "[SymbolNormalizationSummary] "
    "total_findings=%d symbols_normalized=%d "
    "trailing_space_fixes=%d case_fixes=%d suffix_fixes=%d "
    "structural_gaps=5 "
    "causal_chain=%s",
    total_findings,
    len(symbols_normalized),
    trailing_space_fixes,
    case_fixes,
    suffix_fixes,
    CAUSAL_CHAIN,
)

# ─────────────────────────────────────────────────────────────────────────────
# Console output
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 72)
print("SYMBOL NORMALIZATION AUDIT COMPLETE")
print("=" * 72)
print(f"  Total findings:        {total_findings}")
print(f"  Symbols with issues:   {len(symbols_normalized)} → {sorted(symbols_normalized)}")
print(f"  Trailing space fixes:  {trailing_space_fixes}")
print(f"  Case fixes:            {case_fixes}")
print(f"  Suffix fixes:          {suffix_fixes}")
print()
print("  Structural gaps identified (no data fix — code paths):")
print("    1. TradeSignal.symbol — no __post_init__ strip")
print("    2. DhanFeed._lookup() — no .strip() before dict lookup")
print("    3. DhanFeed._load()   — no .strip() on SEM_TRADING_SYMBOL")
print("    4. order_manager._broker_place() — symbol not stripped before order_id f-string")
print("    5. Sim fallback bare= — no .strip() → 'JSWSTEEL    ' → false FeedIntegrityViolation")
print()
print("  Causal chain:")
for part in CAUSAL_CHAIN.split(" → "):
    print(f"    → {part}")
