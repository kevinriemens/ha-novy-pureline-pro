"""Switch entities for Novy Pureline Pro."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NovyBaseEntity, NovyCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Novy switch entities."""
    coordinator: NovyCoordinator = entry.runtime_data
    address: str = entry.data[CONF_ADDRESS]
    await async_add_entities([
        NovyRecirculateSwitch(coordinator, address),
    ])


class NovyRecirculateSwitch(NovyBaseEntity, SwitchEntity):
    """Switch to toggle recirculate mode."""

    _attr_name = "Recirculate"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the recirculate switch."""
        super().__init__(coordinator, address, "recirculate")

    @property
    def is_on(self) -> bool:
        """Return True when recirculate is active."""
        return self._state.recirculate

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Enable recirculate mode."""
        await self.coordinator.set_recirculate(True)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Disable recirculate mode."""
        await self.coordinator.set_recirculate(False)
