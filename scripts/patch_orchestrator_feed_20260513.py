"""
Patch master_orchestrator.py:
  - In _do_monitor(): collect degraded_syms from TickerQuote.feed_degraded
  - Pass degraded_symbols=degraded_syms to check_all()
  - Track consecutive degraded cycles per symbol (_feed_degraded_counts)
  - Emit Telegram WARNING when any symbol is degraded >= FEED_DEGRADED_ALERT_CYCLES (6)
  - Log degraded status in monitoring log line
"""
import sys
import re

path = '/app/orchestrator/master_orchestrator.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

crlf = '\r\n' in src
if crlf:
    src = src.replace('\r\n', '\n')
    print('normalised CRLF')

steps_ok = 0

# ── 1. Add _feed_degraded_counts to __init__ ────────────────────────────────
# Find the __init__ of MasterOrchestrator and add tracking dict
if '_feed_degraded_counts' not in src:
    # Look for self.order_manager init line
    m = re.search(r'(        self\.order_manager\s*=\s*OrderManager[^\n]*\n)', src)
    if m:
        src = src[:m.end()] + (
            '        # Feed degradation escalation: consecutive degraded cycles per symbol\n'
            '        self._feed_degraded_counts: dict = {}\n'
        ) + src[m.end():]
        steps_ok += 1
        print('1. _feed_degraded_counts added to __init__')
    else:
        print('WARN 1: OrderManager init line not found, trying fallback')
        # Fallback: add after self.trade_monitor
        m2 = re.search(r'(        self\.trade_monitor\s*=[^\n]*\n)', src)
        if m2:
            src = src[:m2.end()] + (
                '        # Feed degradation escalation: consecutive degraded cycles per symbol\n'
                '        self._feed_degraded_counts: dict = {}\n'
            ) + src[m2.end():]
            steps_ok += 1
            print('1b. _feed_degraded_counts added after trade_monitor init')
        else:
            print('ERROR 1: cannot find init anchor'); sys.exit(1)
else:
    steps_ok += 1
    print('1. already present')

# ── 2. Patch the price-feed assembly block to collect degraded_syms ──────────
# Original block: builds _live_pf from _quotes, then calls check_all()
old_assembly = (
    '            if _open_syms:\n'
    '                _quotes = _feed.get_multiple_quotes([f"{s}.NS" for s in _open_syms])\n'
    '                for _ns_sym, _q in _quotes.items():\n'
    '                    _bare = _ns_sym.replace(".NS", "")\n'
    '                    if _q and getattr(_q, "ltp", 0) > 0:\n'
    '                        _live_pf[_bare] = float(_q.ltp)\n'
    '        except Exception:\n'
    '            _live_pf = {}\n'
    '        self.trade_monitor.check_all(price_feed=_live_pf if _live_pf else None)'
)
new_assembly = (
    '            if _open_syms:\n'
    '                _quotes = _feed.get_multiple_quotes([f"{s}.NS" for s in _open_syms])\n'
    '                _degraded_syms: set = set()\n'
    '                for _ns_sym, _q in _quotes.items():\n'
    '                    _bare = _ns_sym.replace(".NS", "")\n'
    '                    if _q and getattr(_q, "ltp", 0) > 0:\n'
    '                        _live_pf[_bare] = float(_q.ltp)\n'
    '                    # Track degraded feed state\n'
    '                    if _q and getattr(_q, "feed_degraded", False):\n'
    '                        _degraded_syms.add(_bare)\n'
    '                # Escalation: count consecutive degraded cycles and alert\n'
    '                _FEED_DEGRADED_ALERT_CYCLES = 6  # 30 min at 5-min monitoring\n'
    '                for _sym in list(self._feed_degraded_counts.keys()):\n'
    '                    if _sym not in _degraded_syms:\n'
    '                        self._feed_degraded_counts.pop(_sym, None)\n'
    '                for _sym in _degraded_syms:\n'
    '                    cnt = self._feed_degraded_counts.get(_sym, 0) + 1\n'
    '                    self._feed_degraded_counts[_sym] = cnt\n'
    '                    if cnt == _FEED_DEGRADED_ALERT_CYCLES:\n'
    '                        log.warning(\n'
    '                            "[Orchestrator] FEED_DEGRADED_ESCALATION %s -- "\n'
    '                            "degraded for %d consecutive cycles (~%d min). "\n'
    '                            "SL active, adaptive exits SUPPRESSED.",\n'
    '                            _sym, cnt, cnt * 5,\n'
    '                        )\n'
    '                        try:\n'
    '                            from notifications.notifier_manager import get_notifier\n'
    '                            get_notifier().send_alert(\n'
    '                                f"[FEED_DEGRADED] {_sym} -- live LTP unavailable for "\n'
    '                                f"{cnt * 5} min.  Using last-known-good price.  "\n'
    '                                f"SL monitoring active.  Adaptive exits SUPPRESSED."\n'
    '                            )\n'
    '                        except Exception:\n'
    '                            pass\n'
    '        except Exception:\n'
    '            _live_pf = {}\n'
    '            _degraded_syms = set()\n'
    '        self.trade_monitor.check_all(\n'
    '            price_feed=_live_pf if _live_pf else None,\n'
    '            degraded_symbols=_degraded_syms if _live_pf else None,\n'
    '        )'
)
if old_assembly in src:
    src = src.replace(old_assembly, new_assembly, 1)
    steps_ok += 1
    print('2. price-feed assembly + degraded escalation block updated')
elif '_degraded_syms' in src:
    steps_ok += 1
    print('2. already patched')
else:
    print('ERROR 2: assembly block not found'); sys.exit(1)

# Restore CRLF
if crlf:
    src = src.replace('\n', '\r\n')
    print('restored CRLF')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\nmaster_orchestrator.py patched OK  ({steps_ok}/2 steps applied)')
