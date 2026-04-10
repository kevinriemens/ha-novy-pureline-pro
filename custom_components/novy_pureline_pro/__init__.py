"""Integration setup for Novy Pureline Pro BLE integration."""
from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import PLATFORMS
from .coordinator import NovyCoordinator

_LOGGER = logging.getLogger(__name__)

type NovyConfigEntry = ConfigEntry[NovyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: NovyConfigEntry) -> bool:
    """Set up Novy Pureline Pro from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    name: str = entry.data[CONF_NAME]

    # Close any stale connections left from a previous HA session
    from bleak_retry_connector import close_stale_connections_by_address  # noqa: PLC0415

    await close_stale_connections_by_address(address)

    # Resolve the BLE device from the scanner cache
    ble_device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Could not find BLE device {address}. Make sure it is powered on and in range."
        )

    coordinator = NovyCoordinator(hass, address, name, ble_device)

    # Perform first refresh — this will open the BLE connection
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator on the entry for platform access
    entry.runtime_data = coordinator

    # Register callback for new BLE advertisement updates
    @callback
    def _on_ble_advertisement(
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        """Update cached BLE device on new advertisement."""
        _LOGGER.debug("BLE advertisement from %s (change=%s)", address, change)
        coordinator.update_ble_device(service_info.device)

    cancel_advertisement = bluetooth.async_register_callback(
        hass,
        _on_ble_advertisement,
        BluetoothCallbackMatcher(address=address, connectable=True),
        BluetoothScanningMode.ACTIVE,
    )
    coordinator.register_cancel_callback(cancel_advertisement)

    # Register callback for device becoming unavailable
    @callback
    def _on_unavailable(service_info: BluetoothServiceInfoBleak) -> None:
        """Handle BLE device disappearing from scanner."""
        _LOGGER.warning("Novy Pureline Pro %s is unavailable", address)
        coordinator.set_unavailable()

    cancel_unavailable = bluetooth.async_track_unavailable(
        hass, _on_unavailable, address, connectable=True
    )
    coordinator.register_cancel_callback(cancel_unavailable)

    # Forward platforms (fan + light)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register a shutdown handler to cleanly disconnect on HA stop / entry unload
    entry.async_on_unload(coordinator.async_shutdown)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NovyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
