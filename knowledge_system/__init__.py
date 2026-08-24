"""knowledge_system — options-specific knowledge accumulation and research pipeline."""

from knowledge_system.options_knowledge_observer import (
    get_options_knowledge_observer,
    OptionsKnowledgeObserver,
)
from knowledge_system.options_opportunity_registry import (
    get_options_opportunity_registry,
    OptionsOpportunityRegistry,
)
from knowledge_system.options_feature_extractor import (
    extract_features,
    OptionsFeatureVector,
)
from knowledge_system.options_knowledge_store import (
    get_options_knowledge_store,
    OptionsKnowledgeStore,
    KnowledgeItem,
    KS_OBSERVED, KS_CANDIDATE, KS_VALIDATING,
    KS_VALIDATED, KS_AUTHENTICATED, KS_DEGRADED,
    KS_INVALIDATED, KS_RETIRED,
)
from knowledge_system.options_pattern_engine import (
    get_options_pattern_engine,
    OptionsPatternEngine,
    DiscoveredPattern,
)
from knowledge_system.options_hypothesis_engine import (
    get_options_hypothesis_engine,
    OptionsHypothesisEngine,
    ResearchHypothesis,
)
from knowledge_system.options_validator import (
    run_oos_validation,
    run_walk_forward,
    validate_with_raw_outcomes,
)
from knowledge_system.options_counterfactual_engine import (
    get_options_counterfactual_engine,
    OptionsCounterfactualEngine,
)
from knowledge_system.options_research_pipeline import (
    get_options_research_pipeline,
    OptionsResearchPipeline,
)
