import logging
from typing import Optional

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    UnitOfTemperature,
)
import homeassistant.helpers.config_validation as cv

from .connection import DEFAULT_PORT, M4Connection, ThermostatState, get_connection
from .const import CONF_DEVICE, CONF_HVACS, CONF_MAX_TEMP, CONF_MIN_TEMP

_LOGGER = logging.getLogger(__name__)

THERMOSTAT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Coerce(int),
        vol.Optional(CONF_MIN_TEMP, default=6): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=33): vol.Coerce(float),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_HVACS): vol.All(cv.ensure_list, [THERMOSTAT_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up dinplug HVAC controllers from YAML."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    hvac_conf = config[CONF_HVACS]

    conn = get_connection(hass, host, port)

    entities = []
    for cfg in hvac_conf:
        name = cfg[CONF_NAME]
        dev = cfg[CONF_DEVICE]
        min_temp = cfg[CONF_MIN_TEMP]
        max_temp = cfg[CONF_MAX_TEMP]
        entities.append(M4Climate(conn, host, port, name, dev, min_temp, max_temp))

    async_add_entities(entities, update_before_add=True)


class M4Climate(ClimateEntity):
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_hvac_modes = [
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.FAN_ONLY,
        HVACMode.OFF,
    ]
    _attr_fan_modes = ["high", "medium", "low", "auto"]

    def __init__(
        self,
        conn: M4Connection,
        host: str,
        port: int,
        name: str,
        device: int,
        min_temp: float,
        max_temp: float,
    ):
        self._conn = conn
        self._host = host
        self._port = port
        self._attr_name = name
        self._device = device
        self._min_temp = min_temp
        self._max_temp = max_temp

        self._attr_unique_id = f"{self._host}-{self._port}-hvac-{self._device}"
        self._hvac_mode: HVACMode = HVACMode.OFF
        self._fan_mode: Optional[str] = None
        self._target_temp: Optional[float] = None
        self._current_temp: Optional[float] = None

        self._conn.register_thermostat_listener(
            self._device, self._handle_state_update
        )
        last = self._conn.get_last_thermostat_state(self._device)
        if last is not None:
            self._handle_state_update(last)

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @property
    def target_temperature(self) -> Optional[float]:
        return self._target_temp

    @property
    def current_temperature(self) -> Optional[float]:
        return self._current_temp

    @property
    def fan_mode(self) -> Optional[str]:
        return self._fan_mode

    @property
    def min_temp(self) -> float:
        return self._min_temp

    @property
    def max_temp(self) -> float:
        return self._max_temp

    @property
    def hvac_action(self) -> HVACAction:
        if self._hvac_mode == HVACMode.HEAT:
            if (
                self._current_temp is not None
                and self._target_temp is not None
                and self._current_temp < self._target_temp
            ):
                return HVACAction.HEATING
            return HVACAction.IDLE
        if self._hvac_mode == HVACMode.COOL:
            if (
                self._current_temp is not None
                and self._target_temp is not None
                and self._current_temp > self._target_temp
            ):
                return HVACAction.COOLING
            return HVACAction.IDLE
        if self._hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.IDLE

    # --- Callbacks from the connection ---

    def _handle_state_update(self, state: ThermostatState) -> None:
        mode_map = {
            "HEAT": HVACMode.HEAT,
            "COOL": HVACMode.COOL,
            "FAN": HVACMode.FAN_ONLY,
            "OFF": HVACMode.OFF,
        }
        fan_map = {
            "FANHIGH": "high",
            "FANMID": "medium",
            "FANLOW": "low",
            "FANAUTO": "auto",
        }

        if state.target_temp is not None:
            self._target_temp = state.target_temp
        if state.current_temp is not None:
            self._current_temp = state.current_temp
        elif state.external_temp is not None and self._current_temp is None:
            self._current_temp = state.external_temp
        if state.hvac_mode is not None and state.hvac_mode in mode_map:
            self._hvac_mode = mode_map[state.hvac_mode]
        if state.fan_mode is not None and state.fan_mode in fan_map:
            self._fan_mode = fan_map[state.fan_mode]

        self.schedule_update_ha_state()

    # --- Commands from HA ---

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE not in kwargs:
            return
        temp = float(kwargs[ATTR_TEMPERATURE])
        clamped = max(self._min_temp, min(self._max_temp, temp))
        self._conn.send_hvac_setpoint(self._device, clamped)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.HEAT:
            self._conn.send_hvac_mode(self._device, "HEAT")
        elif hvac_mode == HVACMode.COOL:
            self._conn.send_hvac_mode(self._device, "COOL")
        elif hvac_mode == HVACMode.OFF:
            self._conn.send_hvac_mode(self._device, "OFF")
        elif hvac_mode == HVACMode.FAN_ONLY:
            # Best effort: put system in OFF and leave fan in current/auto mode
            self._conn.send_hvac_mode(self._device, "OFF")
            if self._fan_mode is None:
                self._conn.send_hvac_fan_mode(self._device, "FANAUTO")
        else:
            return

        self._hvac_mode = hvac_mode
        self.schedule_update_ha_state()

    async def async_set_fan_mode(self, fan_mode: str):
        fan_mode = fan_mode.lower()
        fan_map = {
            "high": "FANHIGH",
            "medium": "FANMID",
            "low": "FANLOW",
            "auto": "FANAUTO",
        }
        if fan_mode not in fan_map:
            return
        self._conn.send_hvac_fan_mode(self._device, fan_map[fan_mode])
        self._fan_mode = fan_mode
        self.schedule_update_ha_state()
