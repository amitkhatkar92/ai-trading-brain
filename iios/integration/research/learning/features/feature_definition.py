"""features/feature_definition.py — Feature definition and typing."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import FeatureType


@dataclass
class FeatureDefinition:
    """
    Describes a single named feature.

    This is entirely model-agnostic metadata — it does NOT encode transformation
    logic. Transformation is handled by FeatureTransformer/FeaturePipeline.
    """
    feature_id:   str
    name:         str
    feature_type: FeatureType
    description:  Optional[str]
    required:     bool
    default:      Optional[Any]
    min_value:    Optional[float]   # numeric only
    max_value:    Optional[float]   # numeric only
    allowed_vals: list[Any]         # categorical allowed values (empty = any)
    tags:         list[str]
    created_at:   float
    metadata:     dict[str, Any]

    @classmethod
    def create(
        cls,
        name:         str,
        feature_type: FeatureType     = FeatureType.NUMERIC,
        *,
        feature_id:   Optional[str]   = None,
        description:  Optional[str]   = None,
        required:     bool            = True,
        default:      Optional[Any]   = None,
        min_value:    Optional[float] = None,
        max_value:    Optional[float] = None,
        allowed_vals: Optional[list]  = None,
        tags:         Optional[list]  = None,
    ) -> "FeatureDefinition":
        return cls(
            feature_id   = feature_id or f"feat_{uuid.uuid4().hex[:10]}",
            name         = name,
            feature_type = feature_type,
            description  = description,
            required     = required,
            default      = default,
            min_value    = min_value,
            max_value    = max_value,
            allowed_vals = allowed_vals or [],
            tags         = tags or [],
            created_at   = time.time(),
            metadata     = {},
        )

    def validate_value(self, value: Any) -> list[str]:
        """Return validation errors for a single value."""
        errors: list[str] = []
        if value is None:
            if self.required and self.default is None:
                errors.append(f"Feature '{self.name}' is required but got None")
            return errors
        if self.feature_type == FeatureType.NUMERIC:
            if not isinstance(value, (int, float)):
                errors.append(f"Feature '{self.name}' expected numeric, got {type(value).__name__}")
            else:
                if self.min_value is not None and value < self.min_value:
                    errors.append(f"Feature '{self.name}' value {value} < min {self.min_value}")
                if self.max_value is not None and value > self.max_value:
                    errors.append(f"Feature '{self.name}' value {value} > max {self.max_value}")
        elif self.feature_type == FeatureType.CATEGORICAL and self.allowed_vals:
            if value not in self.allowed_vals:
                errors.append(f"Feature '{self.name}' value {value!r} not in allowed set")
        elif self.feature_type == FeatureType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"Feature '{self.name}' expected bool, got {type(value).__name__}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id":   self.feature_id,
            "name":         self.name,
            "feature_type": self.feature_type.value,
            "description":  self.description,
            "required":     self.required,
            "default":      self.default,
            "min_value":    self.min_value,
            "max_value":    self.max_value,
            "allowed_vals": self.allowed_vals,
            "tags":         self.tags,
        }
