import logging
from typing import Optional

import voluptuous as vol

from homeassistant.components.cover import (
    PLATFORM_SCHEMA,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .connection import DEFAULT_PORT, M4Connection, get_connection
from .const import CONF_CHANNEL, CONF_COVERS, CONF_DEVICE

_LOGGER = logging.getLogger(__name__)

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
    """Set up dinplug covers (shades) from YAML."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    covers_conf = config[CONF_COVERS]

    conn = get_connection(hass, host, port)

    entities = []
    for cfg in covers_conf:
        name = cfg[CONF_NAME]
        dev = cfg[CONF_DEVICE]
        ch = cfg[CONF_CHANNEL]
        entities.append(M4Cover(conn, host, port, name, dev, ch))

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

        self._position: Optional[int] = None
        self._attr_unique_id = f"{self._host}-{self._port}-shade-{self._device}-{self._channel}"

        self._conn.register_shade_listener(
            self._device, self._channel, self._handle_shade_update
        )

        last = self._conn.get_last_shade_level(self._device, self._channel)
        if last is not None:
            self._handle_shade_update(last)

    @property
    def is_closed(self) -> Optional[bool]:
        if self._position is None:
            return None
        return self._position == 0

    @property
    def current_cover_position(self) -> Optional[int]:
        return self._position

    def _handle_shade_update(self, level: int) -> None:
        if level < 0 or level > 100:
            _LOGGER.debug(
                "Ignoring out-of-range shade update for dev=%s ch=%s: %s",
                self._device,
                self._channel,
                level,
            )
            return

        self._position = level
        self.schedule_update_ha_state()

    async def async_open_cover(self, **kwargs):
        self._conn.send_shade_up(self._device, self._channel)

    async def async_close_cover(self, **kwargs):
        self._conn.send_shade_down(self._device, self._channel)

    async def async_stop_cover(self, **kwargs):
        self._conn.send_shade_stop(self._device, self._channel)

    async def async_set_cover_position(self, **kwargs):
        if "position" not in kwargs:
            return
        level = max(0, min(100, int(kwargs["position"])))
        self._conn.send_shade_set(self._device, self._channel, level)
