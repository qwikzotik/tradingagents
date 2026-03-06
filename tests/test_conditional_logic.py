"""Tests for the ConditionalLogic graph routing."""

import pytest
from unittest.mock import MagicMock

from tradingagents.graph.conditional_logic import ConditionalLogic


@pytest.fixture
def logic():
    return ConditionalLogic(max_debate_rounds=2, max_risk_discuss_rounds=2)


@pytest.fixture
def logic_single():
    return ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=1)


def _make_state_with_tool_calls(has_tool_calls=True):
    """Helper to create a state with a mock message."""
    msg = MagicMock()
    msg.tool_calls = [{"name": "some_tool"}] if has_tool_calls else []
    return {"messages": [msg]}


class TestAnalystContinuation:
    """Tests for analyst should_continue_* methods."""

    def test_market_continues_with_tool_calls(self, logic):
        state = _make_state_with_tool_calls(True)
        assert logic.should_continue_market(state) == "tools_market"

    def test_market_stops_without_tool_calls(self, logic):
        state = _make_state_with_tool_calls(False)
        assert logic.should_continue_market(state) == "Msg Clear Market"

    def test_social_continues_with_tool_calls(self, logic):
        state = _make_state_with_tool_calls(True)
        assert logic.should_continue_social(state) == "tools_social"

    def test_social_stops_without_tool_calls(self, logic):
        state = _make_state_with_tool_calls(False)
        assert logic.should_continue_social(state) == "Msg Clear Social"

    def test_news_continues_with_tool_calls(self, logic):
        state = _make_state_with_tool_calls(True)
        assert logic.should_continue_news(state) == "tools_news"

    def test_news_stops_without_tool_calls(self, logic):
        state = _make_state_with_tool_calls(False)
        assert logic.should_continue_news(state) == "Msg Clear News"

    def test_fundamentals_continues_with_tool_calls(self, logic):
        state = _make_state_with_tool_calls(True)
        assert logic.should_continue_fundamentals(state) == "tools_fundamentals"

    def test_fundamentals_stops_without_tool_calls(self, logic):
        state = _make_state_with_tool_calls(False)
        assert logic.should_continue_fundamentals(state) == "Msg Clear Fundamentals"


class TestDebateContinuation:
    """Tests for investment debate routing."""

    def test_routes_to_bear_after_bull(self, logic):
        state = {
            "investment_debate_state": {
                "count": 1,
                "current_response": "Bull: I think we should buy",
            }
        }
        assert logic.should_continue_debate(state) == "Bear Researcher"

    def test_routes_to_bull_after_bear(self, logic):
        state = {
            "investment_debate_state": {
                "count": 1,
                "current_response": "Bear: I think we should sell",
            }
        }
        assert logic.should_continue_debate(state) == "Bull Researcher"

    def test_routes_to_manager_when_max_rounds_reached(self, logic):
        state = {
            "investment_debate_state": {
                "count": 4,  # 2 * max_debate_rounds(2)
                "current_response": "Bull: final",
            }
        }
        assert logic.should_continue_debate(state) == "Research Manager"

    def test_single_round_stops_at_count_2(self, logic_single):
        state = {
            "investment_debate_state": {
                "count": 2,  # 2 * 1
                "current_response": "Bull: done",
            }
        }
        assert logic_single.should_continue_debate(state) == "Research Manager"

    def test_single_round_continues_at_count_1(self, logic_single):
        state = {
            "investment_debate_state": {
                "count": 1,
                "current_response": "Bull: first arg",
            }
        }
        assert logic_single.should_continue_debate(state) == "Bear Researcher"


class TestRiskAnalysisContinuation:
    """Tests for risk analysis routing."""

    def test_routes_to_conservative_after_aggressive(self, logic):
        state = {
            "risk_debate_state": {
                "count": 1,
                "latest_speaker": "Aggressive Analyst",
            }
        }
        assert logic.should_continue_risk_analysis(state) == "Conservative Analyst"

    def test_routes_to_neutral_after_conservative(self, logic):
        state = {
            "risk_debate_state": {
                "count": 2,
                "latest_speaker": "Conservative Analyst",
            }
        }
        assert logic.should_continue_risk_analysis(state) == "Neutral Analyst"

    def test_routes_to_aggressive_after_neutral(self, logic):
        state = {
            "risk_debate_state": {
                "count": 3,
                "latest_speaker": "Neutral Analyst",
            }
        }
        assert logic.should_continue_risk_analysis(state) == "Aggressive Analyst"

    def test_routes_to_judge_when_max_rounds_reached(self, logic):
        state = {
            "risk_debate_state": {
                "count": 6,  # 3 * max_risk_discuss_rounds(2)
                "latest_speaker": "Aggressive Analyst",
            }
        }
        assert logic.should_continue_risk_analysis(state) == "Risk Judge"

    def test_single_round_stops_at_count_3(self, logic_single):
        state = {
            "risk_debate_state": {
                "count": 3,  # 3 * 1
                "latest_speaker": "Neutral Analyst",
            }
        }
        assert logic_single.should_continue_risk_analysis(state) == "Risk Judge"
