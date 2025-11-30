import logging
from typing import Any, Dict, Optional, List

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    HVACAction,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, UnitOfTemperature
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_DEVICE
from .hub import M4Connection

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23

CONF_CLIMATES = "hvacs"

CLIMATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Coerce(int),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_CLIMATES): vol.All(cv.ensure_list, [CLIMATE_SCHEMA]),
    }
)

HA_TO_M4_HVAC_MODE = {
    HVACMode.OFF: "OFF",
    HVACMode.COOL: "COOL",
    HVACMode.HEAT: "HEAT",
    HVACMode.FAN_ONLY: "FAN",
}
M4_TO_HA_HVAC_MODE = {v: k for k, v in HA_TO_M4_HVAC_MODE.items()}

HA_TO_M4_FAN_MODE = {"low": "LOW", "medium": "MID", "high": "HIGH"}
M4_TO_HA_FAN_MODE = {v: k for k, v in HA_TO_M4_FAN_MODE.items()}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up dinplug climates from YAML."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    climates_conf = config[CONF_CLIMATES]

    conn = hass.data[DOMAIN].get((host, port))
    if not conn:
        conn = M4Connection(hass, host, port)
        hass.data[DOMAIN][(host, port)] = conn
        conn.start()

    entities = [
        M4Climate(conn, host, port, cfg[CONF_NAME], cfg[CONF_DEVICE])
        for cfg in climates_conf
    ]
    async_add_entities(entities, update_before_add=True)


class M4Climate(ClimateEntity):
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
    _attr_fan_modes = ["low", "medium", "high"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )

    def __init__(self, conn: M4Connection, host: str, port: int, name: str, device: int):
        self._conn = conn
        self._host = host
        self._port = port
        self._attr_name = name
        self._device = device
        self._attr_unique_id = f"{host}-{port}-{device}-hvac"

        self._state: Dict[str, Any] = {}

        self._conn.register_hvac_listener(self._device, self._handle_update)

        last_state = self._conn.get_last_hvac_state(self._device)
        if last_state:
            self._handle_update(last_state)

    def _handle_update(self, state: Dict[str, Any]):
        self._state = state
        self.schedule_update_ha_state()

    @property
    def current_temperature(self) -> Optional[float]:
        return self._state.get("current_temperature")

    @property
    def target_temperature(self) -> Optional[float]:
        return self._state.get("temperature")

    @property
    def hvac_mode(self) -> Optional[HVACMode]:
        mode = self._state.get("mode")
        return M4_TO_HA_HVAC_MODE.get(mode.upper()) if mode else None

    @property
    def fan_mode(self) -> Optional[str]:
        mode = self._state.get("fan_mode")
        return M4_TO_HA_FAN_MODE.get(mode.upper()) if mode else None

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        if self.hvac_mode == HVACMode.COOL:
            return HVACAction.COOLING
        if self.hvac_mode == HVACMode.HEAT:
            return HVACAction.HEATING
        if self.hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        return HVACAction.OFF

    async def async_set_temperature(self, **kwargs):
        if temp := kwargs.get("temperature"):
            self._conn.send_hvac(self._device, "SETPOINT", temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if m4_mode := HA_TO_M4_HVAC_MODE.get(hvac_mode):
            self._conn.send_hvac(self._device, m4_mode)

    async def async_set_fan_mode(self, fan_mode: str):
        if m4_mode := HA_TO_M4_FAN_MODE.get(fan_mode):
            self._conn.send_hvac(self._device, f"FAN{m4_mode}")
