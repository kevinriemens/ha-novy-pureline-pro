"""Light entity for Novy Pureline Pro."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COLOR_TEMP_MODE_THRESHOLD,
    LIGHT_MODE_AMBI,
    LIGHT_MODE_OFF,
    LIGHT_MODE_WHITE,
)
from .coordinator import NovyBaseEntity, NovyCoordinator

_LOGGER = logging.getLogger(__name__)

# Color temperature range in Kelvin
MIN_KELVIN = 2700  # warm/amber (device 255)
MAX_KELVIN = 6500  # cool/white (device 0)

# Kelvin threshold for mode selection (corresponds to ~3800K)
_MODE_THRESHOLD_KELVIN = round(1_000_000 / COLOR_TEMP_MODE_THRESHOLD)


def _device_to_kelvin(raw: int) -> int:
    """Map device 0-255 → Kelvin 6500-2700.

    Device 0   = 6500 K (cool/white)
    Device 255 = 2700 K (warm/amber)
    """
    return round(MAX_KELVIN - (raw * (MAX_KELVIN - MIN_KELVIN) / 255))


def _kelvin_to_device(kelvin: int) -> int:
    """Map Kelvin 6500-2700 → device 0-255."""
    return round((MAX_KELVIN - kelvin) * 255 / (MAX_KELVIN - MIN_KELVIN))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Novy light entity."""
    coordinator: NovyCoordinator = entry.runtime_data
    async_add_entities([NovyLight(coordinator, entry.data[CONF_ADDRESS])])


class NovyLight(NovyBaseEntity, LightEntity):
    """Represents the Novy Pureline Pro integrated light."""

    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_min_color_temp_kelvin = MIN_KELVIN
    _attr_max_color_temp_kelvin = MAX_KELVIN

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the light entity."""
        super().__init__(coordinator, address, "light")

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        """Return True when the light is emitting (brightness > 0)."""
        return self._state.brightness > 0

    @property
    def brightness(self) -> int:
        """Return brightness in HA scale (0-255, same as device scale)."""
        return self._state.brightness

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return color temperature in Kelvin."""
        return _device_to_kelvin(self._state.color_temp)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on with optional brightness and color temp.

        Command order (throttling is handled by coordinator's command lock):
        1. Set light mode (white or ambi) based on color_temp
        2. Set brightness (default 255)
        3. Set color temperature (if provided)
        """
        requested_kelvin: int | None = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        requested_brightness: int | None = kwargs.get(ATTR_BRIGHTNESS)

        # --- 1. Determine and apply light mode ---
        if requested_kelvin is not None:
            if requested_kelvin >= _MODE_THRESHOLD_KELVIN:
                await self.coordinator.set_light_white()
            else:
                await self.coordinator.set_light_ambi()
        else:
            # Keep current mode; if currently off, default to white
            current_mode = self._state.light_mode
            if current_mode in (LIGHT_MODE_WHITE, LIGHT_MODE_OFF):
                await self.coordinator.set_light_white()
            else:
                await self.coordinator.set_light_ambi()

        # --- 2. Set brightness ---
        brightness = requested_brightness if requested_brightness is not None else 255
        await self.coordinator.set_brightness(brightness)

        # --- 3. Set color temperature (if provided) ---
        if requested_kelvin is not None:
            device_ct = _kelvin_to_device(requested_kelvin)
            await self.coordinator.set_color_temp(device_ct)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn the light off."""
        await self.coordinator.turn_light_off()
