"""Tests for the Propagator state initialization."""

import pytest
from tradingagents.graph.propagation import Propagator


class TestPropagator:
    """Tests for the Propagator class."""

    def test_default_recursion_limit(self):
        p = Propagator()
        assert p.max_recur_limit == 100

    def test_custom_recursion_limit(self):
        p = Propagator(max_recur_limit=50)
        assert p.max_recur_limit == 50

    def test_create_initial_state_has_required_keys(self):
        p = Propagator()
        state = p.create_initial_state("AAPL", "2026-01-15")
        required = [
            "messages",
            "company_of_interest",
            "trade_date",
            "investment_debate_state",
            "risk_debate_state",
            "market_report",
            "fundamentals_report",
            "sentiment_report",
            "news_report",
        ]
        for key in required:
            assert key in state, f"Missing key: {key}"

    def test_create_initial_state_company(self):
        p = Propagator()
        state = p.create_initial_state("NVDA", "2026-01-15")
        assert state["company_of_interest"] == "NVDA"

    def test_create_initial_state_date_as_string(self):
        p = Propagator()
        state = p.create_initial_state("AAPL", "2026-01-15")
        assert state["trade_date"] == "2026-01-15"
        assert isinstance(state["trade_date"], str)

    def test_create_initial_state_messages(self):
        p = Propagator()
        state = p.create_initial_state("AAPL", "2026-01-15")
        assert state["messages"] == [("human", "AAPL")]

    def test_create_initial_state_reports_empty(self):
        p = Propagator()
        state = p.create_initial_state("AAPL", "2026-01-15")
        assert state["market_report"] == ""
        assert state["fundamentals_report"] == ""
        assert state["sentiment_report"] == ""
        assert state["news_report"] == ""

    def test_create_initial_state_debate_states_zeroed(self):
        p = Propagator()
        state = p.create_initial_state("AAPL", "2026-01-15")
        assert state["investment_debate_state"]["count"] == 0
        assert state["investment_debate_state"]["history"] == ""
        assert state["risk_debate_state"]["count"] == 0
        assert state["risk_debate_state"]["history"] == ""

    def test_get_graph_args_basic(self):
        p = Propagator(max_recur_limit=50)
        args = p.get_graph_args()
        assert args["stream_mode"] == "values"
        assert args["config"]["recursion_limit"] == 50
        assert "callbacks" not in args["config"]

    def test_get_graph_args_with_callbacks(self):
        p = Propagator()
        cb = [lambda: None]
        args = p.get_graph_args(callbacks=cb)
        assert args["config"]["callbacks"] is cb

    def test_get_graph_args_no_callbacks_when_empty(self):
        p = Propagator()
        args = p.get_graph_args(callbacks=[])
        assert "callbacks" not in args["config"]
