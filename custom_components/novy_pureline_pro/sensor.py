"""Sensor entities for Novy Pureline Pro."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NovyBaseEntity, NovyCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Novy sensor entities."""
    coordinator: NovyCoordinator = entry.runtime_data
    address: str = entry.data[CONF_ADDRESS]
    await async_add_entities([
        NovyGreaseTimerSensor(coordinator, address),
        NovyFanHoursSensor(coordinator, address),
        NovyLedHoursSensor(coordinator, address),
        NovyOffTimerSensor(coordinator, address),
        NovyBoostTimerSensor(coordinator, address),
    ])


class _NovyDurationSensor(NovyBaseEntity, SensorEntity):
    """Base class for all duration-based sensor entities."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: NovyCoordinator, address: str, suffix: str) -> None:
        """Initialise the duration sensor."""
        super().__init__(coordinator, address, suffix)


class NovyGreaseTimerSensor(_NovyDurationSensor):
    """Grease filter timer sensor (seconds → minutes)."""

    _attr_name = "Grease Timer"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the grease timer sensor."""
        super().__init__(coordinator, address, "grease_timer")

    @property
    def native_value(self) -> int:
        """Return grease timer in minutes."""
        return self._state.grease_timer // 60


class NovyFanHoursSensor(_NovyDurationSensor):
    """Fan run-hours sensor (seconds → hours)."""

    _attr_name = "Fan Hours"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the fan hours sensor."""
        super().__init__(coordinator, address, "fan_hours")

    @property
    def native_value(self) -> int:
        """Return fan hours."""
        return self._state.fan_hours // 3600


class NovyLedHoursSensor(_NovyDurationSensor):
    """LED run-hours sensor (seconds → hours)."""

    _attr_name = "LED Hours"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the LED hours sensor."""
        super().__init__(coordinator, address, "led_hours")

    @property
    def native_value(self) -> int:
        """Return LED hours."""
        return self._state.led_hours // 3600


class NovyOffTimerSensor(_NovyDurationSensor):
    """Off timer countdown sensor (seconds, no conversion)."""

    _attr_name = "Off Timer"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the off timer sensor."""
        super().__init__(coordinator, address, "off_timer")

    @property
    def native_value(self) -> int:
        """Return countdown in seconds."""
        return self._state.countdown


class NovyBoostTimerSensor(_NovyDurationSensor):
    """Boost timer countdown sensor (seconds, no conversion)."""

    _attr_name = "Boost Timer"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NovyCoordinator, address: str) -> None:
        """Initialise the boost timer sensor."""
        super().__init__(coordinator, address, "boost_timer")

    @property
    def native_value(self) -> int:
        """Return countdown in seconds."""
        return self._state.countdown
