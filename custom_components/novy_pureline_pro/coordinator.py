"""BLE connection manager, packet parser, and DataUpdateCoordinator for Novy Pureline Pro."""
from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections_by_address,
    establish_connection,
)

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CMD_BRIGHTNESS,
    CMD_COLOR_TEMP,
    CMD_DELAYED_OFF,
    CMD_FAN_SPEED,
    CMD_FAN_STATE,
    CMD_LIGHT_AMBI,
    CMD_LIGHT_OFF,
    CMD_LIGHT_WHITE,
    CMD_POWER_TOGGLE,
    CMD_RECIRCULATE,
    CMD_RESET_GREASE,
    DOMAIN,
    MIN_COMMAND_INTERVAL,
    PENDING_REQUEST_TIMEOUT,
    STATUS_DEFAULTS,
    STATUS_GREASE,
    STATUS_LED,
    STATUS_MAIN,
    UART_RX_CHAR_UUID,
    UART_TX_CHAR_UUID,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

# Status packets rotate through these three supplemental IDs
_SUPPLEMENTAL_STATUS = [STATUS_GREASE, STATUS_DEFAULTS, STATUS_LED]


@dataclass
class NovyState:
    """Snapshot of all device state parsed from BLE notifications."""

    fan_speed: int = 0          # 0-100 (maps directly to HA percentage)
    fan_on: bool = False
    light_mode: int = 0         # 0=off, 1=white, 2=ambi
    brightness: int = 0         # 0-255 device scale
    color_temp: int = 0         # 0-255 device raw value
    clean_grease: bool = False
    recirculate: bool = False
    grease_timer: int = 0       # seconds
    fan_hours: int = 0          # seconds
    led_hours: int = 0          # seconds
    countdown: int = 0          # seconds
    firmware: str = ""
    default_speed: int = 0
    available: bool = False


class NovyCoordinator(DataUpdateCoordinator[NovyState]):
    """Manages BLE connection, packet parsing, and state updates for Novy Pureline Pro."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        ble_device: BLEDevice,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{address}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._address = address
        self._name = name
        self._ble_device = ble_device

        self._client: BleakClient | None = None
        self._state = NovyState()

        # Flow-control: serialise outgoing commands and wait for ACK.
        self._command_lock = asyncio.Lock()
        self._pending_event: asyncio.Event | None = None
        self._last_command_time: float = 0.0

        # Track which status command was last sent so we can match the binary
        # response to the correct parser (packets carry no ID in their payload).
        self._pending_status_cmd: int | None = None

        # Round-robin index for supplemental status requests
        self._supplemental_idx: int = 0

        # Cleanup callbacks registered with HA
        self._cancel_callbacks: list[Callable[[], None]] = []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def address(self) -> str:
        """Return the BLE device MAC address."""
        return self._address

    @property
    def device_name(self) -> str:
        """Return the device name."""
        return self._name

    # ------------------------------------------------------------------
    # BLE device tracking (called from __init__.py)
    # ------------------------------------------------------------------

    @callback
    def update_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the cached BLEDevice when a new advertisement is seen."""
        self._ble_device = ble_device

    @callback
    def set_unavailable(self) -> None:
        """Mark device as unavailable (called when BLE goes away)."""
        self._state.available = False
        self.async_set_updated_data(self._state)

    def register_cancel_callback(self, cancel: Callable[[], None]) -> None:
        """Register a cleanup callback to run on unload."""
        self._cancel_callbacks.append(cancel)

    async def async_shutdown(self) -> None:
        """Disconnect and clean up all callbacks (idempotent)."""
        for cancel in self._cancel_callbacks:
            cancel()
        self._cancel_callbacks.clear()
        await self._async_disconnect()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _async_connect(self) -> None:
        """Open a BLE connection and subscribe to TX notifications."""
        _LOGGER.debug("Connecting to %s (%s)", self._name, self._address)
        await close_stale_connections_by_address(self._address)

        self._client = await establish_connection(
            client_class=BleakClientWithServiceCache,
            device=self._ble_device,
            name=self._name,
            disconnected_callback=self._on_disconnect,
            max_attempts=3,
        )

        await self._client.start_notify(UART_TX_CHAR_UUID, self._on_notification)
        _LOGGER.debug("Connected to %s", self._name)
        self._state.available = True

    async def _async_disconnect(self) -> None:
        """Cleanly close the BLE connection."""
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._client = None

    def _on_disconnect(self, client: BleakClient) -> None:  # noqa: ARG002
        """Handle unexpected BLE disconnection."""
        _LOGGER.warning("Disconnected from %s — will reconnect on next update", self._name)
        self._state.available = False
        self._client = None
        # Wake up any waiting pending event so callers don't block forever
        if self._pending_event is not None:
            self._pending_event.set()

    async def _async_ensure_connected(self) -> None:
        """Reconnect if the client is absent or disconnected."""
        if self._client is None or not self._client.is_connected:
            await self._async_connect()

    # ------------------------------------------------------------------
    # Notification handling / packet parsing
    # ------------------------------------------------------------------

    def _on_notification(self, _sender: int, data: bytearray) -> None:
        """Handle incoming BLE notifications from the TX characteristic."""
        raw = bytes(data)

        # ASCII ACK response (e.g. command echo) — just unblock the caller
        if raw and raw[0:1] == b"[":
            _LOGGER.debug("ASCII ACK: %s", raw.decode("ascii", errors="replace"))
            if self._pending_event is not None:
                self._pending_event.set()
            return

        # Binary status packet — route based on which command we sent
        self._parse_packet(raw)

        # Unblock any pending command waiting for an ACK
        if self._pending_event is not None:
            self._pending_event.set()

    def _parse_packet(self, data: bytes) -> None:
        """Parse a binary status packet and update internal state.

        The Novy hood does NOT include a packet ID in the notification payload.
        We determine which parser to use from ``_pending_status_cmd`` (context-based)
        combined with payload length as a sanity check.
        """
        if len(data) < 2:
            return

        pending = self._pending_status_cmd

        try:
            if pending == STATUS_MAIN and len(data) >= 16:
                self._parse_status_main(data)
            elif pending == STATUS_GREASE and len(data) >= 24:
                self._parse_status_grease(data)
            elif pending == STATUS_DEFAULTS and len(data) >= 20:
                self._parse_status_defaults(data)
            elif pending == STATUS_LED and len(data) >= 20:
                self._parse_status_led(data)
            elif pending is None:
                # Unsolicited notification — try length-based detection as fallback.
                # Packet 400 (16 bytes) is the most common unsolicited packet.
                if len(data) == 16:
                    self._parse_status_main(data)
                elif len(data) == 24:
                    self._parse_status_grease(data)
                else:
                    _LOGGER.debug(
                        "Unsolicited packet of %d bytes (no pending cmd) — skipped",
                        len(data),
                    )
                    return
            else:
                _LOGGER.debug(
                    "Unexpected packet: pending=%s, length=%d", pending, len(data)
                )
                return
        except struct.error as exc:
            _LOGGER.debug("Packet parse error (pending=%s): %s", pending, exc)
            return

        self.async_set_updated_data(self._state)

    def _parse_status_main(self, data: bytes) -> None:
        """Packet 400 (16 bytes): fan speed, light mode, brightness, color temp."""
        self._state.fan_speed = data[1]
        self._state.clean_grease = bool(data[2] & 0x01)
        self._state.light_mode = data[5]
        self._state.brightness = data[6]
        self._state.color_temp = data[7]
        self._state.countdown = struct.unpack_from(">H", data, 8)[0]
        self._state.fan_on = self._state.fan_speed > 0

    def _parse_status_grease(self, data: bytes) -> None:
        """Packet 402 (24 bytes): recirculate flag, grease timer, firmware version."""
        self._state.recirculate = bool(data[2] & 0x01)
        self._state.grease_timer = struct.unpack_from(">I", data, 4)[0]
        self._state.firmware = f"{data[8]}.{data[9]}.{data[10]}"

    def _parse_status_defaults(self, data: bytes) -> None:
        """Packet 403 (20 bytes): fan run hours, default speed."""
        self._state.fan_hours = struct.unpack_from(">I", data, 10)[0]
        self._state.default_speed = data[14]

    def _parse_status_led(self, data: bytes) -> None:
        """Packet 404 (~20 bytes): LED run hours."""
        if len(data) >= 17:
            self._state.led_hours = struct.unpack_from(">I", data, 13)[0]

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------

    def _build_command(self, *args: int) -> bytes:
        """Build an ASCII command string from integer arguments.

        Format: ``[arg0;arg1;arg2;...]`` encoded as UTF-8 bytes.
        """
        payload = "[" + ";".join(str(a) for a in args) + "]"
        return payload.encode()

    async def _async_send_command(self, *args: int, wait_for_ack: bool = True) -> None:
        """Send a command to the device with throttling and optional ACK waiting."""
        async with self._command_lock:
            await self._async_ensure_connected()

            # Enforce minimum interval between commands (300 ms throttle)
            now = self.hass.loop.time()
            elapsed = now - self._last_command_time
            if elapsed < MIN_COMMAND_INTERVAL:
                await asyncio.sleep(MIN_COMMAND_INTERVAL - elapsed)

            command_bytes = self._build_command(*args)

            # Track which status command we're sending so the notification
            # handler knows which parser to use (packets carry no ID).
            cmd_id = args[0] if args else None
            if cmd_id in {STATUS_MAIN, STATUS_GREASE, STATUS_DEFAULTS, STATUS_LED}:
                self._pending_status_cmd = cmd_id
            else:
                self._pending_status_cmd = None

            if wait_for_ack:
                self._pending_event = asyncio.Event()

            if self._client is None:
                _LOGGER.error("Cannot send command %s — client is None after connect", args)
                self._pending_event = None
                self._pending_status_cmd = None
                raise RuntimeError("BLE client unexpectedly None after connect")

            try:
                await self._client.write_gatt_char(
                    UART_RX_CHAR_UUID, command_bytes, response=True
                )
                self._last_command_time = self.hass.loop.time()
            except Exception as exc:
                _LOGGER.error("Command %s failed: %s", args, exc)
                self._pending_event = None
                self._pending_status_cmd = None
                await self._async_disconnect()
                raise

            if wait_for_ack and self._pending_event is not None:
                try:
                    await asyncio.wait_for(
                        self._pending_event.wait(), timeout=PENDING_REQUEST_TIMEOUT
                    )
                except TimeoutError:
                    _LOGGER.warning(
                        "Timeout waiting for ACK from %s — forcing reconnect", self._name
                    )
                    await self._async_disconnect()
                finally:
                    self._pending_event = None
                    self._pending_status_cmd = None

    # ------------------------------------------------------------------
    # DataUpdateCoordinator hook
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> NovyState:
        """Fetch the latest state from the device (fallback poll)."""
        try:
            # Always request main status
            await self._async_send_command(STATUS_MAIN, 0)

            # Round-robin through supplemental status requests
            supplemental = _SUPPLEMENTAL_STATUS[self._supplemental_idx]
            self._supplemental_idx = (self._supplemental_idx + 1) % len(_SUPPLEMENTAL_STATUS)
            await self._async_send_command(supplemental, 0)

        except Exception as exc:
            raise UpdateFailed(f"Error communicating with {self._name}: {exc}") from exc

        return self._state

    # ------------------------------------------------------------------
    # Public command API (used by fan.py and light.py)
    # ------------------------------------------------------------------

    async def set_fan_speed(self, speed: int) -> None:
        """Set fan speed (0-100). Sends ``[28;1;speed]``."""
        await self._async_send_command(CMD_FAN_SPEED, 1, speed)

    async def set_fan_state(self, on: bool) -> None:
        """Turn fan on or off. Sends ``[29;1;1]`` or ``[29;1;0]``."""
        await self._async_send_command(CMD_FAN_STATE, 1, 1 if on else 0)

    async def set_light_white(self) -> None:
        """Switch to white light mode. Sends ``[16;0]``."""
        await self._async_send_command(CMD_LIGHT_WHITE, 0)

    async def set_light_ambi(self) -> None:
        """Switch to ambient light mode. Sends ``[15;0]``."""
        await self._async_send_command(CMD_LIGHT_AMBI, 0)

    async def set_brightness(self, value: int) -> None:
        """Set brightness (0-255). Sends ``[21;1;value]``."""
        await self._async_send_command(CMD_BRIGHTNESS, 1, value)

    async def set_color_temp(self, value: int) -> None:
        """Set color temperature raw (0-255). Sends ``[22;1;value]``."""
        await self._async_send_command(CMD_COLOR_TEMP, 1, value)

    async def turn_light_off(self) -> None:
        """Turn light off. Sends ``[36;0]``."""
        await self._async_send_command(CMD_LIGHT_OFF, 0)

    async def power_toggle(self) -> None:
        """Toggle power. Sends ``[10;0]``."""
        await self._async_send_command(CMD_POWER_TOGGLE, 0)

    async def reset_grease_timer(self) -> None:
        """Reset grease filter timer. Sends ``[23;0]`` — no ACK expected."""
        await self._async_send_command(CMD_RESET_GREASE, 0, wait_for_ack=False)

    async def set_recirculate(self, on: bool) -> None:
        """Set recirculate mode. Sends [25;1;1] or [25;1;0]."""
        await self._async_send_command(CMD_RECIRCULATE, 1, 1 if on else 0)

    async def delayed_off(self) -> None:
        """Activate delayed off. Sends [11;0]."""
        await self._async_send_command(CMD_DELAYED_OFF, 0)


# ---------------------------------------------------------------------------
# Shared base entity
# ---------------------------------------------------------------------------

_DEVICE_INFO_CACHE: dict[str, DeviceInfo] = {}


def _build_device_info(address: str, name: str) -> DeviceInfo:
    """Return a cached DeviceInfo for the given BLE address.

    All entities belonging to the same physical device must share an identical
    ``DeviceInfo`` so HA can group them under a single device entry.
    """
    if address not in _DEVICE_INFO_CACHE:
        _DEVICE_INFO_CACHE[address] = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            manufacturer="Novy",
            model="Pureline Pro",
            name=name,
        )
    return _DEVICE_INFO_CACHE[address]


class NovyBaseEntity(CoordinatorEntity[NovyCoordinator]):
    """Base class shared by all Novy Pureline Pro entities.

    Provides:
    - Safe ``_state`` accessor that returns a default ``NovyState`` when the
      coordinator has not yet delivered data (avoids ``AttributeError`` on
      ``coordinator.data`` being ``None`` during the first HA startup cycle).
    - Unified ``available`` property backed by the state flag.
    - ``_handle_coordinator_update`` that calls ``async_write_ha_state``.
    - Shared ``DeviceInfo`` construction (same device, single registry entry).
    """

    _attr_has_entity_name = True
    # Setting name=None tells HA to use the device name as the entity name,
    # which is the correct pattern for a device that exposes a single primary
    # entity per platform (fan / light).
    _attr_name = None

    def __init__(self, coordinator: NovyCoordinator, address: str, unique_suffix: str) -> None:
        """Initialise the base entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{address}_{unique_suffix}"
        self._attr_device_info = _build_device_info(address, coordinator.device_name)

    @property
    def _state(self) -> NovyState:
        """Return coordinator data, falling back to a safe default when not yet available."""
        return self.coordinator.data if self.coordinator.data is not None else NovyState()

    @property
    def available(self) -> bool:
        """Return True if the device is reachable."""
        return self._state.available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        self.async_write_ha_state()
