"""
iios.ai
=======
IIOS AI Platform — Phase 3.

The AI Platform provides enterprise artificial intelligence capabilities
on top of the frozen IIOS Core Trading Platform V1.0.

Architecture
------------
A1  AI Foundation          ``iios.ai.foundation``
A2  Model Management       ``iios.ai.model_management``     (Phase 3, planned)
A3  Prompt & Context       ``iios.ai.prompt_context``       (Phase 3, planned)
A4  Memory & Knowledge     ``iios.ai.memory``               (Phase 3, planned)
A5  AI Agent Framework     ``iios.ai.agent``                (Phase 3, planned)
A6  Multi-Agent Collab     ``iios.ai.collaboration``        (Phase 3, planned)
A7  Learning & Evaluation  ``iios.ai.learning``             (Phase 3, planned)
A8  AI Governance          ``iios.ai.governance``           (Phase 3, planned)
A9  Tool & Skill Platform  ``iios.ai.tool_skill``           (Phase 3, planned)
A10 AI Orchestration       ``iios.ai.orchestration``        (Phase 3, planned)

Dependency policy
-----------------
All AI modules consume Core Platform services ONLY through frozen M6
gateway APIs.  No AI module imports from below M6 of any Core Platform
module.  No Core Platform module (C1–C16) depends on any AI module.
"""
from __future__ import annotations

__version__: str = "1.0.0-dev"
__all__: list[str] = []
