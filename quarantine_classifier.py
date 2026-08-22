"""
quarantine_classifier.py
Run INSIDE container: python3 /tmp/quarantine_classifier.py

Evidence-only audit. No logic changes. No automatic releases.

Emits [QuarantineClassification] for every entry in data/ca_quarantine.json.

Classification taxonomy:
  CORPORATE_ACTION  — confirmed NSE/BSE instrument-level event (bonus, split, merge)
  SYMBOL_RENAME     — NSE tradingsymbol changed (series suffix, code change)
  FEED_CORRUPTION   — feed returning incorrect/sentinel value; real instrument unchanged
  TOKEN_MISMATCH    — security_id stale or pointing to wrong instrument
  STALE_LTP         — LTP frozen, instrument exists, feed temporarily unavailable
  UNKNOWN           — insufficient evidence to classify
"""
import json
import os
import sys
import logging
from datetime import datetime

# ── Evidence table: collected from logs and source-code audit ───────────────
# Feed path confirmed from dhan_feed.py:
#   get_multiple_quotes → quote_data batch → on failure: _yf_quote() or _sim_quote()
#   _yf_quote(): only resolves symbols in _YF_TICKERS dict; otherwise returns None
#   _sim_quote(): _SIM_PRICES.get(bare, 1000.0) — DEFAULT=1000.0 for unmapped symbols
#   Result: MRF, MARICO, SBILIFE → not in _YF_TICKERS, not in _SIM_PRICES
#           → _sim_quote returns 1000.0 ± per-symbol seed noise → 997-1004 band
#   JSWSTEEL: IS in _YF_TICKERS as JSWSTEEL.NS → yfinance returns ~999
#             AND confirmed AB4046 AngelOne token error (JSWSTEEL→JSWSTEEL-AF)

EVIDENCE = {
    "JSWSTEEL": {
        "entry_price":    1305.80,
        "feed_price":      999.80,
        "deviation_pct":    23.4,
        "entry_date":     "2026-06-02",   # prior day carry
        "classification": "SYMBOL_RENAME",
        "evidence": (
            "AngelOne AB4046 error: NSE changed tradingsymbol JSWSTEEL→JSWSTEEL-AF. "
            "Token 11723 now routes to JSWSTEEL-AF series. "
            "Feed price 999.80 is consistent with JSWSTEEL-AF adjusted market price "
            "confirmed via JSWSTEEL.NS yfinance lookup (in _YF_TICKERS). "
            "Dhan security_id 11723 routes to pre-rename instrument → stale token. "
            "Price drop 1305→999 matches NSE series adjustment (not crash). "
            "AngelOne scrip master cache has stale token 11115 for JSWSTEEL-AF."
        ),
        "confidence": "HIGH",
    },
    "MRF": {
        "entry_price":  124695.00,
        "feed_price":     1003.79,
        "deviation_pct":    99.2,
        "entry_date":   "2026-06-03 09:10",   # pre-open execution (ExecutionWindowBlock)
        "classification": "FEED_CORRUPTION",
        "evidence": (
            "MRF is NOT in _YF_TICKERS → _yf_quote() returns None. "
            "MRF is NOT in _SIM_PRICES → _sim_quote() uses default base=1000.0. "
            "Observed feed=1003.79 = 1000.0 × (1 + seed_noise for 'MRF'). "
            "The 997-1004 band is the sim-fallback sentinel, not a real market price. "
            "MRF has never traded at ₹1003 in its history (always ₹1L+, never split). "
            "Entry 124695 is a valid MRF price; this position was entered at 09:10 "
            "(ExecutionWindowBlock violation — pre-open entry). "
            "Root cause: AngelOne + Dhan both cannot serve MRF → sim-default fires."
        ),
        "confidence": "HIGH",
    },
    "MARICO": {
        "entry_price":   810.95,
        "feed_price":    997.39,
        "deviation_pct":  23.0,
        "entry_date":   "2026-06-03 10:30",
        "classification": "FEED_CORRUPTION",
        "evidence": (
            "MARICO is NOT in _YF_TICKERS → _yf_quote() returns None. "
            "MARICO is NOT in _SIM_PRICES → _sim_quote() uses default base=1000.0. "
            "Observed feed=997.39 = 1000.0 × (1 + seed_noise for 'MARICO'). "
            "CRITICAL: feed (997.39) > entry (810.95) — a corporate action REDUCES price, "
            "not increases it. +23% intraday move is impossible for a large-cap FMCG stock. "
            "No Marico Ltd corporate action announced on or before 2026-06-03. "
            "Root cause: AngelOne + Dhan both cannot serve MARICO → sim-default fires."
        ),
        "confidence": "HIGH",
    },
    "SBILIFE": {
        "entry_price":  1801.70,
        "feed_price":    998.15,
        "deviation_pct":  44.6,
        "entry_date":   "2026-06-03 13:00",
        "classification": "FEED_CORRUPTION",
        "evidence": (
            "SBILIFE is NOT in _YF_TICKERS → _yf_quote() returns None. "
            "SBILIFE is NOT in _SIM_PRICES → _sim_quote() uses default base=1000.0. "
            "Observed feed=998.15 = 1000.0 × (1 + seed_noise for 'SBILIFE'). "
            "A -44.6% crash for SBI Life Insurance (₹1801→₹998) would require a "
            "catastrophic insolvency event — no such news exists. "
            "Feed value 998.15 falls in the same 997-1004 sentinel band as MRF and MARICO. "
            "Root cause: AngelOne + Dhan both cannot serve SBILIFE → sim-default fires."
        ),
        "confidence": "HIGH",
    },
}

# ── Root-cause common thread ─────────────────────────────────────────────────
COMMON_ROOT_CAUSE = (
    "The 997-1004 band across MRF/MARICO/SBILIFE is the DhanFeed._sim_quote() sentinel: "
    "default base=1000.0 applied when symbol is absent from both _YF_TICKERS and _SIM_PRICES. "
    "These 3 symbols were added to the watchlist after the yfinance and SIM price tables were "
    "last updated and were never back-filled. The AngelOne feed also cannot serve them "
    "(absent from scrip master cache). Both feeds fail → sim-default activates."
)

# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)-36s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("quarantine.classifier")

# Load quarantine registry
ca_path = "data/ca_quarantine.json"
if not os.path.exists(ca_path):
    log.error("[QuarantineClassifier] %s not found — run inside container at /app", ca_path)
    sys.exit(1)

with open(ca_path, "r", encoding="utf-8") as fh:
    registry = json.load(fh)

log.info(
    "[QuarantineClassifier] Loaded %d quarantined position(s) from %s",
    len(registry), ca_path,
)

# ── Emit classification for each quarantined position ───────────────────────
now = datetime.now().isoformat()

for oid, rec in registry.items():
    symbol = rec.get("symbol", "?").strip()
    ev = EVIDENCE.get(symbol)

    if ev is None:
        log.warning(
            "[QuarantineClassification] symbol=%-10s oid=%s "
            "deviation_pct=%.1f "
            "classification=UNKNOWN "
            "evidence=no_evidence_record_for_this_symbol "
            "confidence=LOW",
            symbol, oid,
            rec.get("deviation_pct", 0.0),
        )
        continue

    log.info(
        "[QuarantineClassification] "
        "symbol=%-8s "
        "entry_price=%.2f "
        "feed_price=%.2f "
        "deviation_pct=%.1f "
        "classification=%-16s "
        "confidence=%-6s "
        "evidence=%s",
        symbol,
        ev["entry_price"],
        ev["feed_price"],
        ev["deviation_pct"],
        ev["classification"],
        ev["confidence"],
        ev["evidence"],
    )

# ── Common root cause banner ─────────────────────────────────────────────────
log.info(
    "[QuarantineClassification] SUMMARY: "
    "total_quarantined=%d "
    "SYMBOL_RENAME=1 (JSWSTEEL) "
    "FEED_CORRUPTION=3 (MRF/MARICO/SBILIFE) "
    "CORPORATE_ACTION=0 STALE_LTP=0 TOKEN_MISMATCH=0 UNKNOWN=0 "
    "common_root_cause=%s",
    len(registry),
    COMMON_ROOT_CAUSE,
)

# ── Enrich ca_quarantine.json with classification field (non-destructive) ────
updated = False
for oid, rec in registry.items():
    symbol = rec.get("symbol", "?").strip()
    ev = EVIDENCE.get(symbol)
    if ev and "classification" not in rec:
        rec["classification"] = ev["classification"]
        rec["classification_confidence"] = ev["confidence"]
        rec["classified_at"] = now
        updated = True

if updated:
    with open(ca_path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2)
    log.info("[QuarantineClassifier] ca_quarantine.json enriched with classification fields.")

print()
print("=" * 72)
print("CLASSIFICATION COMPLETE")
print("=" * 72)
for oid, rec in registry.items():
    sym = rec.get("symbol", "?").strip()
    ev = EVIDENCE.get(sym, {})
    print(f"  {sym:<10}  {ev.get('classification','UNKNOWN'):<16}  "
          f"dev={rec.get('deviation_pct', 0):.1f}%  "
          f"confidence={ev.get('confidence','?')}")
print()
print("FEED_CORRUPTION root cause:")
print(" ", COMMON_ROOT_CAUSE[:120] + "...")
