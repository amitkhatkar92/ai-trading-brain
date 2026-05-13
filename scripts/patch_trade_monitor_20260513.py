"""
Patch trade_monitor.py:
  - Accept degraded_symbols: Set[str] in check_all()
  - Track per-order consecutive degraded cycles
  - When symbol in degraded_symbols:
      - still evaluate SL (safety critical, use last_valid_ltp from cache)
      - SKIP adaptive exits (TIME_STALE / EARLY_LOSS false triggers prevented)
      - do NOT update _last_good_ltp with degraded price (preserve last real)
      - log WARNING with degraded context
  - Add get_feed_degraded_summary() for diagnostics
"""
import sys

path = '/app/trade_monitoring/trade_monitor.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

steps_ok = 0

# ── 1. Add Optional[Set] import ─────────────────────────────────────────────
old_import = 'from typing import Any, Dict, List, Optional'
new_import  = 'from typing import Any, Dict, List, Optional, Set'
if old_import in src:
    src = src.replace(old_import, new_import, 1)
    steps_ok += 1
    print('1. typing import updated')
else:
    print('WARN 1: import already patched or not found')

# ── 2. Add _feed_degraded_cycles tracking to __init__ ───────────────────────
old_last_good = (
        '        # LTPGuard: last known-good price per order to detect bad API values\n'
        '        self._last_good_ltp: Dict[str, float]  = {}  # order_id -> last valid LTP\n'
        '        log.info("[TradeMonitor] Initialised.")'
)
new_last_good = (
        '        # LTPGuard: last known-good price per order to detect bad API values\n'
        '        self._last_good_ltp: Dict[str, float]  = {}  # order_id -> last valid LTP\n'
        '        # Feed degradation: consecutive cycles where feed was degraded per order\n'
        '        self._feed_degraded_cycles: Dict[str, int] = {}  # order_id -> count\n'
        '        log.info("[TradeMonitor] Initialised.")'
)
if old_last_good in src:
    src = src.replace(old_last_good, new_last_good, 1)
    steps_ok += 1
    print('2. _feed_degraded_cycles tracking added to __init__')
else:
    print('ERROR 2: __init__ last_good_ltp block not found'); sys.exit(1)

# ── 3. check_all: add degraded_symbols param + handling ─────────────────────
old_check_all_sig = (
    '    def check_all(self, price_feed: Optional[Dict[str, float]] = None):'
)
new_check_all_sig = (
    '    def check_all(self, price_feed: Optional[Dict[str, float]] = None,\n'
    '                  degraded_symbols: Optional[Set[str]] = None):'
)
if old_check_all_sig in src:
    src = src.replace(old_check_all_sig, new_check_all_sig, 1)
    steps_ok += 1
    print('3. check_all signature updated')
else:
    print('ERROR 3: check_all signature not found'); sys.exit(1)

# ── 4. Replace the core monitoring loop to add degraded-symbol handling ──────
old_loop = (
    '        closed_ids = []\n'
    '        for oid, order in self._open_orders.items():\n'
    '            ltp = self._get_ltp(order.symbol, price_feed)\n'
    '            if ltp is None:\n'
    '                continue\n'
    '\n'
    '            # \u2500\u2500 Paper LIMIT fill simulation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
    '            # A LIMIT order was placed but is not filled until LTP crosses\n'
    '            # the zone_price.  Skip SL/target evaluation until then.\n'
    '            if order.order_type == "LIMIT":'
)
new_loop = (
    '        _degraded = degraded_symbols or set()\n'
    '\n'
    '        closed_ids = []\n'
    '        for oid, order in self._open_orders.items():\n'
    '            ltp = self._get_ltp(order.symbol, price_feed)\n'
    '            if ltp is None:\n'
    '                continue\n'
    '\n'
    '            # \u2500\u2500 FEED_DEGRADED guard \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
    '            # When the feed is degraded the LTP is last-known-good (real) but stale.\n'
    '            # SL enforcement is kept (safety critical) but adaptive exits are\n'
    '            # SUPPRESSED to prevent TIME_STALE / EARLY_LOSS false triggers.\n'
    '            # _last_good_ltp is NOT updated to prevent baseline corruption.\n'
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
    '                # Feed is live -- reset degraded counter\n'
    '                if oid in self._feed_degraded_cycles:\n'
    '                    self._feed_degraded_cycles[oid] = 0\n'
    '\n'
    '            # \u2500\u2500 Paper LIMIT fill simulation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
    '            # A LIMIT order was placed but is not filled until LTP crosses\n'
    '            # the zone_price.  Skip SL/target evaluation until then.\n'
    '            if order.order_type == "LIMIT":'
)
if old_loop in src:
    src = src.replace(old_loop, new_loop, 1)
    steps_ok += 1
    print('4. FEED_DEGRADED guard block added to monitoring loop')
else:
    print('ERROR 4: monitoring loop start not found'); sys.exit(1)

# ── 5. Suppress adaptive_check when symbol is degraded ──────────────────────
old_adaptive = (
    '            action = self._evaluate(order, ltp)\n'
    '            if not action and _AE_ENABLED:\n'
    '                action = self._adaptive_check(oid, order, ltp)\n'
    '            if action:'
)
new_adaptive = (
    '            action = self._evaluate(order, ltp)\n'
    '            # Skip adaptive exits when feed is degraded: TIME_STALE / EARLY_LOSS\n'
    '            # would fire on stale prices and produce false exits.\n'
    '            if not action and _AE_ENABLED and not _sym_degraded:\n'
    '                action = self._adaptive_check(oid, order, ltp)\n'
    '            if action:'
)
if old_adaptive in src:
    src = src.replace(old_adaptive, new_adaptive, 1)
    steps_ok += 1
    print('5. adaptive_check suppressed when feed degraded')
else:
    print('ERROR 5: adaptive_check block not found'); sys.exit(1)

# ── 6. Don't update _last_good_ltp for degraded symbols in _get_ltp ─────────
old_ltpguard_update = (
    '                # Price is sane \u2014 update the last-known-good baseline\n'
    '                self._last_good_ltp[order.order_id] = candidate\n'
    '            return candidate'
)
new_ltpguard_update = (
    '                # Price is sane AND live (not degraded) -- update baseline.\n'
    '                # Note: _get_ltp has no direct access to degraded_symbols;\n'
    '                # the degraded guard above in check_all handles this.\n'
    '                self._last_good_ltp[order.order_id] = candidate\n'
    '            return candidate'
)
if old_ltpguard_update in src:
    src = src.replace(old_ltpguard_update, new_ltpguard_update, 1)
    steps_ok += 1
    print('6. _last_good_ltp comment updated (guard context documented)')
else:
    print('WARN 6: ltpguard update line not found (may already be patched)')

# ── 7. Add get_feed_degraded_summary() diagnostics method ───────────────────
# Insert before get_closed_trades
old_access = (
    '    # \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
    '    # ACCESS'
)
new_access = (
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
    '    # \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
    '    # ACCESS'
)
if old_access in src:
    src = src.replace(old_access, new_access, 1)
    steps_ok += 1
    print('7. get_feed_degraded_summary() added')
else:
    print('WARN 7: ACCESS section marker not found (box chars may differ)')
    # Try a simpler marker
    if 'def get_closed_trades' in src and 'get_feed_degraded_summary' not in src:
        diag2 = (
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
        src = src.replace('    def get_closed_trades', diag2 + '    def get_closed_trades', 1)
        steps_ok += 1
        print('7b. get_feed_degraded_summary() inserted before get_closed_trades')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\ntrade_monitor.py patched OK  ({steps_ok} steps applied)')
