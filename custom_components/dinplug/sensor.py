import logging
from typing import Optional

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_DEVICE, CONF_CHANNEL
from .hub import M4Connection

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23

CONF_SENSORS = "buttons"

BUTTON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Coerce(int),
        vol.Required(CONF_CHANNEL): vol.Coerce(int),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [BUTTON_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up dinplug button sensors from YAML."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    sensors_conf = config[CONF_SENSORS]

    conn = hass.data[DOMAIN].get((host, port))
    if not conn:
        conn = M4Connection(hass, host, port)
        hass.data[DOMAIN][(host, port)] = conn
        conn.start()

    entities = [
        M4ButtonSensor(
            conn,
            host,
            port,
            cfg[CONF_NAME],
            cfg[CONF_DEVICE],
            cfg[CONF_CHANNEL],
        )
        for cfg in sensors_conf
    ]
    async_add_entities(entities, update_before_add=True)


class M4ButtonSensor(SensorEntity):
    _attr_should_poll = False
    _attr_icon = "mdi:radiobox-marked"

    def __init__(
        self,
        conn: M4Connection,
        host: str,
        port: int,
        name: str,
        device: int,
        channel: int,
    ):
        self._conn = conn
        self._host = host
        self._port = port
        self._attr_name = name
        self._device = device
        self._channel = channel
        self._attr_unique_id = f"{host}-{port}-{device}-{channel}-button"

        self._attr_native_value = None

        self._conn.register_button_listener(
            self._device, self._channel, self._handle_update
        )

        last_state = self._conn.get_last_button_state(self._device, self._channel)
        if last_state:
            self._handle_update(last_state)

    def _handle_update(self, state: str):
        self._attr_native_value = state.lower()
        self.schedule_update_ha_state()
