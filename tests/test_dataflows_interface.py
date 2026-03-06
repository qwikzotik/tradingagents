"""Tests for the dataflows interface module (vendor routing)."""

import pytest
from unittest.mock import patch, MagicMock

from tradingagents.dataflows.interface import (
    TOOLS_CATEGORIES,
    VENDOR_METHODS,
    VENDOR_LIST,
    get_category_for_method,
    get_vendor,
    route_to_vendor,
)
from tradingagents.dataflows.alpha_vantage_common import AlphaVantageRateLimitError


class TestToolsCategories:
    """Tests for the TOOLS_CATEGORIES structure."""

    def test_has_four_categories(self):
        assert len(TOOLS_CATEGORIES) == 4

    def test_categories_have_description_and_tools(self):
        for cat, info in TOOLS_CATEGORIES.items():
            assert "description" in info
            assert "tools" in info
            assert len(info["tools"]) > 0

    def test_core_stock_apis_tools(self):
        assert "get_stock_data" in TOOLS_CATEGORIES["core_stock_apis"]["tools"]

    def test_technical_indicators_tools(self):
        assert "get_indicators" in TOOLS_CATEGORIES["technical_indicators"]["tools"]

    def test_fundamental_data_tools(self):
        tools = TOOLS_CATEGORIES["fundamental_data"]["tools"]
        assert "get_fundamentals" in tools
        assert "get_balance_sheet" in tools
        assert "get_cashflow" in tools
        assert "get_income_statement" in tools

    def test_news_data_tools(self):
        tools = TOOLS_CATEGORIES["news_data"]["tools"]
        assert "get_news" in tools
        assert "get_global_news" in tools
        assert "get_insider_transactions" in tools


class TestVendorMethods:
    """Tests for the VENDOR_METHODS mapping."""

    def test_all_tools_have_vendor_methods(self):
        for cat, info in TOOLS_CATEGORIES.items():
            for tool in info["tools"]:
                assert tool in VENDOR_METHODS, f"Missing VENDOR_METHODS for {tool}"

    def test_vendor_methods_have_callable_implementations(self):
        for method, vendors in VENDOR_METHODS.items():
            for vendor_name, impl in vendors.items():
                func = impl[0] if isinstance(impl, list) else impl
                assert callable(func), f"{method}/{vendor_name} not callable"


class TestGetCategoryForMethod:
    """Tests for get_category_for_method function."""

    def test_stock_data_category(self):
        assert get_category_for_method("get_stock_data") == "core_stock_apis"

    def test_indicators_category(self):
        assert get_category_for_method("get_indicators") == "technical_indicators"

    def test_fundamentals_category(self):
        assert get_category_for_method("get_fundamentals") == "fundamental_data"

    def test_news_category(self):
        assert get_category_for_method("get_news") == "news_data"

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="not found in any category"):
            get_category_for_method("nonexistent_method")


class TestGetVendor:
    """Tests for get_vendor function."""

    @patch("tradingagents.dataflows.interface.get_config")
    def test_returns_category_vendor(self, mock_config):
        mock_config.return_value = {
            "data_vendors": {"core_stock_apis": "yfinance"},
            "tool_vendors": {},
        }
        assert get_vendor("core_stock_apis") == "yfinance"

    @patch("tradingagents.dataflows.interface.get_config")
    def test_tool_level_overrides_category(self, mock_config):
        mock_config.return_value = {
            "data_vendors": {"core_stock_apis": "yfinance"},
            "tool_vendors": {"get_stock_data": "alpha_vantage"},
        }
        assert get_vendor("core_stock_apis", "get_stock_data") == "alpha_vantage"

    @patch("tradingagents.dataflows.interface.get_config")
    def test_falls_back_to_category_when_no_tool_override(self, mock_config):
        mock_config.return_value = {
            "data_vendors": {"core_stock_apis": "yfinance"},
            "tool_vendors": {},
        }
        assert get_vendor("core_stock_apis", "get_stock_data") == "yfinance"

    @patch("tradingagents.dataflows.interface.get_config")
    def test_returns_default_when_no_config(self, mock_config):
        mock_config.return_value = {"data_vendors": {}, "tool_vendors": {}}
        assert get_vendor("nonexistent") == "default"


class TestRouteToVendor:
    """Tests for route_to_vendor function."""

    @patch("tradingagents.dataflows.interface.get_vendor")
    def test_routes_to_primary_vendor(self, mock_get_vendor):
        mock_get_vendor.return_value = "yfinance"
        mock_impl = MagicMock(return_value="data")
        with patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {"get_stock_data": {"yfinance": mock_impl}},
        ):
            result = route_to_vendor("get_stock_data", "AAPL")
            mock_impl.assert_called_once_with("AAPL")
            assert result == "data"

    @patch("tradingagents.dataflows.interface.get_vendor")
    def test_fallback_on_rate_limit(self, mock_get_vendor):
        mock_get_vendor.return_value = "alpha_vantage"
        failing_impl = MagicMock(side_effect=AlphaVantageRateLimitError("rate limited"))
        fallback_impl = MagicMock(return_value="fallback_data")
        with patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {
                "get_stock_data": {
                    "alpha_vantage": failing_impl,
                    "yfinance": fallback_impl,
                }
            },
        ):
            result = route_to_vendor("get_stock_data", "AAPL")
            assert result == "fallback_data"

    @patch("tradingagents.dataflows.interface.get_vendor")
    def test_non_rate_limit_error_propagates(self, mock_get_vendor):
        mock_get_vendor.return_value = "yfinance"
        mock_impl = MagicMock(side_effect=ValueError("bad data"))
        with patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {"get_stock_data": {"yfinance": mock_impl}},
        ):
            with pytest.raises(ValueError, match="bad data"):
                route_to_vendor("get_stock_data", "AAPL")

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="not found in any category"):
            route_to_vendor("totally_fake_method")

    @patch("tradingagents.dataflows.interface.get_vendor")
    def test_no_vendor_available_raises(self, mock_get_vendor):
        mock_get_vendor.return_value = "nonexistent_vendor"
        with patch.dict(
            "tradingagents.dataflows.interface.VENDOR_METHODS",
            {"get_stock_data": {}},
        ):
            with pytest.raises(RuntimeError, match="No available vendor"):
                route_to_vendor("get_stock_data")
