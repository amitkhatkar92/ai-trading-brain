# Developer Guide — Knowledge Intelligence Framework

## Architecture

```
KnowledgeIntelligenceEngine (LifecycleAwareMixin) — primary façade
    └─ KnowledgeIntelligenceManager — 11-phase orchestrator (NEVER RAISES)
         ├─ EntityResolutionEngine   — Phase 2: entity extraction
         ├─ RelationshipEngine       — Phase 4: relationship discovery
         ├─ KnowledgeGraphBuilder    — Phase 5: graph population
         ├─ EmbeddingEngine          — Phase 6: embedding generation
         ├─ VectorStoreManager       — Phase 7: vector indexing
         ├─ KnowledgeEnrichmentEngine — Phase 8: artifact enrichment
         ├─ KnowledgeReasoningEngine — Phase 9: reasoning context
         └─ KnowledgeRecommendationEngine — Phase 10: recommendations
```

## Design Rules

1. **NEVER RAISES**: `KnowledgeIntelligenceManager.process()` catches all exceptions and returns failure responses.
2. **All value objects are frozen dataclasses** — `KnowledgeEntity`, `KnowledgeRelationship`, `EmbeddingVector`, `VectorSearchResult`, all response types.
3. **All stateful engines use `threading.Lock()`** — `KnowledgeGraph`, `VectorIndex`, `EmbeddingRegistry`, statistics, history.
4. **All adapters are Protocols** — pluggable at runtime, stubs work without any external service.
5. **Error codes use KIF prefix** — `KIF-000` through `KIF-009`.

## Adding a New Adapter

```python
from iios.knowledge.intelligence import EmbeddingProvider, EmbeddingEngine

class MyEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        return my_model.encode(text).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return my_model.encode_batch(texts).tolist()

    @property
    def dimension(self) -> int:
        return 768

    @property
    def model_name(self) -> str:
        return "my-model-v1"

engine.set_embedding_provider(MyEmbeddingProvider())
```

## File Structure

```
iios/knowledge/intelligence/
├── constants.py                     # Enums + constants
├── exceptions.py                    # KIF error hierarchy
├── knowledge_graph_engine.py        # KnowledgeEntity, KnowledgeRelationship, KnowledgeGraph
├── embedding_engine.py              # EmbeddingVector, EmbeddingEngine
├── vector_index_engine.py           # VectorIndex, VectorIndexEngine
├── knowledge_intelligence_context.py
├── knowledge_intelligence_request.py
├── knowledge_intelligence_response.py  # All output types
├── knowledge_graph_builder.py
├── knowledge_graph_registry.py
├── entity_resolution_engine.py
├── relationship_engine.py
├── semantic_analysis_engine.py
├── embedding_registry.py
├── vector_store_manager.py
├── retrieval_engine.py
├── hybrid_search_engine.py
├── reranking_engine.py
├── knowledge_similarity_engine.py
├── knowledge_clustering_engine.py
├── knowledge_reasoning_engine.py
├── knowledge_enrichment_engine.py
├── knowledge_memory_engine.py
├── knowledge_recommendation_engine.py
├── knowledge_intelligence_validator.py
├── knowledge_intelligence_statistics.py
├── knowledge_intelligence_history.py
├── knowledge_intelligence_events.py
├── knowledge_intelligence_factory.py
├── knowledge_intelligence_registry.py
├── knowledge_intelligence_manager.py
├── knowledge_intelligence_engine.py
└── __init__.py
```

## Testing

```powershell
# M4 only
.venv\Scripts\python.exe -m pytest tests/unit/knowledge/test_knowledge_intelligence_m4.py -v

# Full regression (supervisor + all knowledge modules)
.venv\Scripts\python.exe -m pytest tests/unit/supervisor/ tests/unit/knowledge/ --tb=short -q
```

## AuditLogger Pattern

```python
from iios.common.logging.audit_logger import get_audit_logger
from .constants import INTELLIGENCE_SYSTEM_ID, VERSION, ACTOR_SYSTEM

_audit = get_audit_logger(__name__, engine_id=INTELLIGENCE_SYSTEM_ID)

# In _on_start():
_audit.log_lifecycle_event(
    engine_id  = INTELLIGENCE_SYSTEM_ID,
    from_state = "stopped",
    to_state   = "running",
    version    = VERSION,
    actor      = ACTOR_SYSTEM,
)
```
