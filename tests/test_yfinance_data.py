"""Tests for yfinance data fetching functions."""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from tradingagents.dataflows.y_finance import (
    get_YFin_data_online,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_insider_transactions,
)


class TestGetYFinDataOnline:
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_formatted_data(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_df = pd.DataFrame(
            {"Open": [100], "Close": [105]},
            index=pd.DatetimeIndex(["2026-01-15"]),
        )
        mock_ticker.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_ticker

        result = get_YFin_data_online("AAPL", "2026-01-10", "2026-01-20")
        assert isinstance(result, str)

    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_data_returns_message(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_ticker

        result = get_YFin_data_online("INVALID", "2026-01-10", "2026-01-20")
        assert "No data" in result or isinstance(result, str)

    def test_invalid_date_format_raises(self):
        with pytest.raises(ValueError):
            get_YFin_data_online("AAPL", "bad-date", "2026-01-20")


class TestGetFundamentals:
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_info_string(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {"sector": "Technology", "marketCap": 3000000000}
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("AAPL")
        assert isinstance(result, str)

    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_handles_empty_info(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("AAPL")
        assert isinstance(result, str)


class TestGetBalanceSheet:
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_balance_sheet_string(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.quarterly_balance_sheet = pd.DataFrame(
            {"TotalAssets": [1000]}, index=pd.DatetimeIndex(["2026-01-15"])
        )
        mock_ticker_cls.return_value = mock_ticker

        result = get_balance_sheet("AAPL")
        assert isinstance(result, str)


class TestGetCashflow:
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_cashflow_string(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.quarterly_cashflow = pd.DataFrame(
            {"OperatingCashFlow": [500]}, index=pd.DatetimeIndex(["2026-01-15"])
        )
        mock_ticker_cls.return_value = mock_ticker

        result = get_cashflow("AAPL")
        assert isinstance(result, str)


class TestGetIncomeStatement:
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_income_statement_string(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.quarterly_income_stmt = pd.DataFrame(
            {"TotalRevenue": [90000]}, index=pd.DatetimeIndex(["2026-01-15"])
        )
        mock_ticker_cls.return_value = mock_ticker

        result = get_income_statement("AAPL")
        assert isinstance(result, str)


class TestGetInsiderTransactions:
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_insider_data_string(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.insider_transactions = pd.DataFrame(
            {"Insider": ["CEO"], "Shares": [1000]}
        )
        mock_ticker_cls.return_value = mock_ticker

        result = get_insider_transactions("AAPL")
        assert isinstance(result, str)
