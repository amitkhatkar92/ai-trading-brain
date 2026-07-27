"""Tests for request models and execution pipeline."""
from __future__ import annotations

import pytest

from iios.ai.foundation.request import (
    RequestMetadata,
    AIRequest,
    AIResponse,
    AIExecutionRequest,
    AIExecutionResult,
)
from iios.ai.foundation.pipeline import (
    ExecutionPipeline,
    ValidationStage,
)
from iios.ai.foundation.exceptions import AIPipelineStageError


class TestRequestMetadata:
    def test_create_generates_ids(self):
        meta = RequestMetadata.create(
            session_id = "s-001",
            module_id  = "a3",
            capability = "completion",
        )
        assert meta.request_id
        assert meta.trace_id
        assert meta.capability == "completion"

    def test_to_dict(self):
        meta = RequestMetadata.create("s-001", "a3")
        d = meta.to_dict()
        assert "request_id" in d
        assert d["module_id"] == "a3"


class TestAIRequest:
    def _make_meta(self) -> RequestMetadata:
        return RequestMetadata.create("s-001", "a3")

    def test_create(self):
        meta = self._make_meta()
        req  = AIRequest.create(
            metadata   = meta,
            messages   = [{"role": "user", "content": "Hello"}],
            max_tokens = 512,
        )
        assert req.request_id == meta.request_id
        assert req.max_tokens == 512
        assert len(req.messages) == 1

    def test_messages_are_immutable(self):
        meta = self._make_meta()
        msgs = [{"role": "user", "content": "Q"}]
        req  = AIRequest.create(meta, msgs, max_tokens=100)
        assert isinstance(req.messages, tuple)

    def test_to_dict(self):
        meta = self._make_meta()
        req  = AIRequest.create(meta, [{"role": "user", "content": "Q"}], max_tokens=100)
        d    = req.to_dict()
        assert d["message_count"] == 1
        assert d["max_tokens"] == 100


class TestAIResponse:
    def test_success_factory(self):
        resp = AIResponse.success(
            request_id    = "r-001",
            session_id    = "s-001",
            content       = "The answer",
            provider_id   = "openai",
            model_id      = "gpt-4o",
            finish_reason = "stop",
            prompt_tokens = 10,
            output_tokens = 5,
            latency_ms    = 250.0,
        )
        assert resp.succeeded
        assert resp.total_tokens == 15
        assert resp.error == ""

    def test_failure_factory(self):
        resp = AIResponse.failure(
            request_id = "r-001",
            session_id = "s-001",
            error      = "timeout",
            latency_ms = 30_000.0,
        )
        assert not resp.succeeded
        assert resp.error == "timeout"
        assert resp.total_tokens == 0

    def test_to_dict(self):
        resp = AIResponse.failure("r", "s", "err", 0.0)
        d    = resp.to_dict()
        assert d["succeeded"] is False
        assert "response_id" in d


class TestExecutionPipeline:
    def _make_exec_request(self) -> AIExecutionRequest:
        meta = RequestMetadata.create("s-001", "a3", timeout_s=5.0)
        req  = AIRequest.create(
            meta,
            [{"role": "user", "content": "Hello"}],
            max_tokens = 100,
        )
        return AIExecutionRequest(request=req)

    def test_pipeline_completes_with_stub(self):
        pipeline = ExecutionPipeline()
        result   = pipeline.run(self._make_exec_request())
        assert result.succeeded
        assert result.stages_completed == 6
        assert result.response.content == "[stub response]"

    def test_stage_names(self):
        pipeline = ExecutionPipeline()
        names    = pipeline.stage_names()
        assert names == [
            "validation",
            "policy_evaluation",
            "provider_selection",
            "execution",
            "result_validation",
            "response",
        ]

    def test_validation_fails_on_empty_messages(self):
        meta = RequestMetadata.create("s-001", "a3")
        req  = AIRequest.create(meta, [], max_tokens=100)
        exec_req = AIExecutionRequest(request=req)
        pipeline = ExecutionPipeline()
        result   = pipeline.run(exec_req)
        assert not result.succeeded
        assert result.response.finish_reason == "error"

    def test_add_custom_stage(self):
        class Marker(ValidationStage):
            @property
            def name(self) -> str:
                return "custom_marker"
            def _run(self, ctx) -> None:
                ctx.set("marker", True)

        pipeline = ExecutionPipeline()
        pipeline.add_stage(Marker(), index=0)
        result = pipeline.run(self._make_exec_request())
        assert "custom_marker" in pipeline.stage_names()
