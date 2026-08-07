"""production_readiness/prr_config.py — PRR-001 configuration constants."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

PRR_DIR              = DATA / "prr"
REPORT_DIR           = PRR_DIR / "reports"
EDGE_GATE_LOG        = PRR_DIR / "edge_gate_log.json"
SIGNAL_FRESHNESS_LOG = PRR_DIR / "signal_freshness_log.json"
UNIVERSE_CACHE       = PRR_DIR / "universe_cache.json"
KNOWLEDGE_VALIDITY   = PRR_DIR / "knowledge_validity.json"

# ── Phase 1: Edge lifecycle ────────────────────────────────────────────────
EDGE_STATUS_FULL        = "ACTIVE"      # 100% contribution
EDGE_STATUS_CANDIDATE   = "CANDIDATE"   # current behaviour (no change)
EDGE_STATUS_DECAYING    = "DECAYING"    # zero contribution (blocked)
EDGE_STATUS_RETIRED     = "RETIRED"     # never used

BLOCKED_EDGE_STATUSES   = {EDGE_STATUS_DECAYING, EDGE_STATUS_RETIRED}
# Configurable: set to a negative float to add a confidence penalty from DECAYING edges
DECAYING_EDGE_CONTRIBUTION = 0.0

# ── Phase 2: SHORT DNA ─────────────────────────────────────────────────────
LOSER_DNA_CONFIDENCE_GATE    = 0.55    # minimum confidence to use loser DNA for SHORT
LOSER_DNA_MAX_BOOST          = 1.50    # maximum confidence boost to SHORT from DNA match
DNA_DB                       = DATA / "mls" / "institutional_dna.db"

# ── Phase 3: Signal freshness ──────────────────────────────────────────────
FRESHNESS_FRESH_MAX_DAYS     = 5       # 0–5 trading days: FRESH
FRESHNESS_WEAKENING_MAX_DAYS = 15      # 6–15: WEAKENING
# 15+: EXPIRED — must never enter live execution

FRESHNESS_STATUS_FRESH       = "FRESH"
FRESHNESS_STATUS_WEAKENING   = "WEAKENING"
FRESHNESS_STATUS_EXPIRED     = "EXPIRED"

# ── Phase 4: Automatic universe ────────────────────────────────────────────
UNIVERSE_FILE                = DATA / "nifty500_universe.json"
MIN_ADV_CRORE_AUTO           = 50.0    # ₹50 Cr daily liquidity minimum
MIN_HISTORY_DAYS             = 252     # 1 trading year required
UNIVERSE_REFRESH_INTERVAL_H  = 24     # re-evaluate eligibility every 24 h

# ── Phase 5: Daily pipeline ────────────────────────────────────────────────
PIPELINE_TIMEOUT_EACH_S      = 300    # max seconds per pipeline stage
PIPELINE_CONTINUE_ON_FAILURE = True   # failure of one stage never stops the rest

# ── Phase 6: Knowledge validity ────────────────────────────────────────────
DNA_STALE_THRESHOLD_DAYS      = 90    # DNA not seen in 90 days → stale
EDGE_STALE_THRESHOLD_DAYS     = 60    # edge not updated in 60 days → stale
HYPOTHESIS_STALE_THRESHOLD_DAYS = 180 # hypothesis not reviewed in 180 days → stale
STALE_KNOWLEDGE_TRADING_BLOCK = True  # stale knowledge may not influence live signals

# ── Phase 7: Missed opportunity classifications ───────────────────────────
MISS_CORRECTLY_IGNORED   = "Correctly_Ignored"
MISS_UNIVERSE_LIMITATION = "Universe_Limitation"
MISS_KNOWLEDGE_LIMITATION = "Knowledge_Limitation"
MISS_RESEARCH_LIMITATION = "Research_Limitation"
MISS_THRESHOLD_LIMITATION = "Threshold_Limitation"
MISS_RISK_LIMITATION      = "Risk_Limitation"
MISS_PORTFOLIO_LIMITATION = "Portfolio_Limitation"
MISS_EXTERNAL_EVENT       = "External_Event"

# Only these three types trigger learning
LEARNING_TRIGGERING_MISSES = {
    MISS_KNOWLEDGE_LIMITATION,
    MISS_RESEARCH_LIMITATION,
    MISS_THRESHOLD_LIMITATION,
}

# ── Phase 9: Certification ─────────────────────────────────────────────────
CERT_PRODUCTION_READY      = "PRODUCTION_READY"
CERT_READY_WITH_OBS        = "PRODUCTION_READY_WITH_OBSERVATIONS"
CERT_NOT_READY             = "NOT_READY"
