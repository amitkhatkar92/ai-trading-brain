"""
sym_probe.py — Symbol normalization evidence collector.
Run inside container: python3 /tmp/sym_probe.py
Evidence only. No behavior changes.
"""
import sys, os, csv, json, re, ast

sys.path.insert(0, '/app')
os.chdir('/app')

SECTION = lambda t: print(f"\n{'='*60}\n{t}\n{'='*60}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. paper_trades.csv — raw symbol field
# ─────────────────────────────────────────────────────────────────────────────
SECTION("1. paper_trades.csv — raw symbol repr")
try:
    with open('data/paper_trades.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        seen = {}
        for row in reader:
            sym = row.get('symbol', '')
            oid = row.get('order_id', row.get('oid', ''))[:40]
            issues = []
            if sym != sym.strip():
                issues.append(f"WHITESPACE raw={repr(sym)} stripped={repr(sym.strip())}")
            if sym != sym.upper():
                issues.append(f"CASE raw={repr(sym)} upper={repr(sym.upper())}")
            if sym.endswith('.NS') or sym.endswith('.BO'):
                issues.append(f"EXCHANGE_SUFFIX raw={repr(sym)}")
            key = repr(sym)
            if key not in seen:
                seen[key] = {'sym': sym, 'issues': issues, 'oid': oid, 'count': 0}
            seen[key]['count'] += 1
    for key, info in seen.items():
        tag = " [ISSUES: " + " | ".join(info['issues']) + "]" if info['issues'] else " [CLEAN]"
        print(f"  sym={repr(info['sym'])} count={info['count']}{tag}")
        if info['issues']:
            print(f"    sample_oid={info['oid']}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. ca_quarantine.json — symbol field
# ─────────────────────────────────────────────────────────────────────────────
SECTION("2. ca_quarantine.json — symbol repr")
try:
    with open('data/ca_quarantine.json', encoding='utf-8') as f:
        q = json.load(f)
    for oid, rec in q.items():
        sym = rec.get('symbol', '')
        issues = []
        if sym != sym.strip():
            issues.append(f"WHITESPACE raw={repr(sym)} stripped={repr(sym.strip())}")
        if sym != sym.upper():
            issues.append(f"CASE raw={repr(sym)}")
        tag = " ISSUES: " + " | ".join(issues) if issues else " CLEAN"
        print(f"  oid_prefix={repr(oid[:35])} sym={repr(sym)}{tag}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Order manager — how the order_id is built from symbol
# ─────────────────────────────────────────────────────────────────────────────
SECTION("3. order_manager.py — order_id construction (source scan)")
try:
    with open('execution_engine/order_manager.py', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if 'order_id' in line.lower() and 'SIM_' in line:
            print(f"  L{i}: {line.rstrip()}")
        if '.strip()' in line and 'symbol' in line.lower():
            print(f"  L{i} [strip]: {line.rstrip()}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. dhan_feed.py — _lookup() normalization
# ─────────────────────────────────────────────────────────────────────────────
SECTION("4. dhan_feed.py — _lookup() and symbol normalization paths")
try:
    with open('data_feeds/dhan_feed.py', encoding='utf-8') as f:
        lines = f.readlines()
    in_lookup = False
    for i, line in enumerate(lines, 1):
        if 'def _lookup' in line:
            in_lookup = True
        if in_lookup:
            print(f"  L{i}: {line.rstrip()}")
            if i > 1 and line.strip() == '' and in_lookup:
                pass
            if in_lookup and i > 5 and line.startswith('    def ') and 'def _lookup' not in line:
                in_lookup = False
                break
        # Also flag any line doing strip/upper on symbol in top section
        if 'strip()' in line and i < 250:
            print(f"  L{i} [strip early]: {line.rstrip()}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. dhan_feed.py — extra_map loading (instrument file parsing)
# ─────────────────────────────────────────────────────────────────────────────
SECTION("5. dhan_feed.py — instrument/extra_map loading (strip usage)")
try:
    with open('data_feeds/dhan_feed.py', encoding='utf-8') as f:
        content = f.read()
    # Find lines near extra_map loading
    for i, line in enumerate(content.splitlines(), 1):
        if any(k in line for k in ['extra_map', 'TRADING_SYMBOL', 'trading_symbol', 'SEM_TRADING_SYMBOL',
                                    'strip()', '.upper()', 'instrument', 'scrip_master']):
            if any(k in line for k in ['strip', 'upper', 'symbol', 'SYMBOL', 'trading']):
                print(f"  L{i}: {line.rstrip()}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. trade_monitor.py — how symbol is read from order
# ─────────────────────────────────────────────────────────────────────────────
SECTION("6. trade_monitor.py — symbol access from order")
try:
    with open('trade_monitoring/trade_monitor.py', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        lstrip = line.strip()
        if any(k in lstrip for k in ['symbol =', 'symbol=', '.symbol', 'sym =', 'sym=']):
            if any(k in lstrip for k in ['order', 'trade', 'position', 'getattr']):
                print(f"  L{i}: {line.rstrip()}")
        if 'strip()' in lstrip and 'symbol' in lstrip.lower():
            print(f"  L{i} [strip]: {line.rstrip()}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Live feed manager — what symbols it currently tracks
# ─────────────────────────────────────────────────────────────────────────────
SECTION("7. Live feed — symbol repr from get_feed_manager watchlist")
try:
    from data_feeds import get_feed_manager
    fm = get_feed_manager()
    # Try to get the watchlist / active symbols
    wl = getattr(fm, '_watchlist', None) or getattr(fm, 'watchlist', None) or \
         getattr(fm, '_symbols', None) or getattr(fm, 'symbols', None)
    if wl:
        for sym in list(wl)[:30]:
            issues = []
            if sym != sym.strip():
                issues.append(f"WHITESPACE")
            if sym != sym.upper():
                issues.append(f"MIXED_CASE")
            if sym.endswith('.NS') or sym.endswith('.BO'):
                issues.append(f"EXCHANGE_SUFFIX")
            tag = " ISSUES: " + ", ".join(issues) if issues else ""
            if issues:
                print(f"  repr={repr(sym)}{tag}")
    else:
        print(f"  Watchlist not found. Attrs: {[a for a in dir(fm) if 'sym' in a.lower() or 'watch' in a.lower()]}")
except Exception as e:
    print(f"  ERROR: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Open orders from order manager — raw symbol fields
# ─────────────────────────────────────────────────────────────────────────────
SECTION("8. Order manager — open orders raw symbol repr")
try:
    from execution_engine.order_manager import OrderManager
    om = OrderManager()
    orders = getattr(om, '_open_orders', {}) or getattr(om, 'open_orders', {})
    if not orders:
        # Try loading from CSV
        import csv
        with open('data/paper_trades.csv') as f:
            orders_csv = list(csv.DictReader(f))
        open_orders = [r for r in orders_csv if not r.get('exit_time') and not r.get('exit_price')]
        print(f"  Open orders from CSV: {len(open_orders)}")
        for r in open_orders:
            sym = r.get('symbol', '')
            print(f"  repr={repr(sym)} oid={r.get('order_id','')[:40]}")
    else:
        for oid, order in list(orders.items())[:20]:
            sym = getattr(order, 'symbol', '?')
            issues = []
            if isinstance(sym, str):
                if sym != sym.strip(): issues.append("WHITESPACE")
                if sym != sym.upper(): issues.append("MIXED_CASE")
            print(f"  repr={repr(sym)} oid={oid[:40]}" + (f" ISSUES: {issues}" if issues else ""))
except Exception as e:
    print(f"  ERROR: {e}")
