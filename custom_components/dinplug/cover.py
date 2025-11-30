import logging
from typing import Optional

import voluptuous as vol

from homeassistant.components.cover import (
    PLATFORM_SCHEMA,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_DEVICE, CONF_CHANNEL
from .hub import M4Connection

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23

CONF_COVERS = "shades"

COVER_SCHEMA = vol.Schema(
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
        vol.Required(CONF_COVERS): vol.All(cv.ensure_list, [COVER_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up dinplug covers from YAML."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    covers_conf = config[CONF_COVERS]

    conn = hass.data[DOMAIN].get((host, port))
    if not conn:
        conn = M4Connection(hass, host, port)
        hass.data[DOMAIN][(host, port)] = conn
        conn.start()

    entities = [
        M4Cover(
            conn,
            host,
            port,
            cfg[CONF_NAME],
            cfg[CONF_DEVICE],
            cfg[CONF_CHANNEL],
        )
        for cfg in covers_conf
    ]
    async_add_entities(entities, update_before_add=True)


class M4Cover(CoverEntity):
    _attr_should_poll = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

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
        self._attr_unique_id = f"{host}-{port}-{device}-{channel}-cover"

        self._position: Optional[int] = None

        self._conn.register_shade_listener(
            self._device, self._channel, self._handle_update
        )

        last_level = self._conn.get_last_shade_level(self._device, self._channel)
        if last_level is not None:
            self._handle_update(last_level)

    def _handle_update(self, level: int):
        self._position = level
        self.schedule_update_ha_state()

    @property
    def current_cover_position(self) -> Optional[int]:
        return self._position

    @property
    def is_closed(self) -> Optional[bool]:
        if self._position is None:
            return None
        return self._position == 0

    async def async_open_cover(self, **kwargs):
        self._conn.send_shade(self._device, self._channel, "UP")

    async def async_close_cover(self, **kwargs):
        self._conn.send_shade(self._device, self._channel, "DOWN")

    async def async_stop_cover(self, **kwargs):
        self._conn.send_shade(self._device, self._channel, "STOP")

    async def async_set_cover_position(self, **kwargs):
        if "position" in kwargs:
            pos = kwargs["position"]
            self._conn.send_shade(self._device, self._channel, f"GOTO {pos}")
