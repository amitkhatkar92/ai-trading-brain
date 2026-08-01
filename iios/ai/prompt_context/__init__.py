"""
iios.ai.prompt_context
=======================
A3 — Prompt & Context Platform.

Enterprise prompt engineering, context assembly, template versioning,
and prompt-execution preparation for the IIOS AI Platform.

This module constructs high-quality AI requests (rendered prompt text +
assembled context) *before* they are handed to A1 (AI Foundation) /
A2 (Model Management) for execution.  A3 never calls an LLM provider,
never executes prompts, and never performs orchestration.

Public entry point
-------------------
All external modules interact with A3 exclusively through the gateway::

    from iios.ai.prompt_context.gateway import PromptContextGateway

    gw = PromptContextGateway()
    gw.initialize()
    gw.start()

    gw.register_prompt("greeting", PromptCategory.SYSTEM, "Hello {{name}}!", variables=("name",))
    ctx = gw.build_context("session-1", "my.module").add_user("What is the regime?").build()
    result = gw.compose_prompt("greeting", {"name": "Trader"}, context=ctx)

Six-layer architecture
----------------------
M1 Lifecycle          -- iios.ai.prompt_context.lifecycle   (re-uses AILifecycleAwareMixin)
M2 Engine             -- iios.ai.prompt_context.context, .composer, .versioning
M3 Policy Framework   -- iios.ai.prompt_context.policy
M4 Core Framework     -- iios.ai.prompt_context.core, .registry, .validation, .events
M5 Snapshot           -- iios.ai.prompt_context.snapshot
M6 Gateway            -- iios.ai.prompt_context.gateway

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

VERSION = "1.0.0"

__version__ = "1.0.0"
