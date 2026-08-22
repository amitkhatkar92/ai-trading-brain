"""Fix wrong OptionsChain attribute names in data_feed_manager.py Phase 3 hooks."""
import sys

DFM = "/app/data_feeds/data_feed_manager.py"

# Helper block to insert once, then reference 3 times
HELPER = (
    "                import datetime as _dtt_oc\n"
    "                def _oc_meta(_c):\n"
    "                    _conts = getattr(_c, 'contracts', []) or []\n"
    "                    _cnt = len(_conts)\n"
    "                    _sp = getattr(_c, 'spot_price', 0) or 0\n"
    "                    _near = sorted(_conts, key=lambda x: abs(x.strike - _sp))[:4] if _sp and _conts else []\n"
    "                    _iv = round(sum(getattr(x,'iv',0) or 0 for x in _near)/max(1,len(_near)),2) if _near else 0.0\n"
    "                    _exp_s = str(getattr(_c,'expiry','') or '')\n"
    "                    _dte = 0\n"
    "                    if _exp_s:\n"
    "                        try: _dte = max(0,(_dtt_oc.datetime.strptime(_exp_s,'%d%b%y').date()-_dtt_oc.date.today()).days)\n"
    "                        except Exception: pass\n"
    "                    return _cnt, _iv, _dte, _exp_s\n"
)

with open(DFM) as f:
    src = f.read()

def do(old, new, label):
    if old not in src:
        print(f"  MISS [{label}]")
        return src
    return src.replace(old, new, 1)

# Fix 1: AngelOne record_options_chain call
OLD1 = (
    "                # Phase 3 — record AngelOne options chain success\n"
    "                _oc = live_chain\n"
    "                _get_ao_auditor().record_options_chain(\n"
    "                    symbol, \"ANGELONE\", True,\n"
    "                    contracts=getattr(_oc, \"contract_count\", 0) or len(getattr(_oc, \"strikes\", {})),\n"
    "                    atm_iv=getattr(_oc, \"atm_iv\", 0.0) or 0.0,\n"
    "                    dte=int(getattr(_oc, \"dte\", 0) or 0),\n"
    "                    expiry=str(getattr(_oc, \"expiry\", \"\") or \"\"),\n"
    "                )\n"
)
NEW1 = (
    "                # Phase 3 — record AngelOne options chain success\n"
    "                _oc = live_chain\n"
    + HELPER +
    "                _cnt1, _iv1, _dte1, _exp1 = _oc_meta(_oc)\n"
    "                _get_ao_auditor().record_options_chain(\n"
    "                    symbol, \"ANGELONE\", True,\n"
    "                    contracts=_cnt1, atm_iv=_iv1, dte=_dte1, expiry=_exp1,\n"
    "                )\n"
)

# Fix 2: Dhan record_options_chain call
OLD2 = (
    "                # Phase 3 — record Dhan options chain success\n"
    "                _dc = live_chain\n"
    "                _get_ao_auditor().record_options_chain(\n"
    "                    symbol, \"DHAN\", True,\n"
    "                    contracts=getattr(_dc, \"contract_count\", 0) or len(getattr(_dc, \"strikes\", {})),\n"
    "                    atm_iv=getattr(_dc, \"atm_iv\", 0.0) or 0.0,\n"
    "                    dte=int(getattr(_dc, \"dte\", 0) or 0),\n"
    "                    expiry=str(getattr(_dc, \"expiry\", \"\") or \"\"),\n"
    "                )\n"
)
NEW2 = (
    "                # Phase 3 — record Dhan options chain success\n"
    "                _dc = live_chain\n"
    + HELPER +
    "                _cnt2, _iv2, _dte2, _exp2 = _oc_meta(_dc)\n"
    "                _get_ao_auditor().record_options_chain(\n"
    "                    symbol, \"DHAN\", True,\n"
    "                    contracts=_cnt2, atm_iv=_iv2, dte=_dte2, expiry=_exp2,\n"
    "                )\n"
)

# Fix 3: emit_options_chain_readiness call
OLD3 = (
    "            # Phase 3 — emit OptionsChainReadiness one-liner\n"
    "            _lc = live_chain\n"
    "            _get_ao_auditor().emit_options_chain_readiness(\n"
    "                symbol, live_source,\n"
    "                contracts=getattr(_lc, \"contract_count\", 0) or len(getattr(_lc, \"strikes\", {})),\n"
    "                atm_iv=getattr(_lc, \"atm_iv\", 0.0) or 0.0,\n"
    "                dte=int(getattr(_lc, \"dte\", 0) or 0),\n"
    "                chain_live=True,\n"
    "            )\n"
)
NEW3 = (
    "            # Phase 3 — emit OptionsChainReadiness one-liner\n"
    "            _lc = live_chain\n"
    "            import datetime as _dtt_lc\n"
    "            def _lc_meta(_c):\n"
    "                _cn = getattr(_c,'contracts',[]) or []\n"
    "                _sp = getattr(_c,'spot_price',0) or 0\n"
    "                _nr = sorted(_cn,key=lambda x:abs(x.strike-_sp))[:4] if _sp and _cn else []\n"
    "                _iv_v = round(sum(getattr(x,'iv',0) or 0 for x in _nr)/max(1,len(_nr)),2) if _nr else 0.0\n"
    "                _exp_s = str(getattr(_c,'expiry','') or '')\n"
    "                _dte_v = 0\n"
    "                if _exp_s:\n"
    "                    try: _dte_v = max(0,(_dtt_lc.datetime.strptime(_exp_s,'%d%b%y').date()-_dtt_lc.date.today()).days)\n"
    "                    except Exception: pass\n"
    "                return len(_cn), _iv_v, _dte_v\n"
    "            _cnt3, _iv3, _dte3 = _lc_meta(_lc)\n"
    "            _get_ao_auditor().emit_options_chain_readiness(\n"
    "                symbol, live_source,\n"
    "                contracts=_cnt3, atm_iv=_iv3, dte=_dte3, chain_live=True,\n"
    "            )\n"
)

src = do(OLD1, NEW1, "AngelOne-record_options_chain")
src = do(OLD2, NEW2, "Dhan-record_options_chain")
src = do(OLD3, NEW3, "emit_options_chain_readiness")

with open(DFM, "w") as f:
    f.write(src)

print("Done")
