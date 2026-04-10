"""Binary sensor entities for Novy Pureline Pro."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NovyBaseEntity, NovyCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Novy binary sensor entities."""
    coordinator: NovyCoordinator = entry.runtime_data
    address: str = entry.data[CONF_ADDRESS]
    await async_add_entities([
        NovyCleanGreaseBinarySensor(coordinator, address),
    ])


class NovyCleanGreaseBinarySensor(NovyBaseEntity, BinarySensorEntity):
    """Binary sensor that indicates when the grease filter needs cleaning."""

    _attr_name = "Clean Grease Filter"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the clean grease binary sensor."""
        super().__init__(coordinator, address, "clean_grease")

    @property
    def is_on(self) -> bool:
        """Return True when grease filter needs cleaning."""
        return self._state.clean_grease
