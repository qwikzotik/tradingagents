"""Tests for risk management debator agent nodes."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator
from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator


@pytest.fixture
def debator_state():
    """State for debator nodes."""
    return {
        "market_report": "Market is volatile.",
        "sentiment_report": "Mixed sentiment.",
        "news_report": "Earnings report pending.",
        "fundamentals_report": "Average fundamentals.",
        "trader_investment_plan": "Buy 50 shares of AAPL.",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
    }


class TestAggressiveDebator:
    def test_creates_callable(self, mock_llm):
        node = create_aggressive_debator(mock_llm)
        assert callable(node)

    def test_returns_updated_risk_state(self, mock_llm, debator_state):
        mock_llm.invoke.return_value.content = "Go all in on AAPL!"
        node = create_aggressive_debator(mock_llm)
        result = node(debator_state)

        state = result["risk_debate_state"]
        assert "Aggressive Analyst:" in state["history"]
        assert "Aggressive Analyst:" in state["aggressive_history"]
        assert state["latest_speaker"] == "Aggressive"
        assert state["count"] == 1

    def test_preserves_other_histories(self, mock_llm, debator_state):
        debator_state["risk_debate_state"]["conservative_history"] = "Be cautious."
        debator_state["risk_debate_state"]["neutral_history"] = "Hold steady."
        node = create_aggressive_debator(mock_llm)
        result = node(debator_state)

        state = result["risk_debate_state"]
        assert state["conservative_history"] == "Be cautious."
        assert state["neutral_history"] == "Hold steady."

    def test_invokes_llm_once(self, mock_llm, debator_state):
        node = create_aggressive_debator(mock_llm)
        node(debator_state)
        mock_llm.invoke.assert_called_once()


class TestConservativeDebator:
    def test_creates_callable(self, mock_llm):
        node = create_conservative_debator(mock_llm)
        assert callable(node)

    def test_returns_conservative_perspective(self, mock_llm, debator_state):
        mock_llm.invoke.return_value.content = "Reduce exposure to limit risk."
        node = create_conservative_debator(mock_llm)
        result = node(debator_state)

        state = result["risk_debate_state"]
        assert "Conservative Analyst:" in state["conservative_history"]
        assert state["latest_speaker"] == "Conservative"
        assert state["count"] == 1

    def test_preserves_aggressive_history(self, mock_llm, debator_state):
        debator_state["risk_debate_state"]["aggressive_history"] = "Go all in."
        node = create_conservative_debator(mock_llm)
        result = node(debator_state)

        assert result["risk_debate_state"]["aggressive_history"] == "Go all in."


class TestNeutralDebator:
    def test_creates_callable(self, mock_llm):
        node = create_neutral_debator(mock_llm)
        assert callable(node)

    def test_returns_neutral_perspective(self, mock_llm, debator_state):
        mock_llm.invoke.return_value.content = "Maintain current allocation."
        node = create_neutral_debator(mock_llm)
        result = node(debator_state)

        state = result["risk_debate_state"]
        assert "Neutral Analyst:" in state["neutral_history"]
        assert state["latest_speaker"] == "Neutral"
        assert state["count"] == 1

    def test_increments_count(self, mock_llm, debator_state):
        debator_state["risk_debate_state"]["count"] = 5
        node = create_neutral_debator(mock_llm)
        result = node(debator_state)
        assert result["risk_debate_state"]["count"] == 6
