"""
tests/unit/configuration/test_configuration_merger.py
======================================================
Unit tests for ConfigurationMerger.
"""

from __future__ import annotations

import pytest

from iios.configuration.configuration_merger import ArrayMergeStrategy, ConfigurationMerger
from iios.configuration.configuration_exception import ConfigurationMergeError


class TestConfigurationMerger:
    # ------------------------------------------------------------------
    # Basic scalar merge
    # ------------------------------------------------------------------

    def test_empty_sources(self):
        m = ConfigurationMerger()
        result = m.merge([])
        assert result == {}

    def test_single_source(self):
        m = ConfigurationMerger()
        result = m.merge([{"a": 1, "b": 2}])
        assert result == {"a": 1, "b": 2}

    def test_later_source_wins_scalar(self):
        m = ConfigurationMerger()
        result = m.merge([{"key": "first"}, {"key": "second"}])
        assert result["key"] == "second"

    def test_missing_key_in_later_source_preserved(self):
        m = ConfigurationMerger()
        result = m.merge([{"a": 1, "b": 2}, {"b": 99}])
        assert result["a"] == 1
        assert result["b"] == 99

    def test_non_dict_source_raises(self):
        m = ConfigurationMerger()
        with pytest.raises(ConfigurationMergeError):
            m.merge([{"a": 1}, "not a dict"])  # type: ignore

    # ------------------------------------------------------------------
    # Deep (nested dict) merge
    # ------------------------------------------------------------------

    def test_nested_dict_deep_merge(self):
        m = ConfigurationMerger()
        base = {"risk": {"vix_threshold": 45.0, "daily_loss_pct": 0.02}}
        override = {"risk": {"vix_threshold": 50.0}}
        result = m.merge([base, override])
        assert result["risk"]["vix_threshold"] == 50.0
        assert result["risk"]["daily_loss_pct"] == 0.02   # preserved from base

    def test_nested_dict_three_levels(self):
        m = ConfigurationMerger()
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 99}}}
        result = m.merge([base, override])
        assert result["a"]["b"]["c"] == 99
        assert result["a"]["b"]["d"] == 2

    def test_nested_type_mismatch_override_wins(self):
        m = ConfigurationMerger()
        base = {"risk": {"threshold": 6.5}}
        override = {"risk": "not a dict"}   # scalar overrides dict
        result = m.merge([base, override])
        assert result["risk"] == "not a dict"

    def test_input_dicts_not_mutated(self):
        m = ConfigurationMerger()
        base = {"risk": {"threshold": 6.5}}
        override = {"risk": {"threshold": 7.0}}
        _ = m.merge([base, override])
        assert base["risk"]["threshold"] == 6.5
        assert override["risk"]["threshold"] == 7.0

    def test_merge_two(self):
        m = ConfigurationMerger()
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"c": 3, "d": 4}}
        result = m.merge_two(base, override)
        assert result["a"] == 1
        assert result["b"]["c"] == 3
        assert result["b"]["d"] == 4

    # ------------------------------------------------------------------
    # Array strategies
    # ------------------------------------------------------------------

    def test_array_replace_strategy(self):
        m = ConfigurationMerger(array_strategy=ArrayMergeStrategy.REPLACE)
        result = m.merge([{"items": [1, 2]}, {"items": [3, 4]}])
        assert result["items"] == [3, 4]

    def test_array_append_strategy(self):
        m = ConfigurationMerger(array_strategy=ArrayMergeStrategy.APPEND)
        result = m.merge([{"items": [1, 2]}, {"items": [3, 4]}])
        assert result["items"] == [1, 2, 3, 4]

    def test_array_prepend_strategy(self):
        m = ConfigurationMerger(array_strategy=ArrayMergeStrategy.PREPEND)
        result = m.merge([{"items": [1, 2]}, {"items": [3, 4]}])
        assert result["items"] == [3, 4, 1, 2]

    def test_array_unique_strategy(self):
        m = ConfigurationMerger(array_strategy=ArrayMergeStrategy.UNIQUE)
        result = m.merge([{"items": [1, 2, 3]}, {"items": [2, 3, 4]}])
        assert set(result["items"]) == {1, 2, 3, 4}

    def test_array_unique_preserves_order(self):
        m = ConfigurationMerger(array_strategy=ArrayMergeStrategy.UNIQUE)
        result = m.merge([{"items": ["a", "b"]}, {"items": ["b", "c"]}])
        # a appears before b, b appears before c, no duplicates
        items = result["items"]
        assert items.index("a") < items.index("b")
        assert "b" in items
        assert items.count("b") == 1

    # ------------------------------------------------------------------
    # Priority ordering (three sources)
    # ------------------------------------------------------------------

    def test_three_source_priority(self):
        m = ConfigurationMerger()
        sources = [
            {"env": "default"},
            {"env": "dotenv"},
            {"env": "env_var"},
        ]
        result = m.merge(sources)
        assert result["env"] == "env_var"

    def test_additive_keys(self):
        m = ConfigurationMerger()
        sources = [
            {"a": 1},
            {"b": 2},
            {"c": 3},
        ]
        result = m.merge(sources)
        assert result == {"a": 1, "b": 2, "c": 3}
