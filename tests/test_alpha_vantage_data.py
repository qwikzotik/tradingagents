"""Tests for Alpha Vantage news and fundamentals modules."""

from unittest.mock import patch, MagicMock

from tradingagents.dataflows.alpha_vantage_news import (
    get_news,
    get_global_news,
    get_insider_transactions,
)
from tradingagents.dataflows.alpha_vantage_fundamentals import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
)


class TestAlphaVantageNews:
    @patch("tradingagents.dataflows.alpha_vantage_news._make_api_request")
    @patch("tradingagents.dataflows.alpha_vantage_news.format_datetime_for_api")
    def test_get_news_calls_api_with_correct_params(self, mock_fmt, mock_api):
        mock_fmt.side_effect = lambda d: d.replace("-", "") + "T0000"
        mock_api.return_value = '{"feed": []}'

        result = get_news("AAPL", "2026-01-01", "2026-01-15")

        mock_api.assert_called_once_with(
            "NEWS_SENTIMENT",
            {
                "tickers": "AAPL",
                "time_from": "20260101T0000",
                "time_to": "20260115T0000",
            },
        )

    @patch("tradingagents.dataflows.alpha_vantage_news._make_api_request")
    @patch("tradingagents.dataflows.alpha_vantage_news.format_datetime_for_api")
    def test_get_global_news_calculates_date_range(self, mock_fmt, mock_api):
        mock_fmt.side_effect = lambda d: d.replace("-", "") + "T0000"
        mock_api.return_value = "news data"

        get_global_news("2026-01-15", look_back_days=7, limit=10)

        call_args = mock_api.call_args[0]
        assert call_args[0] == "NEWS_SENTIMENT"
        params = call_args[1]
        assert params["limit"] == "10"
        assert "topics" in params

    @patch("tradingagents.dataflows.alpha_vantage_news._make_api_request")
    def test_get_insider_transactions_calls_api(self, mock_api):
        mock_api.return_value = "insider data"

        result = get_insider_transactions("IBM")

        mock_api.assert_called_once_with(
            "INSIDER_TRANSACTIONS", {"symbol": "IBM"}
        )
        assert result == "insider data"


class TestAlphaVantageFundamentals:
    @patch("tradingagents.dataflows.alpha_vantage_fundamentals._make_api_request")
    def test_get_fundamentals(self, mock_api):
        mock_api.return_value = "overview data"
        result = get_fundamentals("AAPL")
        mock_api.assert_called_once_with("OVERVIEW", {"symbol": "AAPL"})
        assert result == "overview data"

    @patch("tradingagents.dataflows.alpha_vantage_fundamentals._make_api_request")
    def test_get_balance_sheet(self, mock_api):
        mock_api.return_value = "balance data"
        result = get_balance_sheet("AAPL")
        mock_api.assert_called_once_with("BALANCE_SHEET", {"symbol": "AAPL"})
        assert result == "balance data"

    @patch("tradingagents.dataflows.alpha_vantage_fundamentals._make_api_request")
    def test_get_cashflow(self, mock_api):
        mock_api.return_value = "cashflow data"
        result = get_cashflow("AAPL")
        mock_api.assert_called_once_with("CASH_FLOW", {"symbol": "AAPL"})
        assert result == "cashflow data"

    @patch("tradingagents.dataflows.alpha_vantage_fundamentals._make_api_request")
    def test_get_income_statement(self, mock_api):
        mock_api.return_value = "income data"
        result = get_income_statement("AAPL")
        mock_api.assert_called_once_with("INCOME_STATEMENT", {"symbol": "AAPL"})
        assert result == "income data"
