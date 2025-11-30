import asyncio
import logging
from typing import Callable, Dict, Tuple, List, Optional, Any

_LOGGER = logging.getLogger(__name__)

KEEPALIVE_INTERVAL = 10  # seconds
RECONNECT_DELAY = 5      # seconds

# Listener types
ListenLight = Callable[[int], None]
ListenShade = Callable[[int], None]
ListenButton = Callable[[str], None]
ListenHvac = Callable[[Dict[str, Any]], None]


class M4Connection:
    """Single TCP/Telnet connection to the M4/DINPLUG controller."""

    def __init__(self, hass, host: str, port: int):
        self._hass = hass
        self._host = host
        self._port = port
        self._writer: Optional[asyncio.StreamWriter] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._task: Optional[asyncio.Task] = None
        self._connected = False

        # Listeners
        self._light_listeners: Dict[Tuple[int, int], List[ListenLight]] = {}
        self._shade_listeners: Dict[Tuple[int, int], List[ListenShade]] = {}
        self._button_listeners: Dict[Tuple[int, int], List[ListenButton]] = {}
        self._hvac_listeners: Dict[int, List[ListenHvac]] = {}

        # Caches for last known states
        self._last_light_levels: Dict[Tuple[int, int], int] = {}
        self._last_shade_levels: Dict[Tuple[int, int], int] = {}
        self._last_button_states: Dict[Tuple[int, int], str] = {}
        self._last_hvac_states: Dict[int, Dict[str, Any]] = {}

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

                try:
                    self.send_raw("REFRESH")
                except Exception as e:
                    _LOGGER.debug("Failed to send REFRESH: %s", e)

                self._hass.loop.create_task(self._keepalive_loop())

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
        _LOGGER.debug("TX: %s", cmd)
        self._writer.write(msg)

    # ---- Light methods ----

    def send_load(self, device: int, channel: int, level: int, fade: Optional[int] = None):
        level = max(0, min(100, int(level)))
        cmd = f"LOAD {device} {channel} {level}" + (f" {fade:04d}" if fade else "")
        self.send_raw(cmd)

    def register_light_listener(self, device: int, channel: int, callback: ListenLight):
        self._light_listeners.setdefault((device, channel), []).append(callback)

    def get_last_light_level(self, device: int, channel: int) -> Optional[int]:
        return self._last_light_levels.get((device, channel))

    # ---- Shade methods ----

    def send_shade(self, device: int, channel: int, command: str):
        self.send_raw(f"SHADE {device} {channel} {command}")

    def register_shade_listener(self, device: int, channel: int, callback: ListenShade):
        self._shade_listeners.setdefault((device, channel), []).append(callback)

    def get_last_shade_level(self, device: int, channel: int) -> Optional[int]:
        return self._last_shade_levels.get((device, channel))

    # ---- Button sensor methods ----

    def register_button_listener(self, device: int, channel: int, callback: ListenButton):
        self._button_listeners.setdefault((device, channel), []).append(callback)

    def get_last_button_state(self, device: int, channel: int) -> Optional[str]:
        return self._last_button_states.get((device, channel))

    # ---- HVAC methods ----

    def send_hvac(self, device: int, command: str, value: Optional[Any] = None):
        cmd = f"HVAC {device} {command}" + (f" {value}" if value is not None else "")
        self.send_raw(cmd)

    def register_hvac_listener(self, device: int, callback: ListenHvac):
        self._hvac_listeners.setdefault(device, []).append(callback)

    def get_last_hvac_state(self, device: int) -> Optional[Dict[str, Any]]:
        return self._last_hvac_states.get(device)

    # ---- Central line handler ----

    def _handle_line(self, text: str):
        """Parse incoming lines and dispatch to correct handlers."""
        _LOGGER.debug("RX: %s", text)
        parts = text.split()
        if not parts:
            return

        # R:LOAD <dev> <ch> <level>
        if parts[0] == "R:LOAD" and len(parts) >= 4:
            self._handle_load(parts)
        # R:SHADE <dev> <ch> <level>
        elif parts[0] == "R:SHADE" and len(parts) >= 4:
            self._handle_shade(parts)
        # R:BTN <state> <dev> <ch>
        elif parts[0] == "R:BTN" and len(parts) >= 4:
            self._handle_btn(parts)
        # R:HVAC ...
        elif parts[0] == "R:HVAC" and len(parts) >= 3:
            self._handle_hvac(parts)

    def _handle_load(self, parts: List[str]):
        try:
            dev, ch, level = map(int, parts[1:4])
        except (ValueError, IndexError):
            return

        key = (dev, ch)
        self._last_light_levels[key] = level
        if key in self._light_listeners:
            for cb in self._light_listeners[key]:
                self._hass.add_job(cb, level)

    def _handle_shade(self, parts: List[str]):
        try:
            dev, ch, level = map(int, parts[1:4])
        except (ValueError, IndexError):
            return

        key = (dev, ch)
        self._last_shade_levels[key] = level
        if key in self._shade_listeners:
            for cb in self._shade_listeners[key]:
                self._hass.add_job(cb, level)

    def _handle_btn(self, parts: List[str]):
        try:
            state = parts[1]
            dev, ch = map(int, parts[2:4])
        except (ValueError, IndexError):
            return

        key = (dev, ch)
        self._last_button_states[key] = state
        if key in self._button_listeners:
            for cb in self._button_listeners[key]:
                self._hass.add_job(cb, state)

    def _handle_hvac(self, parts: List[str]):
        try:
            # R:HVAC <MODE|FANHIGH|...> <dev>
            if len(parts) == 3:
                prop, dev_str = parts[1], parts[2]
                dev = int(dev_str)
                state = self._last_hvac_states.setdefault(dev, {})

                if prop in {"COOL", "HEAT", "FAN", "OFF"}:
                    state["mode"] = prop.lower()
                elif prop.startswith("FAN"):
                    state["fan_mode"] = prop[3:].lower()

            # R:HVAC <CURRENTTEMP|SETPOINT> <dev> <temp>
            elif len(parts) == 4:
                prop, dev_str, val_str = parts[1], parts[2], parts[3]
                dev = int(dev_str)
                state = self._last_hvac_states.setdefault(dev, {})

                if prop == "CURRENTTEMP":
                    state["current_temperature"] = float(val_str)
                elif prop == "SETPOINT":
                    state["temperature"] = float(val_str)

            else:
                return  # Unrecognized HVAC format

            # Dispatch update
            if dev in self._hvac_listeners:
                for cb in self._hvac_listeners[dev]:
                    self._hass.add_job(cb, state.copy())

        except (ValueError, IndexError):
            pass
