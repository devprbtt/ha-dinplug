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

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23
KEEPALIVE_INTERVAL = 10  # seconds
RECONNECT_DELAY = 5      # seconds

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

# ---------- Connection manager ----------


class M4Connection:
    """Single TCP/Telnet connection to the M4/DINPLUG controller."""

    def __init__(self, hass, host: str, port: int):
        self._hass = hass
        self._host = host
        self._port = port
        self._writer: Optional[asyncio.StreamWriter] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._task: Optional[asyncio.Task] = None
        self._listeners: Dict[Tuple[int, int], List[Callable[[int], None]]] = {}
        self._connected = False

    def start(self):
        """Start background connection loop."""
        if self._task is None:
            self._task = self._hass.loop.create_task(self._run_loop())

    async def _run_loop(self):
        """Connect, read lines, reconnect if needed."""
        while True:
            try:
                _LOGGER.info("Connecting to M4 DINPLUG at %s:%s", self._host, self._port)
                self._reader, self._writer = await asyncio.open_connection(
                    self._host, self._port
                )
                self._connected = True
                _LOGGER.info("M4 DINPLUG connected")

                # Kick off keepalive
                self._hass.loop.create_task(self._keepalive_loop())

                # Read loop
                while True:
                    line = await self._reader.readline()
                    if not line:
                        raise ConnectionError("EOF from controller")
                    text = line.decode(errors="ignore").strip()
                    if not text:
                        continue
                    self._handle_line(text)

            except Exception as e:
                _LOGGER.warning("M4 DINPLUG connection error: %s", e)
            finally:
                self._connected = False
                if self._writer:
                    try:
                        self._writer.close()
                        await self._writer.wait_closed()
                    except Exception:
                        pass
                self._writer = None
                self._reader = None

            _LOGGER.info("Reconnecting to M4 DINPLUG in %s seconds", RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)

    async def _keepalive_loop(self):
        """Send STA keepalive while connected."""
        while self._connected and self._writer is not None:
            try:
                self.send_raw("STA")
            except Exception as e:
                _LOGGER.debug("Failed to send STA: %s", e)
            await asyncio.sleep(KEEPALIVE_INTERVAL)

    def send_raw(self, cmd: str):
        """Send a raw command with CRLF."""
        if not self._writer:
            raise ConnectionError("Not connected to controller")
        msg = (cmd + "\r\n").encode()
        self._writer.write(msg)

    # ---- Protocol-specific helpers ----

    def send_load(self, device: int, channel: int, level: int, fade: Optional[int] = None):
        """Send LOAD command.

        If fade is None -> LOAD dev ch level
        Else -> LOAD dev ch level fade
        """
        level = max(0, min(100, int(level)))
        if fade is None:
            cmd = f"LOAD {device} {channel} {level}"
        else:
            cmd = f"LOAD {device} {channel} {level:03d} {fade:04d}"
        _LOGGER.debug("SEND: %s", cmd)
        self.send_raw(cmd)

    def send_switch(self, device: int, channel: int, on: bool):
        """Switch-style LOAD."""
        level = 100 if on else 0
        cmd = f"LOAD {device} {channel} {level}"
        _LOGGER.debug("SEND: %s", cmd)
        self.send_raw(cmd)

    def register_load_listener(
        self, device: int, channel: int, callback: Callable[[int], None]
    ):
        key = (device, channel)
        self._listeners.setdefault(key, []).append(callback)

    def _handle_line(self, text: str):
        """Parse incoming lines and dispatch R:LOAD."""
        _LOGGER.debug("RX: %s", text)

        # Example: R:LOAD 104 3 50
        if text.startswith("R:LOAD "):
            parts = text.split()
            if len(parts) >= 4:
                try:
                    dev = int(parts[1])
                    ch = int(parts[2])
                    level = int(parts[3])
                except ValueError:
                    return

                key = (dev, ch)
                if key in self._listeners:
                    for cb in self._listeners[key]:
                        # Run callbacks in HA loop safely
                        self._hass.add_job(cb, level)

        # You can extend later: R:SCN, R:HVAC, etc.


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
        self._conn.register_load_listener(self._device, self._channel, self._handle_level_update)

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
        # Ignore weird levels like 65535 from REFRESH
        if level < 0 or level > 100:
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
