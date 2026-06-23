import sys; sys.path.insert(0,'/app')
from oios.db.connection import get_connection
with get_connection() as c:
    q = lambda sql: c.execute(sql).fetchone()[0]
    print('market_leaders_daily   =', q('SELECT COUNT(*) FROM market_leaders_daily'))
    print('market_leader_features =', q('SELECT COUNT(*) FROM market_leader_features'))
    print('market_research_ctrl   =', q('SELECT COUNT(*) FROM market_research_controls'))
    print('feature_differentials  =', q('SELECT COUNT(*) FROM feature_differentials'))
    print('market_leader_outcomes =', q('SELECT COUNT(*) FROM market_leader_outcomes'))
    f = q('SELECT COUNT(*) FROM market_leader_features')
    d = q('SELECT COUNT(*) FROM feature_differentials')
    print('VERDICT:', 'FIXED_AND_VERIFIED' if f>0 and d>0 else 'FAILED')
