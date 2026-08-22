import sys
sys.path.insert(0, '/app')
from data_feeds.data_feed_manager import get_feed_manager

fm = get_feed_manager()
ao = fm.angelone
print(f'AngelOne is_live={ao.is_live}')

chain = ao.get_options_chain('NIFTY')
if chain:
    print(f'NIFTY chain: contracts={len(chain.contracts)} spot={chain.spot_price:.0f} expiry={chain.expiry} pcr={chain.pcr:.2f}')
else:
    print('NIFTY chain: None')

chain2 = ao.get_options_chain('BANKNIFTY')
if chain2:
    print(f'BANKNIFTY chain: contracts={len(chain2.contracts)} spot={chain2.spot_price:.0f} expiry={chain2.expiry} pcr={chain2.pcr:.2f}')
else:
    print('BANKNIFTY chain: None')

# Also test via data_feed_manager.get_options_chain (the patched path)
print()
print('--- Via FeedManager.get_options_chain ---')
from data_feeds.options_feed import OptionsChain as _OC
fc = fm.get_options_chain('NIFTY')
if fc:
    print(f'FeedMgr NIFTY: source ok, contracts available')
else:
    print('FeedMgr NIFTY: None')

print('SMOKE TEST DONE')
