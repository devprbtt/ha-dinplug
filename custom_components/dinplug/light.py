import asyncio
import logging
from typing import Callable, Dict, Tuple, List, Optional

import voluptuous as vol

from homeassistant.components.light import (
    PLATFORM_SCHEMA,
    LightEntity,
    ColorMode,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_LIGHTS,
    CONF_DEVICE,
    CONF_CHANNEL,
    CONF_DIMMER,
)
from .hub import M4Connection

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23

# ---------- YAML schema ----------

LIGHT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Coerce(int),
        vol.Required(CONF_CHANNEL): vol.Coerce(int),
        vol.Optional(CONF_DIMMER, default=True): cv.boolean,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_LIGHTS): vol.All(cv.ensure_list, [LIGHT_SCHEMA]),
    }
)

# ---------- Platform setup ----------

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up dinplug lights from YAML."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    lights_conf = config[CONF_LIGHTS]

    hass.data.setdefault(DOMAIN, {})
    conn_key = (host, port)

    if conn_key not in hass.data[DOMAIN]:
        conn = M4Connection(hass, host, port)
        hass.data[DOMAIN][conn_key] = conn
        conn.start()
    else:
        conn = hass.data[DOMAIN][conn_key]

    entities = []
    for cfg in lights_conf:
        name = cfg[CONF_NAME]
        dev = cfg[CONF_DEVICE]
        ch = cfg[CONF_CHANNEL]
        dimmer = cfg[CONF_DIMMER]
        entities.append(M4Light(conn, host, port, name, dev, ch, dimmer))

    async_add_entities(entities, update_before_add=True)


# ---------- Light entity ----------


class M4Light(LightEntity):
    _attr_should_poll = False

    def __init__(
        self,
        conn: M4Connection,
        host: str,
        port: int,
        name: str,
        device: int,
        channel: int,
        dimmer: bool,
    ):
        self._conn = conn
        self._host = host
        self._port = port
        self._attr_name = name
        self._device = device
        self._channel = channel
        self._dimmer = dimmer

        self._is_on: bool = False
        self._level: int = 0  # 0..100

        if dimmer:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

        self._attr_unique_id = f"{self._host}-{self._port}-{self._device}-{self._channel}"

        # Register for R:LOAD updates for this device/channel
        self._conn.register_light_listener(
            self._device,
            self._channel,
            self._handle_level_update,
        )

        # Se já tivemos um R:LOAD antes da entidade subir (por REFRESH), usa esse estado
        last = self._conn.get_last_light_level(self._device, self._channel)
        if last is not None:
            self._handle_level_update(last)

    # ---- HA required properties ----

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> Optional[int]:
        if not self._dimmer:
            return None
        # Map 0..100 to 0..255
        return int(self._level * 255 / 100) if self._is_on else 0

    # ---- Callbacks from connection ----

    def _handle_level_update(self, level: int):
        """Callback from M4Connection when R:LOAD is received."""
        # Ignora níveis malucos tipo 65535 do REFRESH
        if level < 0 or level > 100:
            _LOGGER.debug(
                "Ignoring out-of-range level for dev=%s ch=%s: %s",
                self._device,
                self._channel,
                level,
            )
            return

        self._level = level
        self._is_on = level > 0

        _LOGGER.debug(
            "Entity %s updated from R:LOAD: dev=%s ch=%s level=%s",
            self.entity_id,
            self._device,
            self._channel,
            level,
        )
        self.schedule_update_ha_state()

    # ---- Commands from HA ----

    async def async_turn_on(self, **kwargs):
        # For dimmers: use brightness if provided, else full
        if self._dimmer:
            if "brightness" in kwargs:
                b = int(kwargs["brightness"])
                level = max(1, min(100, int(b * 100 / 255)))
            else:
                level = 100
            self._conn.send_load(self._device, self._channel, level)
        else:
            self._conn.send_switch(self._device, self._channel, True)

    async def async_turn_off(self, **kwargs):
        if self._dimmer:
            self._conn.send_load(self._device, self._channel, 0)
        else:
            self._conn.send_switch(self._device, self._channel, False)
