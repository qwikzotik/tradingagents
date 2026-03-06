import tradingagents.default_config as default_config
from typing import Dict, Optional


class _ConfigHolder:
    """Encapsulates configuration state to avoid bare global mutation."""

    def __init__(self):
        self._config: Optional[Dict] = None

    def initialize(self):
        """Initialize the configuration with default values."""
        if self._config is None:
            self._config = default_config.DEFAULT_CONFIG.copy()

    def set(self, config: Dict):
        """Update the configuration with custom values."""
        if self._config is None:
            self._config = default_config.DEFAULT_CONFIG.copy()
        self._config.update(config)

    def get(self) -> Dict:
        """Get a copy of the current configuration."""
        if self._config is None:
            self.initialize()
        return self._config.copy()


_holder = _ConfigHolder()


def initialize_config():
    """Initialize the configuration with default values."""
    _holder.initialize()


def set_config(config: Dict):
    """Update the configuration with custom values."""
    _holder.set(config)


def get_config() -> Dict:
    """Get the current configuration."""
    return _holder.get()


# Initialize with default config
initialize_config()
