"""Tests for GraphSetup graph construction."""

import pytest
from unittest.mock import MagicMock, patch

from tradingagents.graph.setup import GraphSetup
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.agents.utils.memory import FinancialSituationMemory


@pytest.fixture
def mock_tool_nodes():
    """Create mock tool nodes for all analyst types."""
    return {
        "market": MagicMock(),
        "social": MagicMock(),
        "news": MagicMock(),
        "fundamentals": MagicMock(),
    }


@pytest.fixture
def graph_setup(mock_llm, mock_tool_nodes):
    """Create a GraphSetup with mocked dependencies."""
    return GraphSetup(
        quick_thinking_llm=mock_llm,
        deep_thinking_llm=mock_llm,
        tool_nodes=mock_tool_nodes,
        bull_memory=FinancialSituationMemory("bull"),
        bear_memory=FinancialSituationMemory("bear"),
        trader_memory=FinancialSituationMemory("trader"),
        invest_judge_memory=FinancialSituationMemory("judge"),
        risk_manager_memory=FinancialSituationMemory("risk"),
        conditional_logic=ConditionalLogic(),
    )


# Patches needed for all graph compilation tests
ALL_AGENT_PATCHES = [
    "tradingagents.graph.setup.create_market_analyst",
    "tradingagents.graph.setup.create_social_media_analyst",
    "tradingagents.graph.setup.create_news_analyst",
    "tradingagents.graph.setup.create_fundamentals_analyst",
    "tradingagents.graph.setup.create_bull_researcher",
    "tradingagents.graph.setup.create_bear_researcher",
    "tradingagents.graph.setup.create_research_manager",
    "tradingagents.graph.setup.create_trader",
    "tradingagents.graph.setup.create_aggressive_debator",
    "tradingagents.graph.setup.create_neutral_debator",
    "tradingagents.graph.setup.create_conservative_debator",
    "tradingagents.graph.setup.create_risk_manager",
    "tradingagents.graph.setup.create_msg_delete",
]


def _patch_all_agents():
    """Context manager that patches all agent creation functions."""
    from contextlib import ExitStack
    stack = ExitStack()
    mocks = []
    for target in ALL_AGENT_PATCHES:
        m = stack.enter_context(patch(target, return_value=lambda state: state))
        mocks.append(m)
    return stack, mocks


class TestGraphSetup:
    """Tests for GraphSetup class."""

    def test_setup_graph_compiles(self, graph_setup):
        """Test that setup_graph produces a compiled graph."""
        from contextlib import ExitStack
        with ExitStack() as stack:
            for target in ALL_AGENT_PATCHES:
                stack.enter_context(patch(target, return_value=lambda state: state))
            graph = graph_setup.setup_graph(["market", "social", "news", "fundamentals"])
            assert graph is not None

    def test_setup_graph_empty_analysts_raises(self, graph_setup):
        with pytest.raises(ValueError, match="no analysts selected"):
            graph_setup.setup_graph([])

    def test_setup_graph_single_analyst(self, graph_setup):
        """Test that a single analyst selection works."""
        from contextlib import ExitStack
        with ExitStack() as stack:
            for target in ALL_AGENT_PATCHES:
                stack.enter_context(patch(target, return_value=lambda state: state))
            graph = graph_setup.setup_graph(["market"])
            assert graph is not None

    def test_setup_graph_fundamentals_only(self, graph_setup):
        """Test with only fundamentals analyst selected."""
        from contextlib import ExitStack
        with ExitStack() as stack:
            for target in ALL_AGENT_PATCHES:
                stack.enter_context(patch(target, return_value=lambda state: state))
            graph = graph_setup.setup_graph(["fundamentals"])
            assert graph is not None

    def test_init_stores_components(self, graph_setup, mock_llm):
        assert graph_setup.quick_thinking_llm is mock_llm
        assert graph_setup.deep_thinking_llm is mock_llm
        assert isinstance(graph_setup.conditional_logic, ConditionalLogic)
