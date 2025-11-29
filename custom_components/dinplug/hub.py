import asyncio
import logging
from typing import Callable, Dict, Tuple, List, Optional

from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, KEEPALIVE_INTERVAL, RECONNECT_DELAY

_LOGGER = logging.getLogger(__name__)


class M4Hub:
    """Hub de conexão com o controlador M4/DINPLUG."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self._hass = hass
        self._host = host
        self._port = port

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected: bool = False
        self._main_task: Optional[asyncio.Task] = None

        # Cache de telemetria
        self._loads: Dict[Tuple[int, int], int] = {}          # (dev,ch) -> level
        self._modules_online: Dict[int, bool] = {}            # dev -> bool

        # Listeners
        self._load_listeners: Dict[Tuple[int, int], List[Callable[[int], None]]] = {}
        self._module_status_listeners: List[Callable[[int, bool], None]] = []
        self._new_load_callbacks: List[Callable[[int, int, int], None]] = []

    # --------- API pública ---------

    def start(self) -> None:
        if self._main_task is None:
            self._main_task = self._hass.loop.create_task(self._run())

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def get_last_load(self, device: int, channel: int) -> Optional[int]:
        return self._loads.get((device, channel))

    def iter_known_loads(self):
        return list(self._loads.items())

    def is_module_online(self, device: int) -> Optional[bool]:
        return self._modules_online.get(device)

    # listeners

    def register_load_listener(
        self, device: int, channel: int, callback_fn: Callable[[int], None]
    ) -> None:
        key = (device, channel)
        self._load_listeners.setdefault(key, []).append(callback_fn)

    def register_module_status_listener(
        self, callback_fn: Callable[[int, bool], None]
    ) -> None:
        self._module_status_listeners.append(callback_fn)

    def register_new_load_callback(
        self, callback_fn: Callable[[int, int, int], None]
    ) -> None:
        self._new_load_callbacks.append(callback_fn)

    # comandos

    def _send_raw(self, cmd: str) -> None:
        if not self._writer:
            raise ConnectionError("Not connected")
        msg = (cmd + "\r\n").encode()
        self._writer.write(msg)

    def send_sta(self) -> None:
        self._send_raw("STA")

    def send_load(self, device: int, channel: int, level: int) -> None:
        level = max(0, min(100, int(level)))
        cmd = f"LOAD {device} {channel} {level}"
        _LOGGER.debug("SEND: %s", cmd)
        self._send_raw(cmd)

    def send_switch(self, device: int, channel: int, on: bool) -> None:
        level = 100 if on else 0
        self.send_load(device, channel, level)

    def send_refresh(self) -> None:
        _LOGGER.debug("SEND: REFRESH")
        self._send_raw("REFRESH")

    # --------- loops internos ---------

    async def _run(self) -> None:
        while True:
            try:
                _LOGGER.info(
                    "Conectando ao M4 DINPLUG em %s:%s", self._host, self._port
                )
                self._reader, self._writer = await asyncio.open_connection(
                    self._host, self._port
                )
                self._connected = True
                _LOGGER.info("M4 DINPLUG conectado (%s:%s)", self._host, self._port)

                # REFRESH inicial pra povoar todos os loads
                try:
                    self.send_refresh()
                except Exception as exc:
                    _LOGGER.debug("Falha ao enviar REFRESH inicial: %s", exc)

                # loop de keepalive STA
                self._hass.loop.create_task(self._keepalive_loop())

                # loop de leitura
                while True:
                    line = await self._reader.readline()
                    if not line:
                        raise ConnectionError("EOF from controller")
                    text = line.decode(errors="ignore").strip()
                    if not text:
                        continue
                    self._handle_line(text)

            except Exception as exc:
                _LOGGER.warning("Erro de conexão M4 DINPLUG: %s", exc)
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

            _LOGGER.info(
                "Tentando reconectar ao M4 DINPLUG (%s:%s) em %s s",
                self._host,
                self._port,
                RECONNECT_DELAY,
            )
            await asyncio.sleep(RECONNECT_DELAY)


    async def _keepalive_loop(self) -> None:
        while self._connected and self._writer is not None:
            try:
                self.send_sta()
            except Exception as exc:
                _LOGGER.debug("Falha ao enviar STA: %s", exc)
            await asyncio.sleep(KEEPALIVE_INTERVAL)

    # --------- parsing ---------

    @callback
    def _handle_line(self, text: str) -> None:
        _LOGGER.debug("RX: %s", text)

        # LOAD feedback: R:LOAD dev ch level
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
                is_new = key not in self._loads
                self._loads[key] = level

                # listeners de load
                if key in self._load_listeners:
                    for cb in self._load_listeners[key]:
                        self._hass.add_job(cb, level)

                # auto-discovery de loads
                if is_new:
                    for cb in self._new_load_callbacks:
                        self._hass.add_job(cb, dev, ch, level)
            return

        # status de módulo: R:MODULE STATUS 101 0
        if text.startswith("R:MODULE STATUS"):
            parts = text.split()
            if len(parts) >= 4:
                try:
                    dev = int(parts[2])
                    status_token = parts[3]
                    # pela sua telemetria: 0 = online, 1 = offline
                    online = status_token == "0"
                except Exception:
                    return

                self._modules_online[dev] = online
                for cb in self._module_status_listeners:
                    self._hass.add_job(cb, dev, online)
            return

        # offline count: R:MODULES OFFLINE: 2/11
        if text.startswith("R:MODULES OFFLINE:"):
            payload = text.split("R:MODULES OFFLINE:")[1].strip()
            self._hass.bus.async_fire(
                "m4_dinplug_offline_count",
                {"raw": text, "payload": payload},
            )
            return

        # keypad: R:BTN PRESS 108 29 etc (já deixamos pronto pra automações)
        if text.startswith("R:BTN "):
            parts = text.split()
            if len(parts) >= 4:
                action = parts[1]
                try:
                    device = int(parts[2])
                    key = int(parts[3])
                except ValueError:
                    return
                self._hass.bus.async_fire(
                    "m4_dinplug_keypad",
                    {
                        "action": action,
                        "device": device,
                        "key": key,
                        "raw": text,
                    },
                )
            return

        # REFRESH mensagens
        if text.startswith("R:REFRESH"):
            self._hass.bus.async_fire("m4_dinplug_refresh", {"raw": text})


async def get_hub(hass: HomeAssistant, host: str, port: int) -> M4Hub:
    """Retorna (ou cria) um hub para (host, port) compartilhado entre plataformas."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("hubs", {})
    hubs: Dict[Tuple[str, int], M4Hub] = hass.data[DOMAIN]["hubs"]

    key = (host, port)
    if key in hubs:
        return hubs[key]

    hub = M4Hub(hass, host, port)
    hubs[key] = hub
    hub.start()
    return hub
