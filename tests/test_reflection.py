"""Tests for the Reflector system."""

import pytest
from unittest.mock import MagicMock

from tradingagents.graph.reflection import Reflector
from tradingagents.agents.utils.memory import FinancialSituationMemory


class TestReflector:
    """Tests for the Reflector class."""

    @pytest.fixture
    def reflector(self, mock_llm):
        return Reflector(mock_llm)

    def test_init(self, reflector, mock_llm):
        assert reflector.quick_thinking_llm is mock_llm
        assert isinstance(reflector.reflection_system_prompt, str)

    def test_reflection_prompt_content(self, reflector):
        prompt = reflector.reflection_system_prompt
        assert "Reasoning" in prompt
        assert "Improvement" in prompt
        assert "Summary" in prompt

    def test_extract_current_situation(self, reflector, sample_agent_state):
        situation = reflector._extract_current_situation(sample_agent_state)
        assert "Market is bullish" in situation
        assert "Social sentiment" in situation
        assert "Positive earnings" in situation
        assert "Strong balance sheet" in situation

    def test_reflect_on_component(self, reflector, mock_llm):
        mock_llm.invoke.return_value.content = "Reflection analysis"
        result = reflector._reflect_on_component(
            "BULL", "Buy recommendation", "Market data", 1000
        )
        assert result == "Reflection analysis"
        mock_llm.invoke.assert_called_once()

    def test_reflect_on_component_passes_returns(self, reflector, mock_llm):
        mock_llm.invoke.return_value.content = "analysis"
        reflector._reflect_on_component("BULL", "report", "situation", 500)
        call_args = mock_llm.invoke.call_args[0][0]
        human_msg = call_args[1][1]
        assert "500" in human_msg

    def test_reflect_bull_researcher(self, reflector, mock_llm, sample_agent_state):
        mock_llm.invoke.return_value.content = "Bull reflection"
        mem = FinancialSituationMemory("bull")
        reflector.reflect_bull_researcher(sample_agent_state, 1000, mem)
        assert len(mem.documents) == 1

    def test_reflect_bear_researcher(self, reflector, mock_llm, sample_agent_state):
        mock_llm.invoke.return_value.content = "Bear reflection"
        mem = FinancialSituationMemory("bear")
        reflector.reflect_bear_researcher(sample_agent_state, -500, mem)
        assert len(mem.documents) == 1

    def test_reflect_trader(self, reflector, mock_llm, sample_agent_state):
        mock_llm.invoke.return_value.content = "Trader reflection"
        mem = FinancialSituationMemory("trader")
        reflector.reflect_trader(sample_agent_state, 200, mem)
        assert len(mem.documents) == 1

    def test_reflect_invest_judge(self, reflector, mock_llm, sample_agent_state):
        mock_llm.invoke.return_value.content = "Judge reflection"
        mem = FinancialSituationMemory("judge")
        reflector.reflect_invest_judge(sample_agent_state, 100, mem)
        assert len(mem.documents) == 1

    def test_reflect_risk_manager(self, reflector, mock_llm, sample_agent_state):
        mock_llm.invoke.return_value.content = "Risk reflection"
        mem = FinancialSituationMemory("risk")
        reflector.reflect_risk_manager(sample_agent_state, -100, mem)
        assert len(mem.documents) == 1

    def test_all_reflections_use_same_situation(self, reflector, mock_llm, sample_agent_state):
        mock_llm.invoke.return_value.content = "reflection"
        memories = [FinancialSituationMemory(f"mem_{i}") for i in range(5)]
        reflector.reflect_bull_researcher(sample_agent_state, 100, memories[0])
        reflector.reflect_bear_researcher(sample_agent_state, 100, memories[1])
        reflector.reflect_trader(sample_agent_state, 100, memories[2])
        reflector.reflect_invest_judge(sample_agent_state, 100, memories[3])
        reflector.reflect_risk_manager(sample_agent_state, 100, memories[4])
        # Each memory should have the same situation (concatenation of 4 reports)
        for mem in memories:
            assert "Market is bullish" in mem.documents[0]
