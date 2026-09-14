# Snapshot Schema Guide — C14 M5

## Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `snapshot_id` | str | auto | UUID4 prefixed with `snap-` |
| `knowledge_session_id` | str | ✅ | ID of the originating session |
| `knowledge_workflow_id` | str | ✅ | ID of the originating workflow |
| `enterprise_session_id` | str | ✅ | ID of the enterprise orchestration session |
| `knowledge_version` | str | ✅ | Semantic version of the knowledge represented |
| `framework_version` | str | auto | IIOS framework version |
| `snapshot_version` | str | auto | Schema version of this snapshot |
| `knowledge_scope` | KnowledgeScope | ✅ | LOCAL / REGIONAL / GLOBAL / ENTERPRISE |
| `knowledge_type` | KnowledgeType | ✅ | OPERATIONAL / ANALYTICAL / STRATEGIC / TACTICAL |
| `lifecycle_state` | str | ✅ | Current lifecycle state (e.g. `"active"`) |
| `governance_state` | str | ✅ | Governance compliance state (e.g. `"compliant"`) |
| `knowledge_state` | str | ✅ | Knowledge readiness (e.g. `"ready"`) |
| `snapshot_timestamp` | str | auto | ISO-8601 UTC timestamp when snapshot was taken |
| `created_at` | str | auto | ISO-8601 UTC creation timestamp |
| `updated_at` | str | auto | ISO-8601 UTC last update timestamp |
| `content_hash` | str | auto | SHA-256 of canonical content |
| `schema_version` | str | auto | `"1.0"` |
| `state` | SnapshotState | auto | BUILT / PUBLISHED / etc. |
| `version_tag` | SnapshotVersionTag | auto | STABLE / RELEASE / DRAFT / DEPRECATED |

## Summary sections

### KnowledgeSummary
| Field | Type | Description |
|---|---|---|
| `artifacts` | int | Count of knowledge artifacts |
| `sources` | tuple[str] | Source system names |
| `domains` | tuple[str] | Knowledge domains covered |
| `categories` | tuple[str] | Knowledge categories |
| `quality_score` | float | 0.0–1.0 quality score |
| `coverage_score` | float | 0.0–1.0 coverage score |
| `freshness_score` | float | 0.0–1.0 freshness score |
| `confidence_score` | float | 0.0–1.0 confidence score |
| `completeness_score` | float | 0.0–1.0 completeness score |

### GraphSummary
| Field | Type | Description |
|---|---|---|
| `graph_version` | str | Graph schema version |
| `total_nodes` | int | Total node count |
| `total_edges` | int | Total edge count |
| `entity_types` | tuple[str] | Distinct entity types |
| `relationship_types` | tuple[str] | Distinct relationship types |
| `connected_components` | int | Number of connected subgraphs |
| `graph_health` | str | Health label (e.g. `"healthy"`) |

### EmbeddingSummary
| Field | Type | Description |
|---|---|---|
| `provider` | str | Embedding provider name |
| `model` | str | Model name |
| `model_version` | str | Model version |
| `vector_dimensions` | int | Vector size |
| `embedding_count` | int | Embeddings computed |
| `embedding_health` | str | Health label |

### VectorIndexSummary
| Field | Type | Description |
|---|---|---|
| `vector_store` | str | Vector store type (e.g. `"in-memory"`) |
| `index_version` | str | Index version |
| `index_size` | int | Size of the index |
| `indexed_artifacts` | int | Artifacts indexed |
| `index_health` | str | Health label |

### RetrievalSummary
| Field | Type | Description |
|---|---|---|
| `strategy` | str | Retrieval strategy name |
| `hybrid_search_enabled` | bool | Whether hybrid search is on |
| `average_retrieval_ms` | float | Average retrieval latency |
| `quality_score` | float | 0.0–1.0 retrieval quality |

### RecommendationSummary
| Field | Type | Description |
|---|---|---|
| `recommendations_generated` | int | Count of recommendations |
| `categories` | tuple[str] | Recommendation categories |
| `confidence_score` | float | 0.0–1.0 |

### SnapshotMemorySummary
| Field | Type | Description |
|---|---|---|
| `memory_objects` | int | Count of memory objects |
| `memory_domains` | tuple[str] | Memory domains |
| `cross_subsystem_links` | int | Cross-subsystem memory links |
| `historical_references` | int | Historical snapshot references |

### SnapshotAudit
| Field | Type | Description |
|---|---|---|
| `governance_version` | str | Governance schema version |
| `graph_version` | str | Graph audit version |
| `embedding_version` | str | Embedding audit version |
| `validation_summary` | dict | Validation results per check |
| `audit_trail` | tuple | Ordered audit events |

### SnapshotStatistics (operational)
| Field | Type | Description |
|---|---|---|
| `processing_duration_ms` | float | Total processing time |
| `snapshot_size_bytes` | int | Snapshot object size estimate |
| `artifact_count` | int | Total artifacts processed |
| `entity_count` | int | Total entities extracted |
| `relationship_count` | int | Total relationships extracted |
| `embedding_count` | int | Total embeddings generated |
| `vector_count` | int | Total vectors stored |

## Integrity

The `content_hash` field holds a SHA-256 digest of the canonical content dict
(all fields except `content_hash` and `schema_version`), serialized as sorted
UTF-8 JSON.  Verify with `snapshot.verify_integrity()`.
