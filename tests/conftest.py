"""Shared fixtures for the TradingAgents test suite."""

import sys
import types

# Stub out multitasking if not available (yfinance dependency that fails to build
# on some platforms due to setuptools incompatibility)
if "multitasking" not in sys.modules:
    try:
        import multitasking  # noqa: F401
    except ImportError:
        mt = types.ModuleType("multitasking")
        mt.set_max_threads = lambda x: None
        mt.task = lambda *args, **kwargs: (lambda f: f)
        sys.modules["multitasking"] = mt

import pytest
from unittest.mock import MagicMock

from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.default_config import DEFAULT_CONFIG


@pytest.fixture
def default_config():
    """Return a fresh copy of default config for each test."""
    return DEFAULT_CONFIG.copy()


@pytest.fixture
def memory():
    """Return a fresh FinancialSituationMemory instance."""
    return FinancialSituationMemory("test_memory")


@pytest.fixture
def sample_situations():
    """Sample financial situations for memory tests."""
    return [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions.",
        ),
    ]


@pytest.fixture
def invest_debate_state():
    """Return a sample InvestDebateState."""
    return InvestDebateState(
        bull_history="Bull: I recommend buying.",
        bear_history="Bear: I recommend selling.",
        history="Bull and Bear debated.",
        current_response="Bull: final argument",
        judge_decision="BUY",
        count=2,
    )


@pytest.fixture
def risk_debate_state():
    """Return a sample RiskDebateState."""
    return RiskDebateState(
        aggressive_history="Aggressive: go all in.",
        conservative_history="Conservative: reduce exposure.",
        neutral_history="Neutral: maintain current position.",
        history="Risk discussion completed.",
        latest_speaker="Aggressive Analyst",
        current_aggressive_response="Aggressive: go all in.",
        current_conservative_response="Conservative: reduce exposure.",
        current_neutral_response="Neutral: maintain current position.",
        judge_decision="HOLD with reduced position",
        count=3,
    )


@pytest.fixture
def sample_agent_state(invest_debate_state, risk_debate_state):
    """Return a sample AgentState-like dict for testing."""
    return {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2026-01-15",
        "sender": "test",
        "market_report": "Market is bullish with strong momentum.",
        "sentiment_report": "Social sentiment is positive.",
        "news_report": "Positive earnings reported.",
        "fundamentals_report": "Strong balance sheet and cash flow.",
        "investment_debate_state": invest_debate_state,
        "risk_debate_state": risk_debate_state,
        "investment_plan": "Buy 100 shares at market open.",
        "trader_investment_plan": "Execute buy order for AAPL.",
        "final_trade_decision": "BUY AAPL - 100 shares at market price.",
    }


@pytest.fixture
def mock_llm():
    """Return a mock LLM that returns predictable responses."""
    llm = MagicMock()
    response = MagicMock()
    response.content = "BUY"
    llm.invoke.return_value = response
    return llm
