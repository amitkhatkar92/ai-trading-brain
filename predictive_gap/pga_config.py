"""predictive_gap/pga_config.py — PGA-001 configuration."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

PGA_DIR          = DATA / "pga"
CT_DB            = DATA / "control_tower.db"
DNA_DB           = DATA / "mls" / "institutional_dna.db"
EDE_FEATURES     = DATA / "ede_feature_db.json"
EDGES_FILE       = DATA / "discovered_edges.json"
UNIVERSE_FILE    = DATA / "nifty500_universe.json"
PAPER_TRADES_CSV = DATA / "paper_trade_log.csv"
HYP_REGISTRY     = DATA / "ars_hypothesis_registry.json"
STRATEGY_PERF    = DATA / "strategy_performance.json"

# Root cause labels
ROOT_CAUSES = [
    "Scanner",
    "PMCI",
    "CDS",
    "DNA",
    "Knowledge",
    "Research",
    "PortfolioConstraint",
    "RiskFilter",
    "MissingFeature",
    "MissingData",
    "MissingHistoricalPattern",
    "WrongThreshold",
    "ExternalEvent",
]

# Learning categories A–G
LEARNING_CATEGORIES = {
    "A": "Existing feature weight calibration",
    "B": "Existing knowledge insufficient confidence",
    "C": "Knowledge gap → Generate hypothesis",
    "D": "Research gap → Schedule ResearchCoordinator",
    "E": "DNA gap → Create candidate DNA",
    "F": "Historical gap → Schedule HKAP replay",
    "G": "Relationship gap → Schedule KDE",
}

# Scientific Director action labels
SD_ACTIONS = [
    "NoAction",
    "ReinforceKnowledge",
    "GenerateHypothesis",
    "GenerateResearch",
    "GenerateInfrastructureImprovement",
]


@dataclass
class PGAConfig:
    top_n: int = 5                   # top N gainers/losers to analyse
    min_move_pct: float = 1.0        # minimum % move to classify as significant
    predicted_threshold: float = 6.5 # IIOS confidence threshold for "predicted"
    dna_coverage_min: int = 3        # minimum DNA patterns for PREDICTABLE
    dry_run: bool = False            # if True, write no files
    max_symbols_for_price_fetch: int = 80  # limit yfinance batch size
