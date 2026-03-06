"""Tests for research manager and risk manager agent nodes."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.managers.risk_manager import create_risk_manager


@pytest.fixture
def mock_memory():
    memory = MagicMock()
    memory.get_memories.return_value = [
        {"recommendation": "Past advice: diversify portfolio."},
    ]
    return memory


@pytest.fixture
def manager_state():
    """State for manager nodes."""
    return {
        "company_of_interest": "AAPL",
        "market_report": "Market is bullish.",
        "sentiment_report": "Positive sentiment.",
        "news_report": "Good earnings.",
        "fundamentals_report": "Strong balance sheet.",
        "investment_plan": "Buy 100 shares.",
        "investment_debate_state": {
            "history": "Bull and Bear debated.",
            "bull_history": "Bull: buy AAPL.",
            "bear_history": "Bear: sell AAPL.",
            "current_response": "Bull: final argument.",
            "count": 4,
        },
        "risk_debate_state": {
            "history": "Risk debate completed.",
            "aggressive_history": "Aggressive: go all in.",
            "conservative_history": "Conservative: reduce exposure.",
            "neutral_history": "Neutral: hold.",
            "latest_speaker": "Neutral",
            "current_aggressive_response": "go all in.",
            "current_conservative_response": "reduce exposure.",
            "current_neutral_response": "hold.",
            "count": 3,
        },
    }


class TestResearchManager:
    def test_creates_callable(self, mock_llm, mock_memory):
        node = create_research_manager(mock_llm, mock_memory)
        assert callable(node)

    def test_returns_investment_plan(self, mock_llm, mock_memory, manager_state):
        mock_llm.invoke.return_value.content = "Final decision: BUY AAPL."
        node = create_research_manager(mock_llm, mock_memory)
        result = node(manager_state)

        assert result["investment_plan"] == "Final decision: BUY AAPL."
        assert "investment_debate_state" in result

    def test_sets_judge_decision(self, mock_llm, mock_memory, manager_state):
        mock_llm.invoke.return_value.content = "BUY"
        node = create_research_manager(mock_llm, mock_memory)
        result = node(manager_state)

        state = result["investment_debate_state"]
        assert state["judge_decision"] == "BUY"
        assert state["current_response"] == "BUY"

    def test_preserves_debate_history(self, mock_llm, mock_memory, manager_state):
        node = create_research_manager(mock_llm, mock_memory)
        result = node(manager_state)

        state = result["investment_debate_state"]
        assert state["bull_history"] == "Bull: buy AAPL."
        assert state["bear_history"] == "Bear: sell AAPL."
        assert state["count"] == 4

    def test_queries_memory(self, mock_llm, mock_memory, manager_state):
        node = create_research_manager(mock_llm, mock_memory)
        node(manager_state)
        mock_memory.get_memories.assert_called_once()

    def test_handles_empty_memories(self, mock_llm, mock_memory, manager_state):
        mock_memory.get_memories.return_value = []
        node = create_research_manager(mock_llm, mock_memory)
        result = node(manager_state)
        assert "investment_plan" in result


class TestRiskManager:
    def test_creates_callable(self, mock_llm, mock_memory):
        node = create_risk_manager(mock_llm, mock_memory)
        assert callable(node)

    def test_returns_final_trade_decision(self, mock_llm, mock_memory, manager_state):
        mock_llm.invoke.return_value.content = "APPROVED: BUY AAPL with stop-loss."
        node = create_risk_manager(mock_llm, mock_memory)
        result = node(manager_state)

        assert result["final_trade_decision"] == "APPROVED: BUY AAPL with stop-loss."
        assert "risk_debate_state" in result

    def test_sets_judge_as_latest_speaker(self, mock_llm, mock_memory, manager_state):
        node = create_risk_manager(mock_llm, mock_memory)
        result = node(manager_state)

        state = result["risk_debate_state"]
        assert state["latest_speaker"] == "Judge"

    def test_preserves_risk_debate_histories(self, mock_llm, mock_memory, manager_state):
        node = create_risk_manager(mock_llm, mock_memory)
        result = node(manager_state)

        state = result["risk_debate_state"]
        assert state["aggressive_history"] == "Aggressive: go all in."
        assert state["conservative_history"] == "Conservative: reduce exposure."
        assert state["neutral_history"] == "Neutral: hold."

    def test_reads_fundamentals_report_correctly(self, mock_llm, mock_memory, manager_state):
        """Verify the bug fix: risk_manager reads fundamentals_report, not news_report."""
        node = create_risk_manager(mock_llm, mock_memory)
        node(manager_state)

        # The memory query should include the fundamentals report
        call_args = mock_memory.get_memories.call_args[0][0]
        assert "Strong balance sheet" in call_args

    def test_queries_memory_with_situation(self, mock_llm, mock_memory, manager_state):
        node = create_risk_manager(mock_llm, mock_memory)
        node(manager_state)
        mock_memory.get_memories.assert_called_once()
        situation = mock_memory.get_memories.call_args[0][0]
        assert "Market is bullish" in situation
        assert "Positive sentiment" in situation
