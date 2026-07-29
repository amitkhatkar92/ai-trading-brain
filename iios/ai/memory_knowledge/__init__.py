"""
iios.ai.memory_knowledge
========================
A4 – Memory & Knowledge Platform
Phase 3, Module 4  |  Version 1.0.0

Six-layer architecture
----------------------
M1  Lifecycle     — re-exports A1 AILifecycleAwareMixin
M2  Engine        — MemoryManager, KnowledgeManager, RetrievalEngine, KnowledgeGraph
M3  Policy        — RetentionPolicy, RetrievalPolicy, RankingPolicy, PrivacyPolicy, ExpirationPolicy
M4  Core          — MemoryEntry, KnowledgeItem, MemoryScope, KnowledgeCategory, vector ABCs
M5  Snapshot      — MemoryKnowledgeSnapshot
M6  Gateway       — MemoryKnowledgeGateway (single public entry point)

Dependency rule
---------------
A4 imports from A1 (AILifecycleAwareMixin, AIException) only.
A4 does NOT import from A2 or A3.
"""

VERSION = "1.0.0"
