"""Fix _parse_option_chain to match actual Dhan API response structure."""
import sys

DHAN = "/app/data_feeds/dhan_feed.py"
HOST_DHAN = None  # will sync separately

with open(DHAN, "r") as f:
    src = f.read()

OLD = '''    def _parse_option_chain(symbol: str, resp: Any, expiry: str) -> Optional[OptionsChain]:
        """Parse Dhan option_chain response \u2192 OptionsChain."""
        if not resp:
            return None
        try:
            data    = resp if isinstance(resp, dict) else {}
            # Dhan option_chain returns {"data": {"CE": {...}, "PE": {...}}, "underlying_price": ...}
            spot    = float(data.get("underlying_price", data.get("spot_price", 22500)))
            ce_data = data.get("data", {}).get("CE", {})
            pe_data = data.get("data", {}).get("PE", {})
            contracts: List[OptionsContract] = []
            total_call_oi = total_put_oi = 0.0

            for strike_str, ce in ce_data.items():
                strike = float(strike_str)
                oi = float(ce.get("OI", ce.get("oi", 0)) or 0)
                total_call_oi += oi
                contracts.append(OptionsContract(
                    symbol      = symbol,
                    expiry      = expiry,
                    strike      = strike,
                    option_type = "CE",
                    ltp         = float(ce.get("last_price", ce.get("LTP", 0)) or 0),
                    iv          = float(ce.get("impliedVolatility", ce.get("iv", 0)) or 0),
                    delta       = float(ce.get("delta", 0) or 0),
                    gamma       = float(ce.get("gamma", 0) or 0),
                    theta       = float(ce.get("theta", 0) or 0),
                    vega        = float(ce.get("vega",  0) or 0),
                    oi          = oi,
                    volume      = float(ce.get("volume", 0) or 0),
                    bid         = float(ce.get("bid_price", 0) or 0),
                    ask         = float(ce.get("ask_price", 0) or 0),
                ))

            for strike_str, pe in pe_data.items():
                strike = float(strike_str)
                oi = float(pe.get("OI", pe.get("oi", 0)) or 0)
                total_put_oi += oi
                contracts.append(OptionsContract(
                    symbol      = symbol,
                    expiry      = expiry,
                    strike      = strike,
                    option_type = "PE",
                    ltp         = float(pe.get("last_price", pe.get("LTP", 0)) or 0),
                    iv          = float(pe.get("impliedVolatility", pe.get("iv", 0)) or 0),
                    delta       = float(pe.get("delta", 0) or 0),
                    gamma       = float(pe.get("gamma", 0) or 0),
                    theta       = float(pe.get("theta", 0) or 0),
                    vega        = float(pe.get("vega",  0) or 0),
                    oi          = oi,
                    volume      = float(pe.get("volume", 0) or 0),
                    bid         = float(pe.get("bid_price", 0) or 0),
                    ask         = float(pe.get("ask_price", 0) or 0),
                ))

            pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0.85
            return OptionsChain(
                underlying = symbol,
                expiry     = expiry,
                spot_price = spot,
                timestamp  = datetime.now(),
                contracts  = contracts,
                pcr        = pcr,
                total_oi   = total_call_oi + total_put_oi,
            )
        except Exception as exc:
            log.debug("[DhanFeed] _parse_option_chain error: %s", exc)
            return None'''

NEW = '''    def _parse_option_chain(symbol: str, resp: Any, expiry: str) -> Optional[OptionsChain]:
        """Parse Dhan option_chain response \u2192 OptionsChain.

        Actual Dhan API structure (verified May 2026):
          resp["data"]["data"]["last_price"]  = spot price
          resp["data"]["data"]["oc"]          = dict keyed by strike (float str)
            oc[strike] = {"ce": {...}, "pe": {...}}
              ce/pe keys: last_price, oi, implied_volatility, volume,
                          top_bid_price, top_ask_price,
                          greeks: {delta, theta, gamma, vega}
        """
        if not resp:
            return None
        try:
            raw   = resp if isinstance(resp, dict) else {}
            # Navigate nested structure
            inner = raw.get("data", raw)
            if isinstance(inner, dict) and "data" in inner:
                inner = inner["data"]
            spot  = float(inner.get("last_price", 22500) or 22500)
            oc    = inner.get("oc", {})
            if not isinstance(oc, dict):
                log.debug("[DhanFeed] _parse_option_chain: oc is not a dict, got %s", type(oc))
                return None

            contracts: List[OptionsContract] = []
            total_call_oi = total_put_oi = 0.0

            def _make_contract(strike: float, opt_type: str, d: dict) -> OptionsContract:
                greeks = d.get("greeks", {}) or {}
                return OptionsContract(
                    symbol      = symbol,
                    expiry      = expiry,
                    strike      = strike,
                    option_type = opt_type,
                    ltp         = float(d.get("last_price", 0) or 0),
                    iv          = float(d.get("implied_volatility", 0) or 0),
                    delta       = float(greeks.get("delta", 0) or 0),
                    gamma       = float(greeks.get("gamma", 0) or 0),
                    theta       = float(greeks.get("theta", 0) or 0),
                    vega        = float(greeks.get("vega",  0) or 0),
                    oi          = float(d.get("oi", 0) or 0),
                    volume      = float(d.get("volume", 0) or 0),
                    bid         = float(d.get("top_bid_price", 0) or 0),
                    ask         = float(d.get("top_ask_price", 0) or 0),
                )

            for strike_str, pair in oc.items():
                try:
                    strike = float(strike_str)
                except ValueError:
                    continue
                ce_d = pair.get("ce", {}) or {}
                pe_d = pair.get("pe", {}) or {}
                ce_oi = float(ce_d.get("oi", 0) or 0)
                pe_oi = float(pe_d.get("oi", 0) or 0)
                total_call_oi += ce_oi
                total_put_oi  += pe_oi
                contracts.append(_make_contract(strike, "CE", ce_d))
                contracts.append(_make_contract(strike, "PE", pe_d))

            pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0.85
            log.debug("[DhanFeed] Options chain: %d contracts  spot=%.2f  expiry=%s  PCR=%.2f",
                      len(contracts), spot, expiry, pcr)
            return OptionsChain(
                underlying = symbol,
                expiry     = expiry,
                spot_price = spot,
                timestamp  = datetime.now(),
                contracts  = contracts,
                pcr        = pcr,
                total_oi   = total_call_oi + total_put_oi,
            )
        except Exception as exc:
            log.debug("[DhanFeed] _parse_option_chain error: %s", exc)
            return None'''

if OLD not in src:
    print("ERROR: anchor not found")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(DHAN, "w") as f:
    f.write(src)
print("OK: _parse_option_chain fixed for actual Dhan API structure")
