import logging
from typing import Optional

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .connection import DEFAULT_PORT, M4Connection, get_connection
from .const import CONF_BUTTONS, CONF_BUTTON_ID, CONF_DEVICE

_LOGGER = logging.getLogger(__name__)

BUTTON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Coerce(int),
        vol.Required(CONF_BUTTON_ID): vol.Coerce(int),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_BUTTONS): vol.All(cv.ensure_list, [BUTTON_SCHEMA]),
    }
)

BUTTON_STATES = ["PRESSED", "RELEASED", "HELD", "DOUBLE"]
BUTTON_MAP = {"PRESS": "PRESSED", "RELEASE": "RELEASED", "HOLD": "HELD"}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Expose keypad/button states as sensors."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    buttons_conf = config[CONF_BUTTONS]

    conn = get_connection(hass, host, port)

    entities = []
    for cfg in buttons_conf:
        name = cfg[CONF_NAME]
        dev = cfg[CONF_DEVICE]
        button_id = cfg[CONF_BUTTON_ID]
        entities.append(M4ButtonSensor(conn, host, port, name, dev, button_id))

    async_add_entities(entities, update_before_add=True)


class M4ButtonSensor(SensorEntity):
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = BUTTON_STATES

    def __init__(
        self,
        conn: M4Connection,
        host: str,
        port: int,
        name: str,
        device: int,
        button: int,
    ):
        self._conn = conn
        self._host = host
        self._port = port
        self._attr_name = name
        self._device = device
        self._button = button
        self._attr_unique_id = (
            f"{self._host}-{self._port}-button-{self._device}-{self._button}"
        )
        self._state: Optional[str] = None

        self._conn.register_button_listener(
            self._device, self._button, self._handle_button_state
        )

        last = self._conn.get_last_button_state(self._device, self._button)
        if last is not None:
            self._handle_button_state(last)

    @property
    def native_value(self) -> Optional[str]:
        return self._state

    def _handle_button_state(self, state: str) -> None:
        normalized = state.upper()
        display = BUTTON_MAP.get(normalized, normalized)
        if display not in BUTTON_STATES:
            _LOGGER.debug(
                "Ignoring unknown button state for dev=%s button=%s: %s",
                self._device,
                self._button,
                state,
            )
            return

        self._state = display
        self.schedule_update_ha_state()
