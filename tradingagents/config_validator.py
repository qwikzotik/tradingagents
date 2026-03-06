"""Startup configuration validation.

Validates config dictionaries before they are used to initialize
the TradingAgentsGraph, providing clear error messages for
misconfigurations that would otherwise surface as cryptic runtime errors.
"""

import os
from typing import Dict, Any, List

from tradingagents.llm_clients.validators import validate_model

SUPPORTED_PROVIDERS = {"openai", "anthropic", "google", "xai", "ollama", "openrouter"}

VALID_ANALYSTS = {"market", "social", "news", "fundamentals"}

VALID_DATA_VENDORS = {"yfinance", "alpha_vantage"}

DATA_VENDOR_CATEGORIES = {
    "core_stock_apis",
    "technical_indicators",
    "fundamental_data",
    "news_data",
}

# Provider → (env var name, display name)
PROVIDER_API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    # ollama doesn't need an API key
}


class ConfigurationError(Exception):
    """Raised when the configuration is invalid.

    Collects all validation errors into a single exception so users
    can fix everything in one pass rather than playing whack-a-mole.
    """

    def __init__(self, errors: List[str]):
        self.errors = errors
        bullet_list = "\n".join(f"  - {e}" for e in errors)
        super().__init__(f"Configuration errors:\n{bullet_list}")


def validate_config(config: Dict[str, Any], selected_analysts: List[str] = None) -> None:
    """Validate a TradingAgents configuration dictionary.

    Raises ConfigurationError with all problems found, so users can
    fix everything at once rather than one error at a time.

    Args:
        config: The configuration dictionary to validate.
        selected_analysts: Optional list of analyst types to validate.
    """
    errors: List[str] = []

    # --- Required keys ---
    required_keys = [
        "llm_provider",
        "deep_think_llm",
        "quick_think_llm",
        "data_vendors",
    ]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required config key: '{key}'")

    # If required keys are missing, remaining checks can't run reliably
    if errors:
        raise ConfigurationError(errors)

    # --- LLM provider ---
    provider = config["llm_provider"]
    if not isinstance(provider, str):
        errors.append(f"'llm_provider' must be a string, got {type(provider).__name__}")
    else:
        provider_lower = provider.lower()
        if provider_lower not in SUPPORTED_PROVIDERS:
            errors.append(
                f"Unsupported llm_provider '{provider}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
            )
        else:
            # --- API key check ---
            env_var = PROVIDER_API_KEYS.get(provider_lower)
            if env_var and not os.environ.get(env_var):
                errors.append(
                    f"Environment variable '{env_var}' is not set "
                    f"(required for provider '{provider}')"
                )

            # --- Model validation ---
            for key in ("deep_think_llm", "quick_think_llm"):
                model = config[key]
                if not isinstance(model, str) or not model:
                    errors.append(f"'{key}' must be a non-empty string")
                elif not validate_model(provider_lower, model):
                    errors.append(
                        f"Model '{model}' is not valid for provider '{provider}'. "
                        f"Check tradingagents.llm_clients.validators.VALID_MODELS for supported models."
                    )

    # --- Debate rounds ---
    for key in ("max_debate_rounds", "max_risk_discuss_rounds"):
        value = config.get(key)
        if value is not None:
            if not isinstance(value, int) or value < 1:
                errors.append(f"'{key}' must be a positive integer, got {value!r}")

    # --- Recursion limit ---
    recur = config.get("max_recur_limit")
    if recur is not None:
        if not isinstance(recur, int) or recur < 1:
            errors.append(f"'max_recur_limit' must be a positive integer, got {recur!r}")

    # --- Data vendors ---
    vendors = config.get("data_vendors")
    if vendors is not None:
        if not isinstance(vendors, dict):
            errors.append(f"'data_vendors' must be a dict, got {type(vendors).__name__}")
        else:
            for category, vendor in vendors.items():
                if category not in DATA_VENDOR_CATEGORIES:
                    errors.append(
                        f"Unknown data vendor category '{category}'. "
                        f"Valid: {', '.join(sorted(DATA_VENDOR_CATEGORIES))}"
                    )
                if vendor not in VALID_DATA_VENDORS:
                    errors.append(
                        f"Invalid vendor '{vendor}' for category '{category}'. "
                        f"Valid: {', '.join(sorted(VALID_DATA_VENDORS))}"
                    )

    # --- Tool vendors ---
    tool_vendors = config.get("tool_vendors")
    if tool_vendors is not None and not isinstance(tool_vendors, dict):
        errors.append(f"'tool_vendors' must be a dict, got {type(tool_vendors).__name__}")

    # --- Selected analysts ---
    if selected_analysts is not None:
        if not selected_analysts:
            errors.append("selected_analysts must not be empty")
        else:
            for analyst in selected_analysts:
                if analyst not in VALID_ANALYSTS:
                    errors.append(
                        f"Unknown analyst type '{analyst}'. "
                        f"Valid: {', '.join(sorted(VALID_ANALYSTS))}"
                    )

    if errors:
        raise ConfigurationError(errors)
