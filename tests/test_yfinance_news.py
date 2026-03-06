"""Tests for yfinance news data fetching functions."""

from unittest.mock import MagicMock, patch
from datetime import datetime

from tradingagents.dataflows.yfinance_news import (
    _extract_article_data,
    _format_article_str,
    get_news_yfinance,
    get_global_news_yfinance,
)


class TestExtractArticleData:
    def test_nested_content_structure(self):
        article = {
            "content": {
                "title": "AAPL Earnings Beat",
                "summary": "Apple reports strong Q1",
                "provider": {"displayName": "Reuters"},
                "canonicalUrl": {"url": "https://example.com/article"},
                "pubDate": "2026-01-15T10:00:00Z",
            }
        }
        result = _extract_article_data(article)
        assert result["title"] == "AAPL Earnings Beat"
        assert result["summary"] == "Apple reports strong Q1"
        assert result["publisher"] == "Reuters"
        assert result["link"] == "https://example.com/article"
        assert result["pub_date"] is not None

    def test_flat_structure(self):
        article = {
            "title": "Market Update",
            "summary": "Stocks rose today",
            "publisher": "Bloomberg",
            "link": "https://example.com",
        }
        result = _extract_article_data(article)
        assert result["title"] == "Market Update"
        assert result["publisher"] == "Bloomberg"
        assert result["pub_date"] is None

    def test_missing_fields_use_defaults(self):
        article = {"content": {}}
        result = _extract_article_data(article)
        assert result["title"] == "No title"
        assert result["publisher"] == "Unknown"
        assert result["summary"] == ""
        assert result["link"] == ""

    def test_invalid_pub_date_returns_none(self):
        article = {"content": {"pubDate": "not-a-date"}}
        result = _extract_article_data(article)
        assert result["pub_date"] is None

    def test_clickthrough_url_fallback(self):
        article = {
            "content": {
                "clickThroughUrl": {"url": "https://click.example.com"},
            }
        }
        result = _extract_article_data(article)
        assert result["link"] == "https://click.example.com"


class TestFormatArticleStr:
    def test_basic_format(self):
        result = _format_article_str("Title", "Publisher")
        assert "### Title (source: Publisher)" in result

    def test_with_summary_and_link(self):
        result = _format_article_str("Title", "Pub", "Summary text", "https://link.com")
        assert "Summary text" in result
        assert "Link: https://link.com" in result

    def test_without_optional_fields(self):
        result = _format_article_str("Title", "Pub")
        assert "Link:" not in result


class TestGetNewsYfinance:
    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    def test_returns_formatted_news(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.get_news.return_value = [
            {
                "title": "Test Article",
                "publisher": "TestPub",
                "summary": "Summary",
                "link": "https://example.com",
            }
        ]
        mock_ticker_cls.return_value = mock_ticker

        result = get_news_yfinance("AAPL", "2026-01-01", "2026-01-31")
        assert "AAPL News" in result
        assert "Test Article" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    def test_no_news_returns_message(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.get_news.return_value = []
        mock_ticker_cls.return_value = mock_ticker

        result = get_news_yfinance("AAPL", "2026-01-01", "2026-01-31")
        assert "No news found" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    def test_handles_request_exception(self, mock_ticker_cls):
        from requests.exceptions import RequestException

        mock_ticker_cls.side_effect = RequestException("timeout")

        result = get_news_yfinance("AAPL", "2026-01-01", "2026-01-31")
        assert "Error fetching news" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    def test_filters_by_date_range(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.get_news.return_value = [
            {
                "content": {
                    "title": "Old Article",
                    "provider": {"displayName": "Pub"},
                    "pubDate": "2025-06-01T10:00:00Z",
                }
            },
            {
                "content": {
                    "title": "Recent Article",
                    "provider": {"displayName": "Pub"},
                    "pubDate": "2026-01-15T10:00:00Z",
                }
            },
        ]
        mock_ticker_cls.return_value = mock_ticker

        result = get_news_yfinance("AAPL", "2026-01-01", "2026-01-31")
        assert "Recent Article" in result
        assert "Old Article" not in result


class TestGetGlobalNewsYfinance:
    @patch("tradingagents.dataflows.yfinance_news.yf.Search")
    def test_returns_formatted_global_news(self, mock_search_cls):
        mock_search = MagicMock()
        mock_search.news = [
            {"title": "Fed Rate Decision", "publisher": "Reuters", "link": ""}
        ]
        mock_search_cls.return_value = mock_search

        result = get_global_news_yfinance("2026-01-15")
        assert "Global Market News" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Search")
    def test_deduplicates_articles(self, mock_search_cls):
        mock_search = MagicMock()
        mock_search.news = [
            {"title": "Same Title", "publisher": "Pub1"},
            {"title": "Same Title", "publisher": "Pub2"},
        ]
        mock_search_cls.return_value = mock_search

        result = get_global_news_yfinance("2026-01-15")
        assert result.count("Same Title") == 1

    @patch("tradingagents.dataflows.yfinance_news.yf.Search")
    def test_no_news_returns_message(self, mock_search_cls):
        mock_search = MagicMock()
        mock_search.news = []
        mock_search_cls.return_value = mock_search

        result = get_global_news_yfinance("2026-01-15")
        assert "No global news found" in result
