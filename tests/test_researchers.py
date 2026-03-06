"""Tests for bull and bear researcher agent nodes."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
from tradingagents.agents.researchers.bear_researcher import create_bear_researcher


@pytest.fixture
def researcher_state():
    """State for researcher nodes."""
    return {
        "trade_date": "2026-01-15",
        "company_of_interest": "AAPL",
        "market_report": "Market is bullish.",
        "sentiment_report": "Positive sentiment.",
        "news_report": "Good earnings.",
        "fundamentals_report": "Strong balance sheet.",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
    }


@pytest.fixture
def mock_memory():
    memory = MagicMock()
    memory.get_memories.return_value = [
        {"recommendation": "Previous rec: buy tech stocks."},
    ]
    return memory


class TestBullResearcher:
    def test_creates_callable(self, mock_llm, mock_memory):
        node = create_bull_researcher(mock_llm, mock_memory)
        assert callable(node)

    def test_returns_updated_debate_state(self, mock_llm, mock_memory, researcher_state):
        mock_llm.invoke.return_value.content = "I recommend buying AAPL."
        node = create_bull_researcher(mock_llm, mock_memory)
        result = node(researcher_state)

        assert "investment_debate_state" in result
        state = result["investment_debate_state"]
        assert "Bull Analyst:" in state["history"]
        assert "Bull Analyst:" in state["bull_history"]
        assert state["count"] == 1

    def test_preserves_bear_history(self, mock_llm, mock_memory, researcher_state):
        researcher_state["investment_debate_state"]["bear_history"] = "Bear said sell."
        node = create_bull_researcher(mock_llm, mock_memory)
        result = node(researcher_state)

        assert result["investment_debate_state"]["bear_history"] == "Bear said sell."

    def test_invokes_llm(self, mock_llm, mock_memory, researcher_state):
        node = create_bull_researcher(mock_llm, mock_memory)
        node(researcher_state)
        mock_llm.invoke.assert_called_once()

    def test_queries_memory(self, mock_llm, mock_memory, researcher_state):
        node = create_bull_researcher(mock_llm, mock_memory)
        node(researcher_state)
        mock_memory.get_memories.assert_called_once()
        _, kwargs = mock_memory.get_memories.call_args
        assert kwargs["n_matches"] == 2

    def test_handles_no_memories(self, mock_llm, mock_memory, researcher_state):
        mock_memory.get_memories.return_value = []
        node = create_bull_researcher(mock_llm, mock_memory)
        result = node(researcher_state)
        assert "investment_debate_state" in result


class TestBearResearcher:
    def test_creates_callable(self, mock_llm, mock_memory):
        node = create_bear_researcher(mock_llm, mock_memory)
        assert callable(node)

    def test_returns_updated_debate_state(self, mock_llm, mock_memory, researcher_state):
        mock_llm.invoke.return_value.content = "I recommend selling AAPL."
        node = create_bear_researcher(mock_llm, mock_memory)
        result = node(researcher_state)

        state = result["investment_debate_state"]
        assert "Bear Analyst:" in state["history"]
        assert "Bear Analyst:" in state["bear_history"]
        assert state["count"] == 1

    def test_preserves_bull_history(self, mock_llm, mock_memory, researcher_state):
        researcher_state["investment_debate_state"]["bull_history"] = "Bull said buy."
        node = create_bear_researcher(mock_llm, mock_memory)
        result = node(researcher_state)

        assert result["investment_debate_state"]["bull_history"] == "Bull said buy."

    def test_increments_count(self, mock_llm, mock_memory, researcher_state):
        researcher_state["investment_debate_state"]["count"] = 3
        node = create_bear_researcher(mock_llm, mock_memory)
        result = node(researcher_state)
        assert result["investment_debate_state"]["count"] == 4
