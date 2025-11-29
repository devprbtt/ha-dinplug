import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up via YAML (platforms will handle connection creation)."""
    hass.data.setdefault(DOMAIN, {})
    return True
