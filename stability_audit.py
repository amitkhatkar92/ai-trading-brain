#!/usr/bin/env python3
"""
stability_audit.py
Core universe stability deep-dive: legitimate persistence vs structural stickiness.
"""
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('/app/data')
NOW_DT   = datetime.now()
SEP      = '=' * 72

def load(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return None

# ── Load data ─────────────────────────────────────────────────────────────
mem       = load(DATA_DIR / 'scanner_memory.json')
raw_today = load(DATA_DIR / 'daily_candidates.json')
cands_today = raw_today.get('candidates', [])

# Build today's full lookup
today_by_sym = {}
for i, c in enumerate(sorted(cands_today, key=lambda x: -x.get('score', 0))):
    today_by_sym[c['symbol']] = {**c, '_rank': i + 1}

# ── Session symbol sets ────────────────────────────────────────────────────
DATE_KEYS   = ['2026-05-27', '2026-05-28', '2026-05-29', '2026-05-30', '2026-06-01']
DAY_LABELS  = {'2026-05-27': 'Tue', '2026-05-28': 'Wed', '2026-05-29': 'Thu',
               '2026-05-30': 'Fri', '2026-06-01': 'Mon'}
sessions    = {dk: set(mem.get(dk, [])) for dk in DATE_KEYS}
today_set   = sessions['2026-06-01']

# ── 25 all-session symbols ─────────────────────────────────────────────────
all5 = set.intersection(*[sessions[dk] for dk in DATE_KEYS])
# 29 symbols that rotated out (ever present but not in today)
ever_present = set.union(*[sessions[dk] for dk in DATE_KEYS])
rotated_out = ever_present - today_set

print(f'\n{SEP}')
print('1. ALL-SESSION CORE: SCORE & CONVICTION AUDIT (25 symbols)')
print(SEP)

# Pull detailed fields from today's candidates for all-5-session symbols
print(f'\n{"Symbol":<14} {"Score":>6} {"Rank":>4} {"ConvDecay":>9} {"ConvScore":>9} {"RefineSts":>10} '
      f'{"DataTrust":>9} {"FreshAge":>8} {"RerankRsn":>20} {"CandOrigin":>14}')
print('-' * 105)

for sym in sorted(all5, key=lambda s: today_by_sym.get(s, {}).get('_rank', 99)):
    c = today_by_sym.get(sym, {})
    print(
        f'{sym:<14} '
        f'{c.get("score", 0):>6.3f} '
        f'{c.get("_rank", "?"):>4} '
        f'{str(c.get("conviction_decay", "?"))[:9]:>9} '
        f'{str(c.get("conviction_score", "?"))[:9]:>9} '
        f'{str(c.get("refinement_status", "?"))[:10]:>10} '
        f'{str(c.get("data_trust_score", "?"))[:9]:>9} '
        f'{str(c.get("freshness_age_minutes", "?"))[:8]:>8} '
        f'{str(c.get("rerank_reason", "none"))[:20]:>20} '
        f'{str(c.get("candidate_origin", "?"))[:14]:>14} '
    )

# ── Score distribution stats for core-25 vs rest ─────────────────────────
print(f'\n{SEP}')
print('2. SCORE STATS: CORE-25 vs ROTATING-34 (today)')
print(SEP)

core_scores  = [today_by_sym[s].get('score', 0) for s in all5 if s in today_by_sym]
other_scores = [c.get('score', 0) for c in cands_today if c['symbol'] not in all5]

def stats(lst):
    if not lst: return {}
    lst_s = sorted(lst)
    n = len(lst_s)
    return {
        'n': n, 'min': lst_s[0], 'max': lst_s[-1],
        'mean': sum(lst_s)/n, 'median': lst_s[n//2],
        'p25': lst_s[n//4], 'p75': lst_s[3*n//4]
    }

cs = stats(core_scores)
os = stats(other_scores)
print(f'  Metric      {"Core-25":>12}  {"Rotating-34":>12}')
print(f'  {"─"*36}')
for metric in ['n', 'min', 'max', 'mean', 'median', 'p25', 'p75']:
    cv = cs.get(metric, '?')
    ov = os.get(metric, '?')
    fmt = '.3f' if isinstance(cv, float) else ''
    print(f'  {metric:<10}  {cv:>12{fmt}}  {ov:>12{fmt}}')

# ── Conviction decay analysis ─────────────────────────────────────────────
print(f'\n{SEP}')
print('3. CONVICTION DECAY ANALYSIS (stickiness signal)')
print(SEP)

# conviction_decay closer to 0 = score is aging / stale
# conviction_score vs base score delta = inertia indicator
decays = []
for c in cands_today:
    cd = c.get('conviction_decay')
    if cd is not None:
        try:
            decays.append((c['symbol'], float(cd), c.get('score', 0), c['symbol'] in all5))
        except Exception:
            pass

if decays:
    core_decays  = [d[1] for d in decays if d[3]]
    other_decays = [d[1] for d in decays if not d[3]]
    print(f'  Core-25 avg conviction_decay  : {sum(core_decays)/max(len(core_decays),1):.4f}')
    print(f'  Rotating avg conviction_decay : {sum(other_decays)/max(len(other_decays),1):.4f}')
    print(f'  (Lower = less fresh / more stale signal)')
    low_decay = sorted([d for d in decays if d[1] < 0.5], key=lambda x: x[1])[:10]
    if low_decay:
        print(f'\n  Symbols with conviction_decay < 0.5 (staleness risk):')
        for sym, cd, sc, is_core in low_decay:
            tag = '[CORE]' if is_core else '      '
            print(f'    {tag} {sym:<14} decay={cd:.4f}  score={sc:.3f}')
else:
    print('  conviction_decay field not populated.')

# ── Invalidation / corruption flags ──────────────────────────────────────
print(f'\n{SEP}')
print('4. INVALIDATION & CORRUPTION FLAG AUDIT')
print(SEP)

for c in sorted(cands_today, key=lambda x: x['symbol']):
    flags = c.get('corruption_flags', [])
    inv   = c.get('invalidation_state', 'NONE')
    fc    = c.get('fallback_contaminated', False)
    if flags or inv not in ('NONE', None, '') or fc:
        sym  = c.get('symbol', '?')
        core = '[CORE]' if sym in all5 else '      '
        print(f'  {core} {sym:<14}  inv={inv}  flags={flags}  fallback={fc}')

print(f'  (Symbols with clean flags are omitted)')

# ── Wed→Thu anomaly deep-dive ─────────────────────────────────────────────
print(f'\n{SEP}')
print('5. WED→THU 87.7% TURNOVER ANOMALY')
print(SEP)

wed_set = sessions['2026-05-28']
thu_set = sessions['2026-05-29']
wed_to_thu_added   = thu_set - wed_set
wed_to_thu_removed = wed_set - thu_set
print(f'  Wed (May28): {len(wed_set)} symbols')
print(f'  Thu (May29): {len(thu_set)} symbols')
print(f'  Added Thu  : {len(wed_to_thu_added)}  (new in Thu)')
print(f'  Removed Thu: {len(wed_to_thu_removed)}  (dropped from Wed)')
print(f'\n  Symbols REMOVED (in Wed but not Thu):')
for sym in sorted(wed_to_thu_removed):
    in_today = '→ back today' if sym in today_set else ''
    in_fri   = '→ came back Fri' if sym in sessions['2026-05-30'] else ''
    came_back = in_today or in_fri or '(not since)'
    print(f'    {sym:<14} {came_back}')
print(f'\n  Symbols ADDED (new in Thu, not in Wed):')
for sym in sorted(wed_to_thu_added):
    in_today = '→ still today' if sym in today_set else '→ dropped again'
    print(f'    {sym:<14} {in_today}')

# Also check Tue vs Wed (0% turnover)
tue_set = sessions['2026-05-27']
wed_overlap = tue_set == wed_set
print(f'\n  Tue==Wed identical check: {wed_overlap}')
print(f'  Tue-only: {tue_set - wed_set}')
print(f'  Wed-only: {wed_set - tue_set}')

# ── 29 rotated-out symbols ─────────────────────────────────────────────────
print(f'\n{SEP}')
print('6. ROTATED-OUT SYMBOLS: PRIMARY REMOVAL ANALYSIS (29 symbols)')
print(SEP)

print(f'  Total ever-present symbols: {len(ever_present)}')
print(f'  In today: {len(today_set)},  Rotated out: {len(rotated_out)}')

# Session count for each rotated-out symbol
session_count = {}
for dk in DATE_KEYS:
    for sym in sessions[dk]:
        session_count[sym] = session_count.get(sym, 0) + 1

# Categorize rotated-out by last session they appeared in
print(f'\n  {"Symbol":<14} {"Sessions":>8}  {"LastSeen":<12}  {"Back after absence?"}')
print(f'  {"─"*65}')
for sym in sorted(rotated_out, key=lambda s: -session_count.get(s, 0)):
    cnt = session_count.get(sym, 0)
    last = max(dk for dk in DATE_KEYS if sym in sessions[dk])
    last_label = DAY_LABELS.get(last, last)
    # Characterize removal
    if cnt == 1:
        reason = 'one-time appearance'
    elif cnt == 2:
        reason = 'brief visitor'
    elif cnt >= 4:
        reason = 'STRONG DROP - was core'
    else:
        reason = 'regular churn'
    print(f'  {sym:<14} {cnt:>8}  {last_label} ({last})  {reason}')

# ── Score floor analysis ───────────────────────────────────────────────────
print(f'\n{SEP}')
print('7. SCORE FLOOR ANALYSIS (inferred from scanner stats)')
print(SEP)

stats_today = raw_today.get('scanner_stats', {})
print(f'  Scanner stats from today: {stats_today}')
# Score distribution of today's universe — is there a hard floor?
all_scores = sorted([c.get('score', 0) for c in cands_today])
print(f'\n  Score floor of today\'s universe: min={min(all_scores):.3f}  #below0.6={sum(1 for s in all_scores if s < 0.6)}')
print(f'  Score distribution:')
buckets = {'0.90+': 0, '0.80-0.89': 0, '0.70-0.79': 0, '0.60-0.69': 0, '0.50-0.59': 0, '<0.50': 0}
for s in all_scores:
    if s >= 0.90:      buckets['0.90+'] += 1
    elif s >= 0.80:    buckets['0.80-0.89'] += 1
    elif s >= 0.70:    buckets['0.70-0.79'] += 1
    elif s >= 0.60:    buckets['0.60-0.69'] += 1
    elif s >= 0.50:    buckets['0.50-0.59'] += 1
    else:              buckets['<0.50'] += 1
for b, n in buckets.items():
    bar = '█' * n
    print(f'    {b}: {n:>3}  {bar}')

# ── Inertia check: freshness_age_minutes ─────────────────────────────────
print(f'\n{SEP}')
print('8. FRESHNESS AGE ANALYSIS (indicator staleness per candidate)')
print(SEP)

ages = [(c['symbol'], c.get('freshness_age_minutes'), c.get('score', 0), c['symbol'] in all5)
        for c in cands_today if c.get('freshness_age_minutes') is not None]
if ages:
    core_ages  = [a[1] for a in ages if a[3] and a[1] is not None]
    other_ages = [a[1] for a in ages if not a[3] and a[1] is not None]
    print(f'  Core-25 avg freshness_age_min  : {sum(core_ages)/max(len(core_ages),1):.1f}')
    print(f'  Rotating avg freshness_age_min : {sum(other_ages)/max(len(other_ages),1):.1f}')
    old = sorted([(a[0], a[1], a[3]) for a in ages if a[1] and a[1] > 200], key=lambda x: -x[1])
    if old:
        print(f'\n  Symbols with freshness_age > 200 min:')
        for sym, age, is_core in old[:15]:
            tag = '[CORE]' if is_core else '      '
            print(f'    {tag} {sym:<14} age={age:.0f}min')
    print(f'\n  Full freshness age sample (first 20):')
    for sym, age, sc, is_core in sorted(ages, key=lambda x: -(x[1] or 0))[:20]:
        tag = '[CORE]' if is_core else '      '
        print(f'    {tag} {sym:<14}  freshness_age={age:.0f}min  score={sc:.3f}')
else:
    print('  freshness_age_minutes not populated.')

# ── Pull Wed→Thu container logs if available ─────────────────────────────
print(f'\n{SEP}')
print('9. CONTAINER LOG EVIDENCE FOR WED→THU ANOMALY')
print(SEP)

try:
    # 7 days of logs if available
    result = subprocess.run(
        ['docker', 'logs', 'ai-trading-brain', '--since', '120h', '--until', '72h'],
        capture_output=True, text=True, timeout=15
    )
    logs = (result.stdout + result.stderr).splitlines()
    relevant = [l for l in logs if any(t in l for t in [
        'ScannerRun', 'UniverseRebuild', 'CandidateStore', 'restart',
        'PreparedUniverseCap', 'PreparedUniverseStats', 'reset_reason',
        'REGIME_TRANSITION', 'regime_transition', 'EXPLORATION_STARV'
    ])]
    if relevant:
        print(f'  Found {len(relevant)} relevant log lines from ~May28-29:')
        for l in relevant[:30]:
            print(f'  {l}')
    else:
        print(f'  No logs available for that period (only last 24h stored).')
        print(f'  ({len(logs)} total lines fetched — all empty or irrelevant)')
except Exception as e:
    print(f'  Log fetch failed: {e}')

print(f'\n{SEP}')
print(f'Audit complete: {NOW_DT.strftime("%Y-%m-%d %H:%M:%S IST")}')
print(SEP)
