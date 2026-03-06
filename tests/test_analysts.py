"""Tests for analyst agent nodes (market, news, social media, fundamentals)."""

from unittest.mock import MagicMock, patch

import pytest

from tradingagents.agents.analysts.market_analyst import create_market_analyst
from tradingagents.agents.analysts.news_analyst import create_news_analyst
from tradingagents.agents.analysts.social_media_analyst import create_social_media_analyst
from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst


@pytest.fixture
def analyst_state():
    """Minimal state for analyst nodes."""
    return {
        "trade_date": "2026-01-15",
        "company_of_interest": "AAPL",
        "messages": [],
    }


@pytest.fixture
def mock_analyst_llm():
    """LLM mock that supports bind_tools and returns via chain invocation.

    LangChain's RunnableSequence calls bound_llm(prompt_output), so we
    configure bound_llm.return_value (i.e. __call__) to return results.
    """
    llm = MagicMock()
    bound_llm = MagicMock()

    result = MagicMock()
    result.content = "Market analysis report for AAPL."
    result.tool_calls = []
    bound_llm.return_value = result

    llm.bind_tools.return_value = bound_llm
    return llm


class TestMarketAnalyst:
    def test_creates_callable(self, mock_analyst_llm):
        node = create_market_analyst(mock_analyst_llm)
        assert callable(node)

    def test_returns_market_report_when_no_tool_calls(self, mock_analyst_llm, analyst_state):
        node = create_market_analyst(mock_analyst_llm)
        result = node(analyst_state)
        assert "market_report" in result
        assert "messages" in result

    def test_returns_empty_report_when_tool_calls_present(self, mock_analyst_llm, analyst_state):
        """When LLM returns tool calls, market_report should be empty."""
        bound = mock_analyst_llm.bind_tools.return_value
        result_with_tools = MagicMock()
        result_with_tools.tool_calls = [{"name": "get_stock_data", "args": {}}]
        result_with_tools.content = "calling tool"
        bound.return_value = result_with_tools

        node = create_market_analyst(mock_analyst_llm)
        result = node(analyst_state)
        assert result["market_report"] == ""


class TestNewsAnalyst:
    def test_creates_callable(self, mock_analyst_llm):
        node = create_news_analyst(mock_analyst_llm)
        assert callable(node)

    def test_returns_news_report(self, mock_analyst_llm, analyst_state):
        node = create_news_analyst(mock_analyst_llm)
        result = node(analyst_state)
        assert "news_report" in result
        assert "messages" in result


class TestSocialMediaAnalyst:
    def test_creates_callable(self, mock_analyst_llm):
        node = create_social_media_analyst(mock_analyst_llm)
        assert callable(node)

    def test_returns_sentiment_report(self, mock_analyst_llm, analyst_state):
        node = create_social_media_analyst(mock_analyst_llm)
        result = node(analyst_state)
        assert "sentiment_report" in result
        assert "messages" in result


class TestFundamentalsAnalyst:
    def test_creates_callable(self, mock_analyst_llm):
        node = create_fundamentals_analyst(mock_analyst_llm)
        assert callable(node)

    def test_returns_fundamentals_report(self, mock_analyst_llm, analyst_state):
        node = create_fundamentals_analyst(mock_analyst_llm)
        result = node(analyst_state)
        assert "fundamentals_report" in result
        assert "messages" in result
