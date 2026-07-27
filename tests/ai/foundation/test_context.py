"""Tests for the AI Foundation context framework."""
from __future__ import annotations

import pytest

from iios.ai.foundation.context import (
    ContextMetadata,
    AIContext,
    ContextBuilder,
    ContextValidator,
    TruncationContextCompressor,
)
from iios.ai.foundation.exceptions import (
    AIContextTooLargeError,
    AIContextValidationError,
    AIContextBuildError,
)


class TestContextMetadata:
    def test_create(self):
        meta = ContextMetadata.create(
            session_id = "s-001",
            module_id  = "a3",
            max_tokens = 4_096,
        )
        assert meta.session_id == "s-001"
        assert meta.max_tokens == 4_096
        assert meta.context_id

    def test_to_dict(self):
        meta = ContextMetadata.create("s-001", "a3")
        d = meta.to_dict()
        assert "context_id" in d
        assert d["module_id"] == "a3"


class TestAIContext:
    def _make_ctx(self, max_tokens: int = 1_000) -> AIContext:
        meta = ContextMetadata.create("s-001", "a3", max_tokens=max_tokens)
        return AIContext(meta)

    def test_add_and_len(self):
        ctx = self._make_ctx()
        ctx.add_system("You are an assistant.", estimated_tokens=5)
        ctx.add_user("Hello", estimated_tokens=2)
        assert len(ctx) == 2

    def test_estimated_tokens_accumulated(self):
        ctx = self._make_ctx()
        ctx.add_entry("system", "S", estimated_tokens=100)
        ctx.add_entry("user",   "U", estimated_tokens=50)
        assert ctx.estimated_tokens == 150

    def test_within_budget(self):
        ctx = self._make_ctx(max_tokens=200)
        ctx.add_entry("user", "Q", estimated_tokens=100)
        assert ctx.is_within_budget

    def test_over_budget(self):
        ctx = self._make_ctx(max_tokens=50)
        ctx.add_entry("user", "Q", estimated_tokens=100)
        assert not ctx.is_within_budget

    def test_merge(self):
        ctx1 = self._make_ctx()
        ctx2 = self._make_ctx()
        ctx1.add_system("system", estimated_tokens=5)
        ctx2.add_user("user", estimated_tokens=3)
        ctx1.merge(ctx2)
        assert len(ctx1) == 2
        assert ctx1.estimated_tokens == 8

    def test_to_messages(self):
        ctx = self._make_ctx()
        ctx.add_system("Sys")
        ctx.add_user("Q")
        msgs = ctx.to_messages()
        assert msgs == [{"role": "system", "content": "Sys"}, {"role": "user", "content": "Q"}]

    def test_remove_last(self):
        ctx = self._make_ctx()
        ctx.add_entry("user", "A", estimated_tokens=10)
        ctx.add_entry("user", "B", estimated_tokens=20)
        removed = ctx.remove_last()
        assert removed.content == "B"
        assert ctx.estimated_tokens == 10

    def test_extra_data(self):
        ctx = self._make_ctx()
        ctx.set_extra("key", "value")
        assert ctx.get_extra("key") == "value"
        assert ctx.get_extra("missing", "def") == "def"


class TestContextBuilder:
    def test_basic_build(self):
        ctx = (
            ContextBuilder("s-001", "a3")
            .with_max_tokens(500)
            .add_system("System prompt", estimated_tokens=5)
            .add_user("Query", estimated_tokens=3)
            .build()
        )
        assert len(ctx) == 2
        assert ctx.max_tokens == 500

    def test_invalid_max_tokens_raises(self):
        with pytest.raises(AIContextBuildError):
            ContextBuilder("s-001", "a3").with_max_tokens(-1)

    def test_validation_runs_on_build(self):
        # empty context should fail validation
        with pytest.raises(AIContextValidationError):
            ContextBuilder("s-001", "a3").build()

    def test_skip_validation(self):
        ctx = (
            ContextBuilder("s-001", "a3")
            .skip_validation()
            .build()
        )
        assert len(ctx) == 0  # built without error

    def test_over_budget_raises_at_build(self):
        with pytest.raises(AIContextTooLargeError):
            (
                ContextBuilder("s-001", "a3")
                .with_max_tokens(10)
                .add_user("query", estimated_tokens=500)
                .build()
            )


class TestContextValidator:
    def _make_ctx(self, max_tokens: int = 1_000) -> AIContext:
        meta = ContextMetadata.create("s-001", "a3", max_tokens=max_tokens)
        return AIContext(meta)

    def test_valid_context_passes(self):
        ctx = self._make_ctx()
        ctx.add_system("S", estimated_tokens=1)
        ctx.add_user("Q", estimated_tokens=1)
        result = ContextValidator().validate(ctx)
        assert result.is_valid

    def test_empty_context_raises(self):
        ctx = self._make_ctx()
        with pytest.raises(AIContextValidationError):
            ContextValidator().validate(ctx)

    def test_blank_content_raises(self):
        ctx = self._make_ctx()
        ctx.add_entry("user", "   ", estimated_tokens=0)
        with pytest.raises(AIContextValidationError):
            ContextValidator().validate(ctx)

    def test_over_budget_raises(self):
        ctx = self._make_ctx(max_tokens=10)
        ctx.add_user("Q", estimated_tokens=1_000)
        with pytest.raises(AIContextTooLargeError):
            ContextValidator().validate(ctx)


class TestTruncationCompressor:
    def _make_ctx(self, max_tokens: int = 100) -> AIContext:
        meta = ContextMetadata.create("s-001", "a3", max_tokens=max_tokens)
        return AIContext(meta)

    def test_no_op_when_within_budget(self):
        ctx = self._make_ctx(max_tokens=100)
        ctx.add_user("Q", estimated_tokens=50)
        result = TruncationContextCompressor().compress(ctx)
        assert result.entries_removed == 0
        assert result.compressed_tokens == 50

    def test_truncates_to_fit(self):
        ctx = self._make_ctx(max_tokens=50)
        ctx.add_user("A", estimated_tokens=30)
        ctx.add_user("B", estimated_tokens=30)
        result = TruncationContextCompressor().compress(ctx)
        assert ctx.is_within_budget
        assert result.entries_removed >= 1
