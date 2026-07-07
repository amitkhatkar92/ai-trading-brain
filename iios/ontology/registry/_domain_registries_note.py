"""
iios/ontology/registry/entity_registry.py
iios/ontology/registry/relationship_registry.py
iios/ontology/registry/event_registry.py
iios/ontology/registry/observation_registry.py
iios/ontology/registry/knowledge_registry.py

Domain-specific registry views over the master OntologyRegistryManager.
Each file is a typed façade that filters the master registry to only
the types belonging to its namespace.
"""

# ─────────────────────────────────────────────────────────────────────────────
# NOTE: All five registries follow the same pattern.
# They are defined in separate files but documented together here.
# ─────────────────────────────────────────────────────────────────────────────
