"""Tests for LLM client factory and client classes."""

import pytest
from unittest.mock import patch, MagicMock

from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.base_client import BaseLLMClient
from tradingagents.llm_clients.openai_client import OpenAIClient, UnifiedChatOpenAI
from tradingagents.llm_clients.anthropic_client import AnthropicClient
from tradingagents.llm_clients.google_client import GoogleClient


class TestCreateLLMClient:
    """Tests for the create_llm_client factory function."""

    def test_openai_returns_openai_client(self):
        client = create_llm_client("openai", "gpt-5.2")
        assert isinstance(client, OpenAIClient)

    def test_anthropic_returns_anthropic_client(self):
        client = create_llm_client("anthropic", "claude-opus-4-5")
        assert isinstance(client, AnthropicClient)

    def test_google_returns_google_client(self):
        client = create_llm_client("google", "gemini-2.5-pro")
        assert isinstance(client, GoogleClient)

    def test_xai_returns_openai_client(self):
        client = create_llm_client("xai", "grok-4")
        assert isinstance(client, OpenAIClient)

    def test_ollama_returns_openai_client(self):
        client = create_llm_client("ollama", "llama3")
        assert isinstance(client, OpenAIClient)

    def test_openrouter_returns_openai_client(self):
        client = create_llm_client("openrouter", "some-model")
        assert isinstance(client, OpenAIClient)

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_client("unsupported", "model")

    def test_case_insensitive_provider(self):
        client = create_llm_client("OpenAI", "gpt-5.2")
        assert isinstance(client, OpenAIClient)

    def test_all_clients_are_base_instances(self):
        for provider, model in [
            ("openai", "gpt-5.2"),
            ("anthropic", "claude-opus-4-5"),
            ("google", "gemini-2.5-pro"),
        ]:
            client = create_llm_client(provider, model)
            assert isinstance(client, BaseLLMClient)

    def test_kwargs_passed_through(self):
        client = create_llm_client("openai", "gpt-5.2", timeout=30)
        assert client.kwargs.get("timeout") == 30


class TestUnifiedChatOpenAI:
    """Tests for the UnifiedChatOpenAI reasoning model handling."""

    def test_is_reasoning_model_o1(self):
        assert UnifiedChatOpenAI._is_reasoning_model("o1") is True
        assert UnifiedChatOpenAI._is_reasoning_model("o1-preview") is True

    def test_is_reasoning_model_o3(self):
        assert UnifiedChatOpenAI._is_reasoning_model("o3") is True
        assert UnifiedChatOpenAI._is_reasoning_model("o3-mini") is True

    def test_is_reasoning_model_gpt5(self):
        assert UnifiedChatOpenAI._is_reasoning_model("gpt-5") is True
        assert UnifiedChatOpenAI._is_reasoning_model("gpt-5.2") is True
        assert UnifiedChatOpenAI._is_reasoning_model("gpt-5-mini") is True

    def test_is_not_reasoning_model(self):
        assert UnifiedChatOpenAI._is_reasoning_model("gpt-4o") is False
        assert UnifiedChatOpenAI._is_reasoning_model("gpt-4.1") is False


class TestOpenAIClient:
    """Tests for OpenAIClient."""

    def test_stores_provider(self):
        client = OpenAIClient("gpt-5.2", provider="openai")
        assert client.provider == "openai"

    def test_xai_provider(self):
        client = OpenAIClient("grok-4", provider="xai")
        assert client.provider == "xai"

    def test_validate_model(self):
        client = OpenAIClient("gpt-5.2", provider="openai")
        assert client.validate_model() is True

    def test_validate_invalid_model(self):
        client = OpenAIClient("nonexistent", provider="openai")
        assert client.validate_model() is False

    def test_ollama_validate_any(self):
        client = OpenAIClient("custom-model", provider="ollama")
        assert client.validate_model() is True

    @patch("tradingagents.llm_clients.openai_client.UnifiedChatOpenAI")
    def test_get_llm_openai(self, mock_cls):
        client = OpenAIClient("gpt-5.2", provider="openai")
        client.get_llm()
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["model"] == "gpt-5.2"

    @patch("tradingagents.llm_clients.openai_client.UnifiedChatOpenAI")
    def test_get_llm_xai_sets_base_url(self, mock_cls):
        client = OpenAIClient("grok-4", provider="xai")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["base_url"] == "https://api.x.ai/v1"

    @patch("tradingagents.llm_clients.openai_client.UnifiedChatOpenAI")
    def test_get_llm_ollama_sets_localhost(self, mock_cls):
        client = OpenAIClient("llama3", provider="ollama")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert "localhost:11434" in call_kwargs["base_url"]
        assert call_kwargs["api_key"] == "ollama"

    @patch("tradingagents.llm_clients.openai_client.UnifiedChatOpenAI")
    def test_get_llm_openrouter_sets_base_url(self, mock_cls):
        client = OpenAIClient("model", provider="openrouter")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert "openrouter.ai" in call_kwargs["base_url"]

    @patch("tradingagents.llm_clients.openai_client.UnifiedChatOpenAI")
    def test_get_llm_passes_kwargs(self, mock_cls):
        client = OpenAIClient("gpt-5.2", provider="openai", timeout=30, max_retries=3)
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["max_retries"] == 3


class TestAnthropicClient:
    """Tests for AnthropicClient."""

    def test_validate_model(self):
        client = AnthropicClient("claude-opus-4-5")
        assert client.validate_model() is True

    def test_validate_invalid_model(self):
        client = AnthropicClient("nonexistent")
        assert client.validate_model() is False

    @patch("tradingagents.llm_clients.anthropic_client.ChatAnthropic")
    def test_get_llm(self, mock_cls):
        client = AnthropicClient("claude-opus-4-5")
        client.get_llm()
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-5"

    @patch("tradingagents.llm_clients.anthropic_client.ChatAnthropic")
    def test_get_llm_passes_kwargs(self, mock_cls):
        client = AnthropicClient("claude-opus-4-5", timeout=30, max_tokens=1024)
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["max_tokens"] == 1024


class TestGoogleClient:
    """Tests for GoogleClient."""

    def test_validate_model(self):
        client = GoogleClient("gemini-2.5-pro")
        assert client.validate_model() is True

    def test_validate_invalid_model(self):
        client = GoogleClient("nonexistent")
        assert client.validate_model() is False

    @patch("tradingagents.llm_clients.google_client.NormalizedChatGoogleGenerativeAI")
    def test_get_llm(self, mock_cls):
        client = GoogleClient("gemini-2.5-pro")
        client.get_llm()
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-pro"

    @patch("tradingagents.llm_clients.google_client.NormalizedChatGoogleGenerativeAI")
    def test_get_llm_gemini3_thinking_level(self, mock_cls):
        client = GoogleClient("gemini-3-pro-preview", thinking_level="high")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["thinking_level"] == "high"

    @patch("tradingagents.llm_clients.google_client.NormalizedChatGoogleGenerativeAI")
    def test_get_llm_gemini3_pro_minimal_remapped(self, mock_cls):
        client = GoogleClient("gemini-3-pro-preview", thinking_level="minimal")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["thinking_level"] == "low"

    @patch("tradingagents.llm_clients.google_client.NormalizedChatGoogleGenerativeAI")
    def test_get_llm_gemini25_thinking_budget_high(self, mock_cls):
        client = GoogleClient("gemini-2.5-pro", thinking_level="high")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["thinking_budget"] == -1

    @patch("tradingagents.llm_clients.google_client.NormalizedChatGoogleGenerativeAI")
    def test_get_llm_gemini25_thinking_budget_other(self, mock_cls):
        client = GoogleClient("gemini-2.5-pro", thinking_level="low")
        client.get_llm()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["thinking_budget"] == 0
