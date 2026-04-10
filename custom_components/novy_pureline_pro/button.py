"""Button entities for Novy Pureline Pro."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
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
    """Set up Novy button entities."""
    coordinator: NovyCoordinator = entry.runtime_data
    address: str = entry.data[CONF_ADDRESS]
    await async_add_entities([
        NovyResetGreaseButton(coordinator, address),
        NovyDelayedOffButton(coordinator, address),
        NovyPowerButton(coordinator, address),
    ])


class _NovyButton(NovyBaseEntity, ButtonEntity):
    """Base class for all Novy button entities.

    Subclasses declare ``_suffix`` (unique_id suffix) and
    ``_coordinator_method`` (name of the coordinator coroutine to call on press).
    """

    _suffix: str
    _coordinator_method: str

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the button entity."""
        super().__init__(coordinator, address, self._suffix)

    async def async_press(self) -> None:
        """Invoke the coordinator action for this button."""
        await getattr(self.coordinator, self._coordinator_method)()


class NovyResetGreaseButton(_NovyButton):
    """Button to reset the grease filter timer."""

    _attr_name = "Reset Grease Timer"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _suffix = "reset_grease"
    _coordinator_method = "reset_grease_timer"


class NovyDelayedOffButton(_NovyButton):
    """Button to activate delayed off."""

    _attr_name = "Delayed Off"
    _suffix = "delayed_off"
    _coordinator_method = "delayed_off"


class NovyPowerButton(_NovyButton):
    """Button to toggle power."""

    _attr_name = "Power"
    _suffix = "power"
    _coordinator_method = "power_toggle"
