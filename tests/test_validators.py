"""Tests for the LLM model validators."""

import pytest
from tradingagents.llm_clients.validators import validate_model, VALID_MODELS


class TestValidateModel:
    """Tests for validate_model function."""

    def test_valid_openai_model(self):
        assert validate_model("openai", "gpt-5.2") is True

    def test_invalid_openai_model(self):
        assert validate_model("openai", "nonexistent-model") is False

    def test_valid_anthropic_model(self):
        assert validate_model("anthropic", "claude-opus-4-5") is True

    def test_invalid_anthropic_model(self):
        assert validate_model("anthropic", "fake-claude") is False

    def test_valid_google_model(self):
        assert validate_model("google", "gemini-2.5-pro") is True

    def test_invalid_google_model(self):
        assert validate_model("google", "fake-gemini") is False

    def test_valid_xai_model(self):
        assert validate_model("xai", "grok-4") is True

    def test_invalid_xai_model(self):
        assert validate_model("xai", "fake-grok") is False

    def test_ollama_accepts_any_model(self):
        assert validate_model("ollama", "llama3:latest") is True
        assert validate_model("ollama", "anything") is True

    def test_openrouter_accepts_any_model(self):
        assert validate_model("openrouter", "anthropic/claude-3") is True
        assert validate_model("openrouter", "anything") is True

    def test_unknown_provider_accepts_any_model(self):
        assert validate_model("unknown_provider", "any_model") is True

    def test_case_insensitive_provider(self):
        assert validate_model("OpenAI", "gpt-5.2") is True
        assert validate_model("ANTHROPIC", "claude-opus-4-5") is True

    def test_all_providers_have_models(self):
        for provider, models in VALID_MODELS.items():
            assert len(models) > 0, f"Provider {provider} has no models"

    def test_all_openai_models_valid(self):
        for model in VALID_MODELS["openai"]:
            assert validate_model("openai", model) is True

    def test_all_anthropic_models_valid(self):
        for model in VALID_MODELS["anthropic"]:
            assert validate_model("anthropic", model) is True

    def test_all_google_models_valid(self):
        for model in VALID_MODELS["google"]:
            assert validate_model("google", model) is True

    def test_all_xai_models_valid(self):
        for model in VALID_MODELS["xai"]:
            assert validate_model("xai", model) is True
