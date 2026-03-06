"""Tests for default_config and dataflows/config modules."""

import pytest
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows import config as dataflows_config


class TestDefaultConfig:
    """Tests for the DEFAULT_CONFIG dictionary."""

    def test_config_has_required_keys(self):
        required_keys = [
            "project_dir",
            "results_dir",
            "data_cache_dir",
            "llm_provider",
            "deep_think_llm",
            "quick_think_llm",
            "backend_url",
            "max_debate_rounds",
            "max_risk_discuss_rounds",
            "max_recur_limit",
            "data_vendors",
            "tool_vendors",
        ]
        for key in required_keys:
            assert key in DEFAULT_CONFIG, f"Missing key: {key}"

    def test_default_provider_is_openai(self):
        assert DEFAULT_CONFIG["llm_provider"] == "openai"

    def test_default_debate_rounds(self):
        assert DEFAULT_CONFIG["max_debate_rounds"] == 1
        assert DEFAULT_CONFIG["max_risk_discuss_rounds"] == 1

    def test_default_recursion_limit(self):
        assert DEFAULT_CONFIG["max_recur_limit"] == 100

    def test_data_vendors_has_all_categories(self):
        vendors = DEFAULT_CONFIG["data_vendors"]
        expected = ["core_stock_apis", "technical_indicators", "fundamental_data", "news_data"]
        for cat in expected:
            assert cat in vendors

    def test_tool_vendors_is_empty_dict(self):
        assert DEFAULT_CONFIG["tool_vendors"] == {}

    def test_config_copy_is_independent(self):
        copy = DEFAULT_CONFIG.copy()
        copy["llm_provider"] = "anthropic"
        assert DEFAULT_CONFIG["llm_provider"] == "openai"


class TestDataflowsConfig:
    """Tests for the dataflows config module."""

    def setup_method(self):
        """Reset config state before each test."""
        dataflows_config._holder._config = None

    def test_initialize_config(self):
        dataflows_config.initialize_config()
        assert dataflows_config._holder._config is not None

    def test_initialize_config_idempotent(self):
        dataflows_config.initialize_config()
        first = dataflows_config._holder._config
        dataflows_config.initialize_config()
        assert dataflows_config._holder._config is first

    def test_get_config_returns_copy(self):
        cfg = dataflows_config.get_config()
        cfg["llm_provider"] = "changed"
        assert dataflows_config.get_config()["llm_provider"] != "changed"

    def test_get_config_auto_initializes(self):
        assert dataflows_config._holder._config is None
        cfg = dataflows_config.get_config()
        assert cfg is not None
        assert "llm_provider" in cfg

    def test_set_config_updates_values(self):
        dataflows_config.initialize_config()
        dataflows_config.set_config({"llm_provider": "anthropic"})
        assert dataflows_config.get_config()["llm_provider"] == "anthropic"

    def test_set_config_preserves_existing(self):
        dataflows_config.initialize_config()
        dataflows_config.set_config({"llm_provider": "anthropic"})
        cfg = dataflows_config.get_config()
        assert "deep_think_llm" in cfg

    def test_set_config_initializes_if_needed(self):
        assert dataflows_config._holder._config is None
        dataflows_config.set_config({"llm_provider": "google"})
        assert dataflows_config.get_config()["llm_provider"] == "google"
