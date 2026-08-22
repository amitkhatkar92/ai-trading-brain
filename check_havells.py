"""Inspect HAVELLS and NESTLEIND candidate records."""
import sys
sys.path.insert(0, '/app')
from opportunity_engine.candidate_store import CandidateStore
cands = CandidateStore.read() or []
targets = {c['symbol']: c for c in cands if c.get('symbol') in ('HAVELLS', 'NESTLEIND')}
for sym, c in targets.items():
    bl = float(c.get('base_ltp') or 0)
    sup = float(c.get('support') or 0)
    res = float(c.get('resistance') or 0)
    atr = float(c.get('atr14') or 0)
    if atr <= 0 and res > sup > 0:
        atr = (res - sup) * 0.40
    if atr <= 0:
        atr = 997 * 0.020   # sim live_ltp fallback
    print(f"{sym}: base_ltp={bl} support={sup} resistance={res} atr14_stored={c.get('atr14')} atr_effective={atr:.2f}")
    print(f"  sup-atr={sup-atr:.2f}  sup<base_ltp*1.05? {sup < bl*1.05}")
    print(f"  ratio_live_sim/base: {997/bl:.3f}" if bl > 0 else "  ratio: N/A (base_ltp=0)")
