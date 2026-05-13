"""
Fix two gaps in the feed degradation implementation:

Gap 1: trade_monitor._get_ltp simulation fallback
  When price_feed exists but symbol is absent (excluded due to no cached LTP),
  the fallback returns order.entry_price * random(+-3%) -- same problem as synthetic.
  Fix: return None when price_feed is provided but symbol is missing.
  Simulation (+-3%) only fires when price_feed is None (no feed at all).

Gap 2: orchestrator price-feed assembly
  Symbols excluded from price_feed due to no cached LTP are NOT in _degraded_syms.
  This means their open positions bypass the FEED_DEGRADED guard in check_all().
  Fix: track symbols that failed AND had no cache as "excluded" -> add to _degraded_syms.
"""
import sys
import re

# ── Fix 1: trade_monitor._get_ltp ───────────────────────────────────────────
path_tm = '/app/trade_monitoring/trade_monitor.py'
with open(path_tm, encoding='utf-8') as f:
    src_tm = f.read()

crlf = '\r\n' in src_tm
if crlf:
    src_tm = src_tm.replace('\r\n', '\n')

old_sim_fallback = (
    '        # Simulation fallback (only when price_feed is None / symbol missing)\n'
    '        import random\n'
    '        if order:\n'
    '            return round(order.entry_price * (1 + random.uniform(-0.03, 0.03)), 2)\n'
    '        return None'
)
new_sim_fallback = (
    '        # Simulation fallback: ONLY when price_feed is None entirely\n'
    '        # (development / no-feed mode).  When price_feed exists but\n'
    '        # this symbol is absent, it means the feed lookup failed and we\n'
    '        # excluded the symbol -- return None to skip this evaluation cycle.\n'
    '        if price_feed is not None:\n'
    '            return None   # feed attempted but symbol absent -- skip cycle\n'
    '        import random\n'
    '        if order:\n'
    '            return round(order.entry_price * (1 + random.uniform(-0.03, 0.03)), 2)\n'
    '        return None'
)

if old_sim_fallback in src_tm:
    src_tm = src_tm.replace(old_sim_fallback, new_sim_fallback, 1)
    print('Fix 1: _get_ltp simulation fallback gated on price_feed=None')
elif 'price_feed is not None' in src_tm:
    print('Fix 1: already patched')
else:
    print('ERROR Fix 1: fallback block not found'); sys.exit(1)

if crlf:
    src_tm = src_tm.replace('\n', '\r\n')
with open(path_tm, 'w', encoding='utf-8') as f:
    f.write(src_tm)

# ── Fix 2: orchestrator - track excluded symbols as degraded ─────────────────
path_orch = '/app/orchestrator/master_orchestrator.py'
with open(path_orch, encoding='utf-8') as f:
    src_orch = f.read()

crlf2 = '\r\n' in src_orch
if crlf2:
    src_orch = src_orch.replace('\r\n', '\n')

# After the _quotes loop that builds _live_pf and _degraded_syms, add:
# symbols in _open_syms that are not in _live_pf (excluded due to no cache) -> degraded
old_excl = (
    '                # Escalation: count consecutive degraded cycles and alert\n'
    '                _FEED_DEGRADED_ALERT_CYCLES = 6  # 30 min at 5-min monitoring'
)
new_excl = (
    '                # Symbols that failed AND had no cached LTP were excluded from\n'
    '                # price_feed entirely.  They are also degraded -- add them to\n'
    '                # _degraded_syms so the FEED_DEGRADED guard protects them too.\n'
    '                for _s in _open_syms:\n'
    '                    if _s not in _live_pf and _s not in _degraded_syms:\n'
    '                        _degraded_syms.add(_s)\n'
    '                        log.warning(\n'
    '                            "[Orchestrator] FEED_EXCLUDED %s -- "\n'
    '                            "no live LTP and no cached LTP -- "\n'
    '                            "SL skip + adaptive SUPPRESSED this cycle",\n'
    '                            _s,\n'
    '                        )\n'
    '\n'
    '                # Escalation: count consecutive degraded cycles and alert\n'
    '                _FEED_DEGRADED_ALERT_CYCLES = 6  # 30 min at 5-min monitoring'
)

if old_excl in src_orch:
    src_orch = src_orch.replace(old_excl, new_excl, 1)
    print('Fix 2: excluded symbols added to _degraded_syms')
elif 'FEED_EXCLUDED' in src_orch:
    print('Fix 2: already patched')
else:
    print('ERROR Fix 2: escalation anchor not found'); sys.exit(1)

if crlf2:
    src_orch = src_orch.replace('\n', '\r\n')
with open(path_orch, 'w', encoding='utf-8') as f:
    f.write(src_orch)

print('\nBoth gap fixes applied')
