"""
iios.ai.prompt_context.core
=============================
Core domain models (M4 Core Framework) for the A3 Prompt & Context Platform.
"""
from __future__ import annotations

from .change_metadata   import ChangeMetadata
from .context_metadata  import ContextMetadata
from .context_priority  import ContextPriority
from .context_segment   import ContextSegment
from .prompt_category   import PromptCategory
from .prompt_metadata   import PromptMetadata
from .prompt_template   import PromptTemplate
from .prompt_variables  import PromptResult, PromptVariables
from .prompt_version    import PromptVersion
from .token_estimator   import estimate_tokens

__all__ = [
    "ChangeMetadata",
    "ContextMetadata",
    "ContextPriority",
    "ContextSegment",
    "PromptCategory",
    "PromptMetadata",
    "PromptTemplate",
    "PromptResult",
    "PromptVariables",
    "PromptVersion",
    "estimate_tokens",
]
