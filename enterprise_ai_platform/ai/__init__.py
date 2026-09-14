"""
enterprise_ai_platform.ai
=======
IIOS AI Platform — Phase 3.

The AI Platform provides enterprise artificial intelligence capabilities
on top of the frozen IIOS Core Trading Platform V1.0.

Architecture
------------
A1  AI Foundation          ``enterprise_ai_platform.ai.foundation``
A2  Model Management       ``enterprise_ai_platform.ai.model_management``     (Phase 3, planned)
A3  Prompt & Context       ``enterprise_ai_platform.ai.prompt_context``       (Phase 3, planned)
A4  Memory & Knowledge     ``enterprise_ai_platform.ai.memory``               (Phase 3, planned)
A5  AI Agent Framework     ``enterprise_ai_platform.ai.agent``                (Phase 3, planned)
A6  Multi-Agent Collab     ``enterprise_ai_platform.ai.collaboration``        (Phase 3, planned)
A7  Learning & Evaluation  ``enterprise_ai_platform.ai.learning``             (Phase 3, planned)
A8  AI Governance          ``enterprise_ai_platform.ai.governance``           (Phase 3, planned)
A9  Tool & Skill Platform  ``enterprise_ai_platform.ai.tool_skill``           (Phase 3, planned)
A10 AI Orchestration       ``enterprise_ai_platform.ai.orchestration``        (Phase 3, planned)

Dependency policy
-----------------
All AI modules consume Core Platform services ONLY through frozen M6
gateway APIs.  No AI module imports from below M6 of any Core Platform
module.  No Core Platform module (C1–C16) depends on any AI module.
"""
from __future__ import annotations

__version__: str = "1.0.0-dev"
__all__: list[str] = []
