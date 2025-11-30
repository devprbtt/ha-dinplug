import logging
import voluptuous as vol
from homeassistant.helpers.discovery import async_load_platform
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                cv.string: vol.All(cv.ensure_list, [dict]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["light", "climate", "cover", "sensor"]


async def async_setup(hass, config):
    """Set up the dinplug integration from YAML."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    # Forward platform setup to the respective platforms
    for p in PLATFORMS:
        if p in config[DOMAIN]:
            hass.async_create_task(
                async_load_platform(hass, p, DOMAIN, config[DOMAIN][p], config)
            )

    return True
