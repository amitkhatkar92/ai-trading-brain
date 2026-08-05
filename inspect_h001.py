import sys, logging, json
sys.path.insert(0, '.')
logging.disable(logging.CRITICAL)

from autonomous_research.knowledge_provider import KnowledgeProvider
from market_learning.idr_repository import IDRRepository
from pathlib import Path
from collections import Counter

kp  = KnowledgeProvider()
idr = IDRRepository()

# 1. Study-003 loser DNA patterns
study003 = json.loads(Path('data/ars_study_003.json').read_text())
stage5   = study003.get('stage5_loser_dna', {})
patterns = stage5.get('loser_dna_patterns', [])
print(f"Study-003 loser patterns: {len(patterns)}")
for p in patterns[:8]:
    eid   = p.get('edge_id', '?')
    conds = p.get('conditions', [])
    oos   = p.get('winner_mean', '?')
    conf  = p.get('confidence', '?')
    print(f"  edge={eid}  cond={conds[0] if conds else '?'}  oos={oos}  conf={conf}")

# 2. IDR loser DNA
loser_dna = [d for d in idr.list_active() if d.category == 'loser']
print(f"\nIDR loser DNA records: {len(loser_dna)}")
for d in loser_dna[:5]:
    meta  = d.metadata or {}
    conds = meta.get('conditions', [])
    print(f"  {d.id}  feat={d.feature_name}  dir={d.direction}  conf={d.confidence:.3f}  cond={conds[0] if conds else '?'}")

# 3. Feature record year coverage
features = kp.list_features()
years = Counter()
for f in features:
    ts = str(getattr(f, 'ts', ''))[:4]
    if ts.isdigit():
        years[ts] += 1
print(f"\nFeature records by year: {dict(sorted(years.items()))}")

# 4. Regime history year coverage
rh = kp.get_regime_history()
rh_years = Counter(str(getattr(r, 'ts', ''))[:4] for r in rh)
print(f"Regime history by year:  {dict(sorted(rh_years.items()))}")

# 5. Edge data year coverage
edges = kp.list_edges()
print(f"\nTotal edges: {len(edges)}")
e0 = edges[0] if edges else None
if e0:
    print(f"Edge sample fields: {[k for k in vars(e0).keys() if not k.startswith('_')][:12]}")
    lr = getattr(e0, 'last_tested', None) or getattr(e0, 'last_updated', None)
    print(f"Edge last_tested sample: {lr}")

# 6. Studies available
studies = kp.list_studies()
print(f"\nStudies: {len(studies)}")
for s in studies:
    sid  = getattr(s, 'study_id', '')
    name = getattr(s, 'title', '') or getattr(s, 'name', '')
    date = getattr(s, 'executed_at', '') or getattr(s, 'date', '')
    n    = getattr(s, 'n_observations', '')
    dr   = getattr(s, 'date_range', {}) or {}
    print(f"  {sid}: {name[:50]}  obs={n}  range={dr}")
