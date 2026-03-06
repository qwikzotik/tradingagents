"""Tests for the SignalProcessor."""

import pytest
from unittest.mock import MagicMock

from tradingagents.graph.signal_processing import SignalProcessor


class TestSignalProcessor:
    """Tests for SignalProcessor class."""

    def test_init(self, mock_llm):
        sp = SignalProcessor(mock_llm)
        assert sp.quick_thinking_llm is mock_llm

    def test_process_signal_calls_llm(self, mock_llm):
        sp = SignalProcessor(mock_llm)
        result = sp.process_signal("Full report suggesting buying AAPL")
        mock_llm.invoke.assert_called_once()

    def test_process_signal_returns_content(self, mock_llm):
        mock_llm.invoke.return_value.content = "BUY"
        sp = SignalProcessor(mock_llm)
        result = sp.process_signal("Buy recommendation report")
        assert result == "BUY"

    def test_process_signal_passes_correct_messages(self, mock_llm):
        sp = SignalProcessor(mock_llm)
        sp.process_signal("Some signal text")
        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0][0] == "system"
        assert call_args[1][0] == "human"
        assert call_args[1][1] == "Some signal text"

    def test_process_signal_system_prompt_mentions_decisions(self, mock_llm):
        sp = SignalProcessor(mock_llm)
        sp.process_signal("test")
        call_args = mock_llm.invoke.call_args[0][0]
        system_prompt = call_args[0][1]
        assert "SELL" in system_prompt
        assert "BUY" in system_prompt
        assert "HOLD" in system_prompt

    def test_process_signal_sell(self, mock_llm):
        mock_llm.invoke.return_value.content = "SELL"
        sp = SignalProcessor(mock_llm)
        assert sp.process_signal("sell everything") == "SELL"

    def test_process_signal_hold(self, mock_llm):
        mock_llm.invoke.return_value.content = "HOLD"
        sp = SignalProcessor(mock_llm)
        assert sp.process_signal("maintain position") == "HOLD"
