"""Tests for trader agent node."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.trader.trader import create_trader


@pytest.fixture
def mock_memory():
    memory = MagicMock()
    memory.get_memories.return_value = [
        {"recommendation": "Past: bought AAPL at $150, gained 10%."},
    ]
    return memory


@pytest.fixture
def trader_state():
    """State for trader node."""
    return {
        "company_of_interest": "AAPL",
        "investment_plan": "Buy 100 shares at market open.",
        "market_report": "Market is bullish.",
        "sentiment_report": "Positive sentiment.",
        "news_report": "Good earnings.",
        "fundamentals_report": "Strong balance sheet.",
    }


class TestTrader:
    def test_creates_callable(self, mock_llm, mock_memory):
        node = create_trader(mock_llm, mock_memory)
        assert callable(node)

    def test_returns_trader_investment_plan(self, mock_llm, mock_memory, trader_state):
        mock_llm.invoke.return_value.content = "Execute buy order for AAPL at $180."
        node = create_trader(mock_llm, mock_memory)
        result = node(trader_state)

        assert result["trader_investment_plan"] == "Execute buy order for AAPL at $180."
        assert result["sender"] == "Trader"
        assert "messages" in result

    def test_invokes_llm_with_messages(self, mock_llm, mock_memory, trader_state):
        node = create_trader(mock_llm, mock_memory)
        node(trader_state)

        mock_llm.invoke.assert_called_once()
        messages = mock_llm.invoke.call_args[0][0]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_message_contains_memories(self, mock_llm, mock_memory, trader_state):
        node = create_trader(mock_llm, mock_memory)
        node(trader_state)

        messages = mock_llm.invoke.call_args[0][0]
        system_content = messages[0]["content"]
        assert "Past: bought AAPL" in system_content

    def test_user_message_contains_company_and_plan(self, mock_llm, mock_memory, trader_state):
        node = create_trader(mock_llm, mock_memory)
        node(trader_state)

        messages = mock_llm.invoke.call_args[0][0]
        user_content = messages[1]["content"]
        assert "AAPL" in user_content
        assert "Buy 100 shares" in user_content

    def test_no_memories_uses_fallback(self, mock_llm, mock_memory, trader_state):
        mock_memory.get_memories.return_value = []
        node = create_trader(mock_llm, mock_memory)
        node(trader_state)

        messages = mock_llm.invoke.call_args[0][0]
        system_content = messages[0]["content"]
        assert "No past memories found" in system_content

    def test_queries_memory(self, mock_llm, mock_memory, trader_state):
        node = create_trader(mock_llm, mock_memory)
        node(trader_state)

        mock_memory.get_memories.assert_called_once()
        situation = mock_memory.get_memories.call_args[0][0]
        assert "Market is bullish" in situation
