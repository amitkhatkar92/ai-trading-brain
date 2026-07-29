"""
iios.ai.model_management.core
================================
M4 Core Framework for A2 Model Management.
"""
from __future__ import annotations

from .ai_model        import AIModel
from .model_category  import ModelCategory
from .model_descriptor import AIModelDescriptor
from .model_metadata  import ModelMetadata
from .model_tier      import ModelTier
from .model_version   import AIModelVersion

__all__ = [
    "AIModel",
    "ModelCategory",
    "ModelTier",
    "ModelMetadata",
    "AIModelDescriptor",
    "AIModelVersion",
]
