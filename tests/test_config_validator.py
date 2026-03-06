"""Tests for the startup configuration validator."""

import copy
import os
import pytest
from unittest.mock import patch

from tradingagents.config_validator import (
    validate_config,
    ConfigurationError,
    SUPPORTED_PROVIDERS,
    VALID_ANALYSTS,
    VALID_DATA_VENDORS,
    DATA_VENDOR_CATEGORIES,
)
from tradingagents.default_config import DEFAULT_CONFIG


def _valid_config(**overrides):
    """Return a minimal valid config dict with optional overrides."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.update(overrides)
    return cfg


class TestValidateConfigHappyPath:
    """Tests that valid configs pass validation."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_default_config_passes(self):
        validate_config(_valid_config())

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_anthropic_config_passes(self):
        validate_config(_valid_config(
            llm_provider="anthropic",
            deep_think_llm="claude-opus-4-5",
            quick_think_llm="claude-sonnet-4-5",
        ))

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test"})
    def test_google_config_passes(self):
        validate_config(_valid_config(
            llm_provider="google",
            deep_think_llm="gemini-2.5-pro",
            quick_think_llm="gemini-2.5-flash",
        ))

    def test_ollama_no_api_key_needed(self):
        validate_config(_valid_config(
            llm_provider="ollama",
            deep_think_llm="llama3",
            quick_think_llm="llama3",
        ))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_selected_analysts_validated(self):
        validate_config(_valid_config(), selected_analysts=["market", "news"])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_none_analysts_skips_validation(self):
        validate_config(_valid_config(), selected_analysts=None)


class TestMissingRequiredKeys:
    """Tests for missing required config keys."""

    def test_missing_llm_provider(self):
        cfg = _valid_config()
        del cfg["llm_provider"]
        with pytest.raises(ConfigurationError, match="llm_provider"):
            validate_config(cfg)

    def test_missing_deep_think_llm(self):
        cfg = _valid_config()
        del cfg["deep_think_llm"]
        with pytest.raises(ConfigurationError, match="deep_think_llm"):
            validate_config(cfg)

    def test_missing_quick_think_llm(self):
        cfg = _valid_config()
        del cfg["quick_think_llm"]
        with pytest.raises(ConfigurationError, match="quick_think_llm"):
            validate_config(cfg)

    def test_missing_data_vendors(self):
        cfg = _valid_config()
        del cfg["data_vendors"]
        with pytest.raises(ConfigurationError, match="data_vendors"):
            validate_config(cfg)

    def test_multiple_missing_keys_reported(self):
        cfg = _valid_config()
        del cfg["llm_provider"]
        del cfg["deep_think_llm"]
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(cfg)
        assert len(exc_info.value.errors) == 2


class TestProviderValidation:
    """Tests for LLM provider validation."""

    def test_unsupported_provider(self):
        with pytest.raises(ConfigurationError, match="Unsupported llm_provider"):
            validate_config(_valid_config(llm_provider="fake_provider"))

    def test_provider_must_be_string(self):
        with pytest.raises(ConfigurationError, match="must be a string"):
            validate_config(_valid_config(llm_provider=123))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_openai_api_key(self):
        # Ensure no API keys are set
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
            os.environ.pop(var, None)
        with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
            validate_config(_valid_config(llm_provider="openai"))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_anthropic_api_key(self):
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            os.environ.pop(var, None)
        with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
            validate_config(_valid_config(
                llm_provider="anthropic",
                deep_think_llm="claude-opus-4-5",
                quick_think_llm="claude-sonnet-4-5",
            ))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_google_api_key(self):
        for var in ("OPENAI_API_KEY", "GOOGLE_API_KEY"):
            os.environ.pop(var, None)
        with pytest.raises(ConfigurationError, match="GOOGLE_API_KEY"):
            validate_config(_valid_config(
                llm_provider="google",
                deep_think_llm="gemini-2.5-pro",
                quick_think_llm="gemini-2.5-flash",
            ))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_xai_api_key(self):
        for var in ("OPENAI_API_KEY", "XAI_API_KEY"):
            os.environ.pop(var, None)
        with pytest.raises(ConfigurationError, match="XAI_API_KEY"):
            validate_config(_valid_config(
                llm_provider="xai",
                deep_think_llm="grok-4",
                quick_think_llm="grok-4",
            ))


class TestModelValidation:
    """Tests for model name validation."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_invalid_model_for_provider(self):
        with pytest.raises(ConfigurationError, match="not valid for provider"):
            validate_config(_valid_config(deep_think_llm="nonexistent-model"))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_empty_model_name(self):
        with pytest.raises(ConfigurationError, match="non-empty string"):
            validate_config(_valid_config(deep_think_llm=""))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_non_string_model(self):
        with pytest.raises(ConfigurationError, match="non-empty string"):
            validate_config(_valid_config(deep_think_llm=42))

    def test_ollama_accepts_any_model(self):
        validate_config(_valid_config(
            llm_provider="ollama",
            deep_think_llm="any-custom-model",
            quick_think_llm="another-model",
        ))


class TestDebateRoundsValidation:
    """Tests for debate round settings."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_zero_debate_rounds_rejected(self):
        with pytest.raises(ConfigurationError, match="max_debate_rounds"):
            validate_config(_valid_config(max_debate_rounds=0))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_negative_debate_rounds_rejected(self):
        with pytest.raises(ConfigurationError, match="max_debate_rounds"):
            validate_config(_valid_config(max_debate_rounds=-1))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_non_int_debate_rounds_rejected(self):
        with pytest.raises(ConfigurationError, match="max_debate_rounds"):
            validate_config(_valid_config(max_debate_rounds=1.5))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_zero_risk_rounds_rejected(self):
        with pytest.raises(ConfigurationError, match="max_risk_discuss_rounds"):
            validate_config(_valid_config(max_risk_discuss_rounds=0))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_valid_debate_rounds(self):
        validate_config(_valid_config(max_debate_rounds=5, max_risk_discuss_rounds=3))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_zero_recur_limit_rejected(self):
        with pytest.raises(ConfigurationError, match="max_recur_limit"):
            validate_config(_valid_config(max_recur_limit=0))


class TestDataVendorValidation:
    """Tests for data vendor configuration."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_invalid_vendor_name(self):
        cfg = _valid_config()
        cfg["data_vendors"]["core_stock_apis"] = "invalid_vendor"
        with pytest.raises(ConfigurationError, match="Invalid vendor"):
            validate_config(cfg)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_unknown_category(self):
        cfg = _valid_config()
        cfg["data_vendors"]["fake_category"] = "yfinance"
        with pytest.raises(ConfigurationError, match="Unknown data vendor category"):
            validate_config(cfg)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_data_vendors_must_be_dict(self):
        with pytest.raises(ConfigurationError, match="must be a dict"):
            validate_config(_valid_config(data_vendors="yfinance"))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_tool_vendors_must_be_dict(self):
        with pytest.raises(ConfigurationError, match="must be a dict"):
            validate_config(_valid_config(tool_vendors="invalid"))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_alpha_vantage_vendor_accepted(self):
        cfg = _valid_config()
        cfg["data_vendors"]["core_stock_apis"] = "alpha_vantage"
        validate_config(cfg)


class TestSelectedAnalystsValidation:
    """Tests for selected_analysts parameter."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_empty_analysts_rejected(self):
        with pytest.raises(ConfigurationError, match="must not be empty"):
            validate_config(_valid_config(), selected_analysts=[])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_unknown_analyst_rejected(self):
        with pytest.raises(ConfigurationError, match="Unknown analyst type"):
            validate_config(_valid_config(), selected_analysts=["market", "crypto"])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_single_valid_analyst(self):
        validate_config(_valid_config(), selected_analysts=["fundamentals"])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_all_valid_analysts(self):
        validate_config(
            _valid_config(),
            selected_analysts=["market", "social", "news", "fundamentals"],
        )


class TestMultipleErrors:
    """Tests that multiple errors are collected."""

    @patch.dict(os.environ, {}, clear=True)
    def test_collects_multiple_errors(self):
        for var in ("OPENAI_API_KEY",):
            os.environ.pop(var, None)
        cfg = _valid_config(
            max_debate_rounds=-1,
            max_risk_discuss_rounds=0,
        )
        cfg["data_vendors"]["fake_cat"] = "fake_vendor"
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(cfg, selected_analysts=["crypto"])
        # Should have errors for: API key, debate rounds, risk rounds,
        # unknown category, invalid vendor, unknown analyst
        assert len(exc_info.value.errors) >= 5


class TestConfigurationErrorFormat:
    """Tests for the ConfigurationError exception."""

    def test_errors_list_accessible(self):
        err = ConfigurationError(["error 1", "error 2"])
        assert err.errors == ["error 1", "error 2"]

    def test_message_contains_all_errors(self):
        err = ConfigurationError(["error 1", "error 2"])
        msg = str(err)
        assert "error 1" in msg
        assert "error 2" in msg

    def test_message_has_bullet_format(self):
        err = ConfigurationError(["first", "second"])
        msg = str(err)
        assert "  - first" in msg
        assert "  - second" in msg
