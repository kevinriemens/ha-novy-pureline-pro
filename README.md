# Novy Pureline Pro

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/kevinriemens/ha-novy-pureline-pro)](https://github.com/kevinriemens/ha-novy-pureline-pro/releases)
[![License: MIT](https://img.shields.io/github/license/kevinriemens/ha-novy-pureline-pro)](LICENSE)

Home Assistant custom integration for **Novy Pureline Pro** kitchen hoods via Bluetooth LE.

Control your Novy hood directly from Home Assistant — no cloud, no bridge, just local BLE. Auto-discovered when in range.

## Supported Devices

Novy Pureline Pro kitchen hoods with built-in Bluetooth LE (BLE advertising name: `Pureline*`).

> Novy is a Belgian brand specializing in kitchen ventilation. The Pureline Pro is their premium recirculation hood with integrated lighting and BLE control.

## Features

| Entity | Type | Description |
|--------|------|-------------|
| Fan | `fan` | Speed control (10 steps, 0-100%), on/off |
| Light | `light` | Brightness + color temperature (2700K–6500K), white/ambient modes |
| Grease Filter Timer | `sensor` | Hours until grease filter cleaning |
| Fan Running Hours | `sensor` | Total fan operation hours |
| LED Running Hours | `sensor` | Total LED operation hours |
| Off Timer | `sensor` | Delayed off countdown (minutes) |
| Boost Timer | `sensor` | Boost mode countdown (minutes) |
| Clean Grease Filter | `binary_sensor` | Alert when grease filter needs cleaning |
| Recirculate | `switch` | Toggle recirculation mode |
| Reset Grease Timer | `button` | Reset the grease filter timer after cleaning |
| Delayed Off | `button` | Start delayed off timer |
| Power Toggle | `button` | Toggle power on/off |

**11 entities** total: 1 fan, 1 light, 5 sensors, 1 binary sensor, 1 switch, 3 buttons.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the **three dots** menu (top right) → **Custom repositories**
3. Add repository URL: `https://github.com/kevinriemens/ha-novy-pureline-pro`
4. Category: **Integration**
5. Click **Add** → find "Novy Pureline Pro" → **Download**
6. Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/kevinriemens/ha-novy-pureline-pro/releases)
2. Copy `custom_components/novy_pureline_pro/` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Auto-Discovery (Recommended)

If your Home Assistant host has a Bluetooth adapter, the integration will automatically discover Novy hoods in range. A notification will appear to set up the device.

### Manual Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Novy Pureline Pro"
3. Enter the MAC address of your hood (find it in the Novy app under device settings)

## Troubleshooting

### Device Not Found

- Ensure your Novy hood is powered on and BLE is enabled
- Check that Home Assistant has a working Bluetooth adapter (`Settings → System → Hardware`)
- Move the HA host closer to the hood — BLE range is typically 5-10 meters
- Try restarting the Bluetooth integration in HA

### Connection Drops

- BLE connections can be affected by interference from other 2.4GHz devices
- Consider using a USB Bluetooth adapter with an extension cable placed closer to the hood
- The integration uses `bleak-retry-connector` for automatic reconnection

### Debug Logging

Enable debug logs for troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.novy_pureline_pro: debug
```

### Bluetooth Adapter Requirements

- Any Bluetooth 4.0+ (BLE) adapter supported by [bleak](https://github.com/hbldh/bleak)
- Built-in Raspberry Pi Bluetooth works but external USB adapters often have better range
- ESPHome Bluetooth Proxy is **not supported** (direct BLE connection required)

## Contributing

PRs are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Whether it's a bug fix, new feature, translation, or documentation improvement — all contributions are appreciated.

## Credits & Acknowledgments

BLE protocol implementation based on [purelinepro](https://github.com/bwynants/purelinepro) by [@bwynants](https://github.com/bwynants) — an ESPHome C++ component for ESP32 BLE control of Novy Pureline Pro hoods. The C++ codebase served as the protocol reference for command IDs, packet structures, and Nordic UART Service implementation.

## License

This project is licensed under the [MIT License](LICENSE).
