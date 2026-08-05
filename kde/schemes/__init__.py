"""KDE discovery schemes — auto-registration package."""
from .s001_winner_dna                 import WinnerDNAScheme
from .s002_loser_dna                  import LoserDNAScheme
from .s003_hidden_feature_interaction import HiddenFeatureInteractionScheme
from .s004_feature_stability          import FeatureStabilityScheme
from .s005_sector_rotation            import SectorRotationScheme
from .s006_regime_behaviour           import RegimeBehaviourScheme
from .s007_market_personality         import MarketPersonalityScheme
from .s008_behaviour_clustering       import BehaviourClusteringScheme
from .s009_dna_evolution              import DNAEvolutionScheme
from .s010_edge_evolution             import EdgeEvolutionScheme
from .s011_failure_analysis           import FailureAnalysisScheme
from .s012_institutional_activity     import InstitutionalActivityScheme
from .s013_feature_importance         import FeatureImportanceScheme
from .s014_cross_year_persistence     import CrossYearPersistenceScheme
from .s015_context_dependency         import ContextDependencyScheme

ALL_SCHEMES = [
    WinnerDNAScheme,
    LoserDNAScheme,
    HiddenFeatureInteractionScheme,
    FeatureStabilityScheme,
    SectorRotationScheme,
    RegimeBehaviourScheme,
    MarketPersonalityScheme,
    BehaviourClusteringScheme,
    DNAEvolutionScheme,
    EdgeEvolutionScheme,
    FailureAnalysisScheme,
    InstitutionalActivityScheme,
    FeatureImportanceScheme,
    CrossYearPersistenceScheme,
    ContextDependencyScheme,
]

__all__ = [
    "ALL_SCHEMES",
    "WinnerDNAScheme",
    "LoserDNAScheme",
    "HiddenFeatureInteractionScheme",
    "FeatureStabilityScheme",
    "SectorRotationScheme",
    "RegimeBehaviourScheme",
    "MarketPersonalityScheme",
    "BehaviourClusteringScheme",
    "DNAEvolutionScheme",
    "EdgeEvolutionScheme",
    "FailureAnalysisScheme",
    "InstitutionalActivityScheme",
    "FeatureImportanceScheme",
    "CrossYearPersistenceScheme",
    "ContextDependencyScheme",
]
