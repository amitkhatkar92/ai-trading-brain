"""
Patch: AngelOne Readiness Auditor hooks.
Applies to:
  1. data_feeds/data_feed_manager.py  — Phase 1 (FeedComparison), Phase 2 (LTP shadow trigger),
                                        Phase 3 (OptionsChain), Phase 6 (failures)
  2. orchestrator/master_orchestrator.py — Phase 7 EOD report
"""
import sys

def patch_file(path, old, new, label):
    with open(path) as f:
        src = f.read()
    if old not in src:
        print(f"  MISS [{label}] — pattern not found in {path}")
        return False
    cnt = src.count(old)
    if cnt > 1:
        print(f"  WARN [{label}] — {cnt} occurrences, patching first only")
    src2 = src.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(src2)
    print(f"  OK   [{label}]")
    return True

results = []
DFM = "/app/data_feeds/data_feed_manager.py"
MO  = "/app/orchestrator/master_orchestrator.py"

# ─── DFM: Add auditor import at top ──────────────────────────────────────────
results.append(patch_file(DFM,
    'from .dhan_feed     import DhanFeed\n'
    'from .angelone_feed import AngelOneFeed\n',

    'from .dhan_feed     import DhanFeed\n'
    'from .angelone_feed import AngelOneFeed\n'
    'from .angelone_readiness_auditor import get_readiness_auditor as _get_ao_auditor\n',
    "DFM-import-auditor",
))

# ─── DFM Phase 1: Hook get_quote — record per-request source + latency ────────
results.append(patch_file(DFM,
    '    def get_quote(self, symbol: str) -> Optional[TickerQuote]:\n'
    '        """Get a market quote. Indian symbols: AngelOne → Dhan → Yahoo. Global: Yahoo."""\n'
    '        bare = symbol.upper().replace(".NS", "").replace(".BO", "")\n'
    '        if bare not in self._GLOBAL_SYMBOLS:\n'
    '            # AngelOne: primary Indian data source (TOTP auto-refresh, no daily token)\n'
    '            if self.angelone.is_live:\n'
    '                q = self.angelone.get_quote(bare)\n'
    '                if q and q.ltp > 0:\n'
    '                    self._stats.record(q)\n'
    '                    return q\n'
    '            # Dhan: fallback for Indian symbols\n'
    '            from .dhan_feed import DHAN_SECURITY_MAP\n'
    '            if self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP:\n'
    '                q = self.dhan.get_quote(symbol)\n'
    '                if q and q.ltp > 0:\n'
    '                    self._stats.record(q)\n'
    '                    return q\n'
    '        q = self.yahoo.get_quote(symbol)\n'
    '        self._stats.record(q)\n'
    '        return q\n',

    '    def get_quote(self, symbol: str) -> Optional[TickerQuote]:\n'
    '        """Get a market quote. Indian symbols: AngelOne → Dhan → Yahoo. Global: Yahoo."""\n'
    '        import time as _qt\n'
    '        bare = symbol.upper().replace(".NS", "").replace(".BO", "")\n'
    '        if bare not in self._GLOBAL_SYMBOLS:\n'
    '            # AngelOne: primary Indian data source (TOTP auto-refresh, no daily token)\n'
    '            if self.angelone.is_live:\n'
    '                _t0 = _qt.monotonic()\n'
    '                q = self.angelone.get_quote(bare)\n'
    '                _ms = (_qt.monotonic() - _t0) * 1000\n'
    '                _ok = bool(q and q.ltp > 0)\n'
    '                _get_ao_auditor().record_request("ANGELONE", _ok, _ms)\n'
    '                if _ok:\n'
    '                    self._stats.record(q)\n'
    '                    return q\n'
    '            # Dhan: fallback for Indian symbols\n'
    '            from .dhan_feed import DHAN_SECURITY_MAP\n'
    '            if self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP:\n'
    '                _t0 = _qt.monotonic()\n'
    '                q = self.dhan.get_quote(symbol)\n'
    '                _ms = (_qt.monotonic() - _t0) * 1000\n'
    '                _ok = bool(q and q.ltp > 0)\n'
    '                _get_ao_auditor().record_request("DHAN", _ok, _ms)\n'
    '                if _ok:\n'
    '                    self._stats.record(q)\n'
    '                    return q\n'
    '        q = self.yahoo.get_quote(symbol)\n'
    '        self._stats.record(q)\n'
    '        return q\n',
    "DFM-Phase1-get_quote",
))

# ─── DFM Phase 1+2: Hook get_multiple_quotes — FeedComparison + LTP shadow ───
results.append(patch_file(DFM,
    '        # ── AngelOne: primary for all Indian symbols ─────────────────────────\n'
    '        if self.angelone.is_live and indian:\n'
    '            ao_result = self.angelone.get_multiple_quotes(indian)\n'
    '            result.update(ao_result)\n'
    '            ao_missed = [s for s in indian if s not in ao_result]\n'
    '            log.debug("[FeedTrace] stage=ANGELONE_RAW requested=%d returned=%d missed=%d",\n'
    '                      len(indian), len(ao_result), len(ao_missed))\n'
    '        else:\n'
    '            ao_missed = indian\n'
    '\n'
    '        # ── Dhan: fallback for what AngelOne missed ───────────────────────────\n'
    '        if ao_missed and self.dhan.is_live:\n'
    '            from .dhan_feed import DHAN_SECURITY_MAP\n'
    '            dhan_candidates = [s for s in ao_missed if _bare(s) in DHAN_SECURITY_MAP]\n'
    '            if dhan_candidates:\n'
    '                dhan_result = self.dhan.get_multiple_quotes(dhan_candidates)\n'
    '                result.update(dhan_result)\n'
    '                log.debug("[FeedTrace] stage=DHAN_FALLBACK requested=%d returned=%d",\n'
    '                          len(dhan_candidates), len(dhan_result))\n'
    '                ao_missed = [s for s in ao_missed if s not in dhan_result]\n',

    '        # ── AngelOne: primary for all Indian symbols ─────────────────────────\n'
    '        if self.angelone.is_live and indian:\n'
    '            _ao_t0 = _t.monotonic()\n'
    '            ao_result = self.angelone.get_multiple_quotes(indian)\n'
    '            _ao_ms = (_t.monotonic() - _ao_t0) * 1000\n'
    '            result.update(ao_result)\n'
    '            ao_missed = [s for s in indian if s not in ao_result]\n'
    '            # Phase 1 — record AngelOne batch hit rate\n'
    '            _ao_aud = _get_ao_auditor()\n'
    '            for _s in indian:\n'
    '                _q = ao_result.get(_s)\n'
    '                _ok = bool(_q and getattr(_q, "ltp", 0) > 0)\n'
    '                _ao_aud.record_request("ANGELONE", _ok, _ao_ms / max(1, len(indian)))\n'
    '            # Phase 2 — trigger background LTP shadow comparison\n'
    '            _ao_aud.trigger_ltp_shadow([s for s in indian if s in ao_result])\n'
    '            log.debug("[FeedTrace] stage=ANGELONE_RAW requested=%d returned=%d missed=%d",\n'
    '                      len(indian), len(ao_result), len(ao_missed))\n'
    '        else:\n'
    '            ao_missed = indian\n'
    '\n'
    '        # ── Dhan: fallback for what AngelOne missed ───────────────────────────\n'
    '        if ao_missed and self.dhan.is_live:\n'
    '            from .dhan_feed import DHAN_SECURITY_MAP\n'
    '            dhan_candidates = [s for s in ao_missed if _bare(s) in DHAN_SECURITY_MAP]\n'
    '            if dhan_candidates:\n'
    '                _dh_t0 = _t.monotonic()\n'
    '                dhan_result = self.dhan.get_multiple_quotes(dhan_candidates)\n'
    '                _dh_ms = (_t.monotonic() - _dh_t0) * 1000\n'
    '                result.update(dhan_result)\n'
    '                _ao_aud2 = _get_ao_auditor()\n'
    '                for _s in dhan_candidates:\n'
    '                    _q = dhan_result.get(_s)\n'
    '                    _ok = bool(_q and getattr(_q, "ltp", 0) > 0)\n'
    '                    _ao_aud2.record_request("DHAN", _ok, _dh_ms / max(1, len(dhan_candidates)))\n'
    '                log.debug("[FeedTrace] stage=DHAN_FALLBACK requested=%d returned=%d",\n'
    '                          len(dhan_candidates), len(dhan_result))\n'
    '                ao_missed = [s for s in ao_missed if s not in dhan_result]\n',
    "DFM-Phase1+2-get_multiple_quotes",
))

# ─── DFM Phase 3: Hook options chain — record per source after each fetch ─────
results.append(patch_file(DFM,
    '        live_chain, live_source = None, None\n'
    '        try:\n'
    '            live_chain = self.angelone.get_options_chain(symbol, expiry)\n'
    '            if live_chain:\n'
    '                live_source = "ANGELONE"\n'
    '        except Exception as _ao_exc:\n'
    '            log.debug("[FeedManager] AngelOne options chain %s failed: %s", symbol, _ao_exc)\n'
    '\n'
    '        # ── Try Dhan live chain (fallback) ────────────────────────────\n'
    '        if live_chain is None and self.dhan.is_live:\n'
    '            live_chain = self.dhan.get_options_chain(symbol, expiry)\n'
    '            if live_chain:\n'
    '                live_source = "DHAN"\n',

    '        live_chain, live_source = None, None\n'
    '        try:\n'
    '            live_chain = self.angelone.get_options_chain(symbol, expiry)\n'
    '            if live_chain:\n'
    '                live_source = "ANGELONE"\n'
    '                # Phase 3 — record AngelOne options chain success\n'
    '                _oc = live_chain\n'
    '                _get_ao_auditor().record_options_chain(\n'
    '                    symbol, "ANGELONE", True,\n'
    '                    contracts=getattr(_oc, "contract_count", 0) or len(getattr(_oc, "strikes", {})),\n'
    '                    atm_iv=getattr(_oc, "atm_iv", 0.0) or 0.0,\n'
    '                    dte=int(getattr(_oc, "dte", 0) or 0),\n'
    '                    expiry=str(getattr(_oc, "expiry", "") or ""),\n'
    '                )\n'
    '            else:\n'
    '                _get_ao_auditor().record_options_chain(symbol, "ANGELONE", False)\n'
    '        except Exception as _ao_exc:\n'
    '            _get_ao_auditor().record_options_chain(symbol, "ANGELONE", False)\n'
    '            _get_ao_auditor().record_failure("ANGELONE", "timeout" if "timeout" in str(_ao_exc).lower() else "empty")\n'
    '            log.debug("[FeedManager] AngelOne options chain %s failed: %s", symbol, _ao_exc)\n'
    '\n'
    '        # ── Try Dhan live chain (fallback) ────────────────────────────\n'
    '        if live_chain is None and self.dhan.is_live:\n'
    '            live_chain = self.dhan.get_options_chain(symbol, expiry)\n'
    '            if live_chain:\n'
    '                live_source = "DHAN"\n'
    '                # Phase 3 — record Dhan options chain success\n'
    '                _dc = live_chain\n'
    '                _get_ao_auditor().record_options_chain(\n'
    '                    symbol, "DHAN", True,\n'
    '                    contracts=getattr(_dc, "contract_count", 0) or len(getattr(_dc, "strikes", {})),\n'
    '                    atm_iv=getattr(_dc, "atm_iv", 0.0) or 0.0,\n'
    '                    dte=int(getattr(_dc, "dte", 0) or 0),\n'
    '                    expiry=str(getattr(_dc, "expiry", "") or ""),\n'
    '                )\n'
    '            else:\n'
    '                _get_ao_auditor().record_options_chain(symbol, "DHAN", False)\n',
    "DFM-Phase3-options-chain",
))

# ─── DFM Phase 3: emit OptionsChainReadiness after live_chain is confirmed ────
results.append(patch_file(DFM,
    '        if live_chain is not None:\n'
    '            self._options_chain_state[symbol] = {\n'
    '                "chain": live_chain, "fetched_at": now,\n'
    '                "source": live_source, "is_live": True,\n'
    '            }\n'
    '            self._options_synthetic = False\n'
    '            log.info(\n'
    '                "[OptionsTruth] symbol=%s source=%s state=LIVE",\n'
    '                symbol, live_source,\n'
    '            )\n'
    '            return live_chain\n',

    '        if live_chain is not None:\n'
    '            self._options_chain_state[symbol] = {\n'
    '                "chain": live_chain, "fetched_at": now,\n'
    '                "source": live_source, "is_live": True,\n'
    '            }\n'
    '            self._options_synthetic = False\n'
    '            log.info(\n'
    '                "[OptionsTruth] symbol=%s source=%s state=LIVE",\n'
    '                symbol, live_source,\n'
    '            )\n'
    '            # Phase 3 — emit OptionsChainReadiness one-liner\n'
    '            _lc = live_chain\n'
    '            _get_ao_auditor().emit_options_chain_readiness(\n'
    '                symbol, live_source,\n'
    '                contracts=getattr(_lc, "contract_count", 0) or len(getattr(_lc, "strikes", {})),\n'
    '                atm_iv=getattr(_lc, "atm_iv", 0.0) or 0.0,\n'
    '                dte=int(getattr(_lc, "dte", 0) or 0),\n'
    '                chain_live=True,\n'
    '            )\n'
    '            return live_chain\n',
    "DFM-Phase3-emit-readiness",
))

# ─── MO: Phase 4 (CandidateParityAudit) + Phase 7 at EOD ─────────────────────
# Phase 4 hook — at the end of _do_eod_learning, before invalidation summary
results.append(patch_file(MO,
    '        # ── InvalidationEffectivenessReport: 5-section EOD invalidation summary ──\n'
    '        # Crosses persistent invalidation_state.json with current store to\n'
    '        # classify genuine vs feed-induced, recovery rates, and recurring symbols.\n'
    '        try:\n'
    '            from opportunity_engine.invalidation_tracker import get_invalidation_tracker as _git_eod\n'
    '            _git_eod().emit_session_summary()\n'
    '        except Exception as _inv_eod_exc:\n'
    '            log.debug("[InvalidationEffectivenessReport] Skipped: %s", _inv_eod_exc)\n',

    '        # ── AngelOneReadinessReport (Phase 7) — Dhan exit readiness ──────────\n'
    '        try:\n'
    '            from data_feeds.angelone_readiness_auditor import get_readiness_auditor as _gara\n'
    '            _ara = _gara()\n'
    '            # Phase 4 — candidate parity using today\'s prepared universe\n'
    '            try:\n'
    '                from opportunity_engine.candidate_store import CandidateStore as _CS\n'
    '                _cands_eod = _CS.read() or []\n'
    '                if _cands_eod:\n'
    '                    _ara.record_candidate_parity(_cands_eod)\n'
    '            except Exception as _p4_exc:\n'
    '                log.debug("[AngelOneReadiness] Phase4 candidate parity: %s", _p4_exc)\n'
    '            # Phase 1 + 6 aggregate\n'
    '            _ara.emit_feed_comparison_audit()\n'
    '            _ara.emit_feed_reliability_audit()\n'
    '            # Phase 7 — full EOD readiness report\n'
    '            _ara.emit_readiness_report()\n'
    '        except Exception as _ara_exc:\n'
    '            log.debug("[AngelOneReadinessReport] Skipped: %s", _ara_exc)\n'
    '\n'
    '        # ── InvalidationEffectivenessReport: 5-section EOD invalidation summary ──\n'
    '        # Crosses persistent invalidation_state.json with current store to\n'
    '        # classify genuine vs feed-induced, recovery rates, and recurring symbols.\n'
    '        try:\n'
    '            from opportunity_engine.invalidation_tracker import get_invalidation_tracker as _git_eod\n'
    '            _git_eod().emit_session_summary()\n'
    '        except Exception as _inv_eod_exc:\n'
    '            log.debug("[InvalidationEffectivenessReport] Skipped: %s", _inv_eod_exc)\n',
    "MO-Phase7-EOD-report",
))

# ─── MO: Phase 5 — signal parity hook in run_full_cycle where signals are used ─
# Hook into the debate/decision output — simpler: hook in equity_scanner_ai
# when a candidate is presented to the debate engine
# Actually the cleanest hook is in order_manager or decision engine signal emit.
# Let's do a lightweight hook in the scan() path where signals are reported.
# Phase 5 is best served by Phase 2's LTP shadow + a summary at EOD.
# The signal hook would require touching protected debate code — skip for now
# and note in the readiness report that Phase 5 is derived from Phase 2.

ok = sum(1 for r in results if r)
fail = sum(1 for r in results if not r)
print(f"\nPatches applied: {ok} OK, {fail} FAILED")
if fail:
    sys.exit(1)
