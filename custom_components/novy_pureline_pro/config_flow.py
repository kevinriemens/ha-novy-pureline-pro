"""Config flow for Novy Pureline Pro BLE integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import DOMAIN, UART_TX_CHAR_UUID

_LOGGER = logging.getLogger(__name__)


class NovyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Novy Pureline Pro."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._discovered: dict[str, str] = {}  # address → name
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    # ------------------------------------------------------------------
    # Bluetooth auto-discovery
    # ------------------------------------------------------------------

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a Bluetooth discovery (matched by service UUID in manifest)."""
        _LOGGER.debug(
            "Bluetooth discovery: %s (%s)", discovery_info.name, discovery_info.address
        )

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered device."""
        assert self._discovery_info is not None

        if user_input is not None:
            return self._create_entry(
                address=self._discovery_info.address,
                name=self._discovery_info.name,
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self._discovery_info.name},
        )

    # ------------------------------------------------------------------
    # Manual / user-initiated setup
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show form — pick from discovered devices or type a MAC address."""
        errors: dict[str, str] = {}

        # Collect all nearby connectable BLE devices — no UUID filter so the
        # integration works regardless of which service UUID the hood advertises.
        # Validation happens on connect (NUS characteristic check).
        self._discovered = {
            info.address: info.name or info.address
            for info in bluetooth.async_discovered_service_info(self.hass)
            if info.connectable and info.name
        }

        # Abort immediately if there's nothing to configure
        if not self._discovered and user_input is None:
            return self.async_abort(reason="no_devices_found")

        if user_input is not None:
            address: str = user_input[CONF_ADDRESS].strip().upper()
            name: str = self._discovered.get(address, address)

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            # Validate we can actually reach the device
            connected = await self._async_validate_connection(address)
            if not connected:
                errors["base"] = "cannot_connect"
            else:
                return self._create_entry(address=address, name=name)

        # Build address selector — either a drop-down or free-text input
        if self._discovered:
            options = [
                SelectOptionDict(value=addr, label=f"{name} ({addr})")
                for addr, name in self._discovered.items()
            ]
            address_field = SelectSelector(
                SelectSelectorConfig(options=options, custom_value=True)
            )
        else:
            address_field = vol.Schema(str)  # type: ignore[assignment]

        schema = vol.Schema({vol.Required(CONF_ADDRESS): address_field})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _async_validate_connection(self, address: str) -> bool:
        """Attempt a quick connection to verify the device is reachable."""
        from bleak import BleakClient  # local import to avoid top-level bleak dep at import

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, address, connectable=True
        )
        if ble_device is None:
            return False

        try:
            async with BleakClient(ble_device, timeout=10.0) as client:
                # Try reading the TX characteristic to confirm NUS is present
                await asyncio.wait_for(
                    client.read_gatt_char(UART_TX_CHAR_UUID), timeout=8.0
                )
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Validation connect failed for %s: %s", address, exc)
            return False

    def _create_entry(self, address: str, name: str) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=name,
            data={CONF_ADDRESS: address, CONF_NAME: name},
        )
