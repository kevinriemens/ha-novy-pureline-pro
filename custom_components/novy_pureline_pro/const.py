"""Constants for the Novy Pureline Pro BLE integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "novy_pureline_pro"

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.FAN, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH]

# Nordic UART Service (NUS) UUIDs
UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # notify/read
UART_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write

# Command IDs (sent to device via RX)
CMD_POWER_TOGGLE = 10
CMD_DELAYED_OFF = 11
CMD_LIGHT_AMBI = 15
CMD_LIGHT_WHITE = 16
CMD_BRIGHTNESS = 21
CMD_COLOR_TEMP = 22
CMD_RESET_GREASE = 23
CMD_RECIRCULATE = 25
CMD_FAN_SPEED = 28
CMD_FAN_STATE = 29
CMD_LIGHT_OFF = 36

# Status request IDs (device sends back via TX notifications)
STATUS_MAIN = 400
STATUS_GREASE = 402
STATUS_DEFAULTS = 403
STATUS_LED = 404

# Light mode values
LIGHT_MODE_OFF = 0
LIGHT_MODE_WHITE = 1
LIGHT_MODE_AMBI = 2

# Throttle — minimum interval between commands in seconds (300 ms).
# The hood firmware crashes if commands arrive faster than this.
MIN_COMMAND_INTERVAL = 0.3

# Color temperature range in mireds (Home Assistant convention).
# Device 0   → 154 mireds (6500 K, cool/white)
# Device 255 → 370 mireds (2700 K, warm/amber)
MIN_MIREDS = 154
MAX_MIREDS = 370

# Mid-point used for white vs. ambi mode selection (mireds)
COLOR_TEMP_MODE_THRESHOLD = 262

# Timeout waiting for a command ACK before forcing reconnect (seconds)
PENDING_REQUEST_TIMEOUT = 15.0

# Poll interval fallback (notifications are the primary update path)
UPDATE_INTERVAL_SECONDS = 5
