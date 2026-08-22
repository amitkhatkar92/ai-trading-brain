import sys
sys.path.insert(0, "/app")

from data_feeds.nse_feed import NSEFeed

nse = NSEFeed()
print("NSEFeed initialised, is_live:", nse.is_live)

chain = nse.get_options_chain("BANKNIFTY")
if chain:
    print("BANKNIFTY NSE chain is_live:", getattr(chain, "is_live", "?"))
    print("  spot:", chain.spot_price)
    print("  contracts:", len(chain.contracts))
    print("  pcr:", chain.pcr)
    print("  source:", getattr(chain, "source", "NSE"))
else:
    print("BANKNIFTY NSE chain: None (sim will be used)")

chain_n = nse.get_options_chain("NIFTY")
if chain_n:
    print("\nNIFTY NSE chain is_live:", getattr(chain_n, "is_live", "?"))
    print("  spot:", chain_n.spot_price)
    print("  contracts:", len(chain_n.contracts))
