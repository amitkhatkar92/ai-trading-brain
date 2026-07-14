"""tests/unit/investment/decision/explainability/test_narrative.py
Tests for DecisionNarrative, NarrativeTemplate, NarrativeReport,
ExplanationFormatter.
"""
from __future__ import annotations

import json

import pytest

from iios.investment.decision.explainability.decision_narrative import (
    DecisionNarrative,
    EnglishNarrativeTemplate,
    NarrativeReport,
)
from iios.investment.decision.explainability.explanation_formatter import (
    ExplanationFormat,
    ExplanationFormatter,
)
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator
from iios.investment.decision.explainability.explainability_constants import DecisionOutcome


class TestNarrativeReport:
    def _gen(self, rich_input, decision_id) -> NarrativeReport:
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        dn   = DecisionNarrative()
        return dn.generate(snap.explanation)

    def test_fields_populated(self, rich_input, decision_id):
        r = self._gen(rich_input, decision_id)
        # decision_id in narrative = risk_snapshot.decision_id (may differ from fixture)
        assert isinstance(r.decision_id, str)
        assert len(r.decision_id) > 0
        assert len(r.outcome_header) > 0

    def test_as_text_non_empty(self, rich_input, decision_id):
        r = self._gen(rich_input, decision_id)
        text = r.as_text()
        assert len(text) > 0

    def test_situation_in_text(self, rich_input, decision_id):
        r = self._gen(rich_input, decision_id)
        text = r.as_text()
        assert r.situation in text

    def test_conclusion_in_text(self, rich_input, decision_id):
        r = self._gen(rich_input, decision_id)
        text = r.as_text()
        assert r.conclusion in text


class TestEnglishNarrativeTemplate:
    def test_template_id(self):
        t = EnglishNarrativeTemplate()
        assert t.template_id == "en_institutional_v1"

    def test_render_returns_report(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        t    = EnglishNarrativeTemplate()
        r    = t.render(snap.explanation)
        assert isinstance(r, NarrativeReport)

    def test_render_audit_note_present(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        t    = EnglishNarrativeTemplate()
        r    = t.render(snap.explanation)
        assert len(r.audit_note) > 0


class TestDecisionNarrative:
    def test_generate(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        dn   = DecisionNarrative()
        r    = dn.generate(snap.explanation)
        assert isinstance(r, NarrativeReport)

    def test_register_custom_template(self, rich_input, decision_id):
        from iios.investment.decision.explainability.decision_narrative import NarrativeTemplate

        class SpanishTemplate(NarrativeTemplate):
            @property
            def template_id(self) -> str:
                return "es_v1"

            def render(self, explanation) -> NarrativeReport:
                return NarrativeReport(
                    decision_id    = explanation.decision_id,
                    subject_id     = explanation.subject_id,
                    outcome_header = "PROCEDER",
                    situation      = "Análisis de mercado",
                    methodology    = "Cuantitativo",
                    findings       = "Señales positivas",
                    conclusion     = "Proceder",
                    caveats        = "Sujeto a cambios",
                    audit_note     = "Generado automáticamente",
                )

        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        dn   = DecisionNarrative()
        dn.register_template(SpanishTemplate())
        # After registering, the default template is replaced — generate will use it
        r = dn.generate(snap.explanation)
        assert r.outcome_header == "PROCEDER"


class TestExplanationFormatter:
    def test_dict_format(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        fmt  = ExplanationFormatter()
        d    = fmt.format(snap, ExplanationFormat.DICT)
        assert isinstance(d, dict)

    def test_json_format_is_parseable(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        fmt  = ExplanationFormatter()
        j    = fmt.format(snap, ExplanationFormat.JSON)
        parsed = json.loads(j)
        assert "decision_id" in parsed or "snapshot_id" in parsed

    def test_text_format_non_empty(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        fmt  = ExplanationFormatter()
        t    = fmt.format(snap, ExplanationFormat.TEXT)
        assert isinstance(t, str)
        assert len(t) > 0

    def test_markdown_format_has_headers(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        fmt  = ExplanationFormatter()
        md   = fmt.format(snap, ExplanationFormat.MARKDOWN)
        assert "#" in md or "**" in md
