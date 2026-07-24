# Knowledge Engine Guide

## Overview

The Knowledge Engine (`iios.knowledge.engine`) is responsible for coordinating
enterprise knowledge workflows.  It collects knowledge artifacts from IIOS
subsystems, validates them, dispatches to downstream frameworks, and publishes
knowledge snapshots.

## What the Engine Does

- **Initializes** knowledge sessions via M1 Knowledge Lifecycle
- **Collects** enterprise artifacts from any configured source
- **Validates** artifact structure and metadata
- **Classifies** knowledge by type and scope
- **Dispatches** to M3 Knowledge Governance Policy Framework
- **Dispatches** to M4 Knowledge Intelligence Framework
- **Publishes** KnowledgeSnapshot outputs
- **Maintains** pipeline history, statistics, and health

## What the Engine Does NOT Do

- No knowledge reasoning
- No semantic search
- No embedding generation or vector indexing
- No LLM inference
- No AI model invocation

## Knowledge Sources

| Source | Description |
|---|---|
| `execution_intelligence` | Execution engine data |
| `execution_recovery` | Recovery and resilience data |
| `execution_analytics` | Execution analytics output |
| `decision_intelligence` | Decision engine output |
| `portfolio_intelligence` | Portfolio intelligence data |
| `risk_intelligence` | Risk system data |
| `market_intelligence` | Market data and signals |
| `ai_supervisor` | AI Supervisor snapshots |
| `infrastructure` | Platform and infrastructure metadata |
| `enterprise` | Any other enterprise source |

## Workflow Phases

```
1  Validate Context        — structural validation of the incoming request
2  Initialize Session      — create a M1 lifecycle session
3  Start Collection        — enter COLLECTING state
4  Collect Artifacts       — gather from request.inputs + sources
5  Validate Artifacts      — artifact consistency checks
6  Classify                — classify by workflow type, source, priority
7  Dispatch                — invoke M3 (Governance) + M4 (Intelligence)
8  Build Snapshot          — construct KnowledgeSnapshot
9  Publish                 — mark session PUBLISHED
10 Complete                — finalize session and pipeline
```

## Statistics

| Counter | Description |
|---|---|
| `knowledge_sessions` | Total sessions created |
| `knowledge_artifacts_collected` | Total artifacts collected |
| `knowledge_sources` | Unique sources seen |
| `published_snapshots` | Snapshots published |
| `average_collection_time_ms` | Mean collection phase duration |
| `average_processing_time_ms` | Mean total processing time |
| `knowledge_throughput` | Artifacts per second |
