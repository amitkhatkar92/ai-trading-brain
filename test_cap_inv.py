import sys; sys.path.insert(0, '/app')
from data_feeds.angelone_readiness_auditor import get_readiness_auditor
a = get_readiness_auditor()
a.record_request('ANGELONE', True, 45.0)
a.record_request('ANGELONE', True, 50.0)
a.record_options_chain('NIFTY', 'ANGELONE', True, contracts=448, atm_iv=0.0, dte=20, expiry='23JUN26', total_oi=1500000.0)
a.record_options_chain('BANKNIFTY', 'ANGELONE', True, contracts=808, atm_iv=0.0, dte=27, expiry='25JUN26', total_oi=890000.0)
inv = a._build_capability_inventory()
for cap, status, reason in inv:
    print(f"  {cap:<35} {status:<20} {reason}")
