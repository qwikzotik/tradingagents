"""Tests for Alpha Vantage common utilities."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.alpha_vantage_common import (
    AlphaVantageRateLimitError,
    _filter_csv_by_date_range,
    _make_api_request,
    format_datetime_for_api,
    get_api_key,
)


class TestGetApiKey:
    @patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test-key-123"})
    def test_returns_key_from_env(self):
        assert get_api_key() == "test-key-123"

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_when_key_missing(self):
        with pytest.raises(ValueError, match="ALPHA_VANTAGE_API_KEY"):
            get_api_key()


class TestFormatDatetimeForApi:
    def test_yyyy_mm_dd_format(self):
        assert format_datetime_for_api("2026-01-15") == "20260115T0000"

    def test_yyyy_mm_dd_hh_mm_format(self):
        assert format_datetime_for_api("2026-01-15 14:30") == "20260115T1430"

    def test_already_correct_format(self):
        assert format_datetime_for_api("20260115T1430") == "20260115T1430"

    def test_datetime_object(self):
        dt = datetime(2026, 1, 15, 14, 30)
        assert format_datetime_for_api(dt) == "20260115T1430"

    def test_unsupported_string_format(self):
        with pytest.raises(ValueError, match="Unsupported date format"):
            format_datetime_for_api("15/01/2026")

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Date must be string or datetime"):
            format_datetime_for_api(12345)


class TestMakeApiRequest:
    @patch("tradingagents.dataflows.alpha_vantage_common.get_api_key", return_value="key")
    @patch("tradingagents.dataflows.alpha_vantage_common.requests.get")
    def test_returns_response_text(self, mock_get, _mock_key):
        mock_response = MagicMock()
        mock_response.text = "timestamp,open,close\n2026-01-15,100,105"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = _make_api_request("TIME_SERIES_DAILY", {"symbol": "AAPL"})
        assert result == "timestamp,open,close\n2026-01-15,100,105"

    @patch("tradingagents.dataflows.alpha_vantage_common.get_api_key", return_value="key")
    @patch("tradingagents.dataflows.alpha_vantage_common.requests.get")
    def test_passes_timeout(self, mock_get, _mock_key):
        mock_response = MagicMock()
        mock_response.text = "data"
        mock_get.return_value = mock_response

        _make_api_request("TEST", {})
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 30

    @patch("tradingagents.dataflows.alpha_vantage_common.get_api_key", return_value="key")
    @patch("tradingagents.dataflows.alpha_vantage_common.requests.get")
    def test_raises_on_rate_limit(self, mock_get, _mock_key):
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {"Information": "API rate limit exceeded. Please wait."}
        )
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with pytest.raises(AlphaVantageRateLimitError, match="rate limit"):
            _make_api_request("TEST", {})

    @patch("tradingagents.dataflows.alpha_vantage_common.get_api_key", return_value="key")
    @patch("tradingagents.dataflows.alpha_vantage_common.requests.get")
    def test_strips_entitlement_when_empty(self, mock_get, _mock_key):
        mock_response = MagicMock()
        mock_response.text = "data"
        mock_get.return_value = mock_response

        _make_api_request("TEST", {"entitlement": ""})
        call_params = mock_get.call_args[1]["params"]
        assert "entitlement" not in call_params


class TestFilterCsvByDateRange:
    def test_filters_rows_in_range(self):
        csv = "timestamp,value\n2026-01-10,1\n2026-01-15,2\n2026-01-20,3\n"
        result = _filter_csv_by_date_range(csv, "2026-01-12", "2026-01-18")
        assert "2026-01-15" in result
        assert "2026-01-10" not in result
        assert "2026-01-20" not in result

    def test_returns_original_on_empty(self):
        assert _filter_csv_by_date_range("", "2026-01-01", "2026-01-31") == ""

    def test_returns_original_on_parse_error(self):
        bad_csv = "not,valid\ncsv,data"
        result = _filter_csv_by_date_range(bad_csv, "2026-01-01", "2026-01-31")
        assert result == bad_csv
