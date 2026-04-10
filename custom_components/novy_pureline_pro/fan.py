"""Fan entity for Novy Pureline Pro."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NovyBaseEntity, NovyCoordinator

_LOGGER = logging.getLogger(__name__)

# Number of discrete speed steps exposed to HA (10%, 20%, …, 100%)
SPEED_COUNT = 10


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Novy fan entity."""
    coordinator: NovyCoordinator = entry.runtime_data
    async_add_entities([NovyFan(coordinator, entry.data[CONF_ADDRESS])])


class NovyFan(NovyBaseEntity, FanEntity):
    """Represents the Novy Pureline Pro extractor fan."""

    _attr_supported_features = FanEntityFeature.SET_SPEED
    _attr_speed_count = SPEED_COUNT

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the fan entity."""
        super().__init__(coordinator, address, "fan")

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        """Return True if the fan is running."""
        return self._state.fan_on

    @property
    def percentage(self) -> int | None:
        """Return current speed as a percentage (0-100)."""
        if not self._state.fan_on:
            return 0
        return self._state.fan_speed

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Turn the fan on, optionally at a specific speed."""
        target_speed = percentage if percentage is not None else 50
        await self.coordinator.set_fan_state(True)
        await self.coordinator.set_fan_speed(target_speed)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn the fan off."""
        await self.coordinator.set_fan_state(False)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed percentage. Setting 0 turns the fan off."""
        if percentage == 0:
            await self.coordinator.set_fan_state(False)
        else:
            await self.coordinator.set_fan_speed(percentage)
