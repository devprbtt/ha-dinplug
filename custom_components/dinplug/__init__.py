import logging
import voluptuous as vol
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.const import CONF_HOST
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["light", "climate", "cover", "sensor"]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [dict])
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the dinplug integration from YAML."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    for host_config in config[DOMAIN]:
        host = host_config[CONF_HOST]
        _LOGGER.debug("Setting up dinplug host: %s", host)

        for p in PLATFORMS:
            if p in host_config:
                hass.async_create_task(
                    async_load_platform(hass, p, DOMAIN, host_config, config)
                )

    return True
