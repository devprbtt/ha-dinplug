import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23
KEEPALIVE_INTERVAL = 10
RECONNECT_DELAY = 5


@dataclass
class ThermostatState:
    """Simple container for thermostat values."""

    target_temp: Optional[float] = None
    current_temp: Optional[float] = None
    external_temp: Optional[float] = None
    hvac_mode: Optional[str] = None
    fan_mode: Optional[str] = None


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

        self._load_listeners: Dict[Tuple[int, int], List[Callable[[int], None]]] = {}
        self._shade_listeners: Dict[Tuple[int, int], List[Callable[[int], None]]] = {}
        self._button_listeners: Dict[Tuple[int, int], List[Callable[[str], None]]] = {}
        self._thermostat_listeners: Dict[int, List[Callable[[ThermostatState], None]]] = {}

        self._last_levels: Dict[Tuple[int, int], int] = {}
        self._last_shade_levels: Dict[Tuple[int, int], int] = {}
        self._last_button_states: Dict[Tuple[int, int], str] = {}
        self._thermostats: Dict[int, ThermostatState] = {}

    def start(self) -> None:
        """Start background connection loop."""
        if self._task is None:
            self._task = self._hass.loop.create_task(self._run_loop())

    # Connection lifecycle -------------------------------------------------

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
                except Exception as err:
                    _LOGGER.debug("Failed to send REFRESH: %s", err)

                self._hass.loop.create_task(self._keepalive_loop())

                while True:
                    line = await self._reader.readline()
                    if not line:
                        raise ConnectionError("EOF from controller")
                    text = line.decode(errors="ignore").strip()
                    if not text:
                        continue
                    self._handle_line(text)

            except Exception as err:
                _LOGGER.warning("M4 DINPLUG connection error: %s", err)
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
            except Exception as err:
                _LOGGER.debug("Failed to send STA: %s", err)
            await asyncio.sleep(KEEPALIVE_INTERVAL)

    # Sending commands ----------------------------------------------------

    def send_raw(self, cmd: str) -> None:
        """Send a raw command with CRLF."""
        if not self._writer:
            raise ConnectionError("Not connected to controller")
        msg = (cmd + "\r\n").encode()
        _LOGGER.debug("TX: %s", cmd)
        self._writer.write(msg)

    def send_load(self, device: int, channel: int, level: int, fade: Optional[int] = None):
        """Send LOAD command."""
        level = max(0, min(100, int(level)))
        if fade is None:
            cmd = f"LOAD {device} {channel} {level}"
        else:
            cmd = f"LOAD {device} {channel} {level:03d} {fade:04d}"
        self.send_raw(cmd)

    def send_switch(self, device: int, channel: int, on: bool):
        """Switch-style LOAD."""
        level = 100 if on else 0
        cmd = f"LOAD {device} {channel} {level}"
        self.send_raw(cmd)

    def send_shade_up(self, device: int, channel: int):
        self.send_raw(f"SHADE UP {device} {channel}")

    def send_shade_down(self, device: int, channel: int):
        self.send_raw(f"SHADE DOWN {device} {channel}")

    def send_shade_stop(self, device: int, channel: int):
        self.send_raw(f"SHADE STOP {device} {channel}")

    def send_shade_set(self, device: int, channel: int, level: int):
        level = max(0, min(100, int(level)))
        self.send_raw(f"SHADE SET {device} {channel} {level}")

    def send_hvac_setpoint(self, device: int, temperature: float):
        value = max(0, min(99, int(round(temperature))))
        self.send_raw(f"HVAC SETPOINT {device} {value:02d}")

    def send_hvac_mode(self, device: int, mode: str):
        mode = mode.upper()
        if mode not in {"HEAT", "COOL", "OFF"}:
            raise ValueError(f"Unsupported HVAC mode {mode}")
        self.send_raw(f"HVAC {mode} {device}")

    def send_hvac_fan_mode(self, device: int, fan_mode: str):
        mode = fan_mode.upper()
        if mode not in {"FANHIGH", "FANMID", "FANLOW", "FANAUTO"}:
            raise ValueError(f"Unsupported fan mode {fan_mode}")
        self.send_raw(f"HVAC {mode} {device}")

    # Listener registration -----------------------------------------------

    def register_load_listener(
        self, device: int, channel: int, callback: Callable[[int], None]
    ):
        self._load_listeners.setdefault((device, channel), []).append(callback)

    def register_shade_listener(
        self, device: int, channel: int, callback: Callable[[int], None]
    ):
        self._shade_listeners.setdefault((device, channel), []).append(callback)

    def register_button_listener(
        self, device: int, button: int, callback: Callable[[str], None]
    ):
        self._button_listeners.setdefault((device, button), []).append(callback)

    def register_thermostat_listener(
        self, device: int, callback: Callable[[ThermostatState], None]
    ):
        self._thermostat_listeners.setdefault(device, []).append(callback)

    # Cached states -------------------------------------------------------

    def get_last_level(self, device: int, channel: int) -> Optional[int]:
        return self._last_levels.get((device, channel))

    def get_last_shade_level(self, device: int, channel: int) -> Optional[int]:
        return self._last_shade_levels.get((device, channel))

    def get_last_button_state(self, device: int, button: int) -> Optional[str]:
        return self._last_button_states.get((device, button))

    def get_last_thermostat_state(self, device: int) -> Optional[ThermostatState]:
        return self._thermostats.get(device)

    # Incoming parsing ----------------------------------------------------

    def _handle_line(self, text: str) -> None:
        """Parse incoming lines and dispatch."""
        _LOGGER.debug("RX: %s", text)

        if text.startswith("R:LOAD "):
            self._parse_load(text)
        elif text.startswith("R:SHADE "):
            self._parse_shade(text)
        elif text.startswith("R:BTN "):
            self._parse_button(text)
        elif text.startswith("R:HVAC"):
            self._parse_hvac(text)

    def _parse_load(self, text: str) -> None:
        parts = text.split()
        if len(parts) < 4:
            return
        try:
            dev = int(parts[1])
            ch = int(parts[2])
            level = int(parts[3])
        except ValueError:
            return

        if level < 0 or level > 100:
            _LOGGER.debug(
                "Ignoring out-of-range level for dev=%s ch=%s: %s", dev, ch, level
            )
            return

        key = (dev, ch)
        self._last_levels[key] = level

        for cb in self._load_listeners.get(key, []):
            self._hass.add_job(cb, level)

    def _parse_shade(self, text: str) -> None:
        parts = text.split()
        if len(parts) < 4:
            return
        try:
            dev = int(parts[1])
            ch = int(parts[2])
            level = int(parts[3])
        except ValueError:
            return

        if level < 0 or level > 100:
            _LOGGER.debug(
                "Ignoring out-of-range shade level for dev=%s ch=%s: %s", dev, ch, level
            )
            return

        key = (dev, ch)
        self._last_shade_levels[key] = level
        for cb in self._shade_listeners.get(key, []):
            self._hass.add_job(cb, level)

    def _parse_button(self, text: str) -> None:
        # Example: R:BTN PRESS 111 2
        parts = text.split()
        if len(parts) < 4:
            return
        state = parts[1].upper()
        try:
            dev = int(parts[2])
            btn = int(parts[3])
        except ValueError:
            return

        key = (dev, btn)
        self._last_button_states[key] = state
        for cb in self._button_listeners.get(key, []):
            self._hass.add_job(cb, state)

        self._hass.bus.async_fire(
            f"{DOMAIN}_button_event",
            {"device": dev, "button": btn, "state": state},
        )

    def _parse_hvac(self, text: str) -> None:
        parts = text.split()
        if len(parts) < 3:
            return
        keyword = parts[1].upper()

        # Messages with temperature
        if keyword in {"SETPOINT", "COOLPOINT", "HEATPOINT"} and len(parts) >= 4:
            self._update_thermostat_temp(parts[2], parts[3], target=True)
            return
        if keyword in {"CURRENTTEMP", "EXTERNALTEMP"} and len(parts) >= 4:
            self._update_thermostat_temp(parts[2], parts[3], target=False, external=keyword == "EXTERNALTEMP")
            return

        # HVAC mode / fan mode
        if keyword in {"COOL", "HEAT", "FAN", "OFF"} and len(parts) >= 3:
            try:
                dev = int(parts[2])
            except ValueError:
                return
            state = self._thermostats.setdefault(dev, ThermostatState())
            state.hvac_mode = keyword
            self._notify_thermostat(dev)
            return

        if keyword in {"FANHIGH", "FANMID", "FANLOW", "FANAUTO"} and len(parts) >= 3:
            try:
                dev = int(parts[2])
            except ValueError:
                return
            state = self._thermostats.setdefault(dev, ThermostatState())
            state.fan_mode = keyword
            self._notify_thermostat(dev)

    def _update_thermostat_temp(
        self, dev_raw: str, value_raw: str, target: bool, external: bool = False
    ) -> None:
        try:
            dev = int(dev_raw)
            value = float(value_raw)
        except ValueError:
            return

        state = self._thermostats.setdefault(dev, ThermostatState())
        if target:
            state.target_temp = value
        else:
            if external:
                state.external_temp = value
            else:
                state.current_temp = value
        self._notify_thermostat(dev)

    def _notify_thermostat(self, device: int) -> None:
        state = self._thermostats.get(device)
        if state is None:
            return
        for cb in self._thermostat_listeners.get(device, []):
            self._hass.add_job(cb, state)


def get_connection(hass, host: str, port: int) -> M4Connection:
    """Return a shared connection per host/port."""
    hass.data.setdefault(DOMAIN, {})
    key = (host, port)
    if key not in hass.data[DOMAIN]:
        conn = M4Connection(hass, host, port)
        hass.data[DOMAIN][key] = conn
        conn.start()
    return hass.data[DOMAIN][key]
