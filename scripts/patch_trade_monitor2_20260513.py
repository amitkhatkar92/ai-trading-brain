"""
Patch trade_monitor.py (CRLF + UTF-8 aware).
Uses line-number-based insertion where string search can't match due to
CRLF endings or Unicode arrows in comments.
"""
import sys
import re

path = '/app/trade_monitoring/trade_monitor.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

# Normalise line endings so our string searches work
crlf = '\r\n' in src
if crlf:
    src = src.replace('\r\n', '\n')
    print('normalised CRLF -> LF for patching')

steps_ok = 0

# ── 1. typing import ────────────────────────────────────────────────────────
old_imp = 'from typing import Any, Dict, List, Optional'
new_imp = 'from typing import Any, Dict, List, Optional, Set'
if old_imp in src:
    src = src.replace(old_imp, new_imp, 1)
    steps_ok += 1
    print('1. typing import OK')
elif 'Set' in src:
    steps_ok += 1
    print('1. Set already imported')
else:
    print('ERROR 1')

# ── 2. Add _feed_degraded_cycles to __init__ ─────────────────────────────────
# Use a broad search that ignores Unicode arrow direction
if '_feed_degraded_cycles' not in src:
    # Find any line containing self._last_good_ltp: Dict
    m = re.search(r'(        # LTPGuard: last known-good price per order[^\n]*\n'
                  r'        self\._last_good_ltp[^\n]*\n)'
                  r'(        log\.info\("\[TradeMonitor\] Initialised\.\"\))', src)
    if m:
        insert_text = (
            m.group(1) +
            '        # Feed degradation: consecutive cycles with degraded feed per order\n'
            '        self._feed_degraded_cycles: Dict[str, int] = {}  # order_id -> count\n'
            + m.group(2)
        )
        src = src[:m.start()] + insert_text + src[m.end():]
        steps_ok += 1
        print('2. _feed_degraded_cycles added to __init__')
    else:
        print('ERROR 2: regex did not match __init__ block')
        sys.exit(1)
else:
    steps_ok += 1
    print('2. already present')

# ── 3. check_all signature ───────────────────────────────────────────────────
old_sig = '    def check_all(self, price_feed: Optional[Dict[str, float]] = None):'
new_sig = ('    def check_all(self, price_feed: Optional[Dict[str, float]] = None,\n'
           '                  degraded_symbols: Optional[Set[str]] = None):')
if old_sig in src:
    src = src.replace(old_sig, new_sig, 1)
    steps_ok += 1
    print('3. check_all signature updated')
elif 'degraded_symbols' in src:
    steps_ok += 1
    print('3. already patched')
else:
    print('ERROR 3'); sys.exit(1)

# ── 4. Insert FEED_DEGRADED guard block before the LIMIT check in check_all ─
# The pattern: after "closed_ids = []" / the for-loop / ltp = / if ltp is None
old_loop_core = (
    '        closed_ids = []\n'
    '        for oid, order in self._open_orders.items():\n'
    '            ltp = self._get_ltp(order.symbol, price_feed)\n'
    '            if ltp is None:\n'
    '                continue\n'
)
if old_loop_core in src and '_degraded = degraded_symbols' not in src:
    new_loop_core = (
        '        _degraded = degraded_symbols or set()\n'
        '\n'
        '        closed_ids = []\n'
        '        for oid, order in self._open_orders.items():\n'
        '            ltp = self._get_ltp(order.symbol, price_feed)\n'
        '            if ltp is None:\n'
        '                continue\n'
        '\n'
        '            # -- FEED_DEGRADED guard ------------------------------------------\n'
        '            # When the feed is degraded the LTP is last-known-good (real) but\n'
        '            # stale. SL enforcement is kept (safety critical). Adaptive exits\n'
        '            # are SUPPRESSED to prevent TIME_STALE / EARLY_LOSS false triggers.\n'
        '            _sym_degraded = order.symbol in _degraded\n'
        '            if _sym_degraded:\n'
        '                dcycles = self._feed_degraded_cycles.get(oid, 0) + 1\n'
        '                self._feed_degraded_cycles[oid] = dcycles\n'
        '                log.warning(\n'
        '                    "[TradeMonitor] FEED_DEGRADED %s -- cycle=%d  "\n'
        '                    "ltp=%.2f(cached)  sl=%.2f  adaptive=SUPPRESSED",\n'
        '                    order.symbol, dcycles, ltp, order.stop_loss,\n'
        '                )\n'
        '            else:\n'
        '                if oid in self._feed_degraded_cycles:\n'
        '                    self._feed_degraded_cycles[oid] = 0\n'
        '\n'
    )
    src = src.replace(old_loop_core, new_loop_core, 1)
    steps_ok += 1
    print('4. FEED_DEGRADED guard block added')
elif '_degraded = degraded_symbols' in src:
    steps_ok += 1
    print('4. already patched')
else:
    print('ERROR 4: loop core not found'); sys.exit(1)

# ── 5. Suppress adaptive_check when degraded ────────────────────────────────
old_ae = (
    '            action = self._evaluate(order, ltp)\n'
    '            if not action and _AE_ENABLED:\n'
    '                action = self._adaptive_check(oid, order, ltp)\n'
    '            if action:'
)
new_ae = (
    '            action = self._evaluate(order, ltp)\n'
    '            # Suppress adaptive exits when feed is degraded (prevents\n'
    '            # TIME_STALE / EARLY_LOSS false triggers on stale prices).\n'
    '            if not action and _AE_ENABLED and not _sym_degraded:\n'
    '                action = self._adaptive_check(oid, order, ltp)\n'
    '            if action:'
)
if old_ae in src:
    src = src.replace(old_ae, new_ae, 1)
    steps_ok += 1
    print('5. adaptive_check suppressed when degraded')
elif 'not _sym_degraded' in src:
    steps_ok += 1
    print('5. already patched')
else:
    print('ERROR 5'); sys.exit(1)

# ── 6. Add get_feed_degraded_summary() before get_closed_trades ─────────────
if 'get_feed_degraded_summary' not in src:
    diag = (
        '    def get_feed_degraded_summary(self) -> dict:\n'
        '        """Return degradation state for all currently monitored symbols."""\n'
        '        out = {}\n'
        '        for oid, order in self._open_orders.items():\n'
        '            cycles = self._feed_degraded_cycles.get(oid, 0)\n'
        '            if cycles > 0:\n'
        '                out[order.symbol] = dict(\n'
        '                    order_id=oid,\n'
        '                    consecutive_degraded_cycles=cycles,\n'
        '                    last_good_ltp=self._last_good_ltp.get(oid, order.entry_price),\n'
        '                    sl=order.stop_loss,\n'
        '                    adaptive_suppressed=True,\n'
        '                )\n'
        '        return out\n'
        '\n'
    )
    old_closed = '    def get_closed_trades(self) -> List[OrderRecord]:'
    if old_closed in src:
        src = src.replace(old_closed, diag + old_closed, 1)
        steps_ok += 1
        print('6. get_feed_degraded_summary() added')
    else:
        print('WARN 6: get_closed_trades not found')
else:
    steps_ok += 1
    print('6. already present')

# Restore CRLF if needed
if crlf:
    src = src.replace('\n', '\r\n')
    print('restored CRLF')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\ntrade_monitor.py patched OK  ({steps_ok}/6 steps applied)')
