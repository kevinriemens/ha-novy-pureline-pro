---
name: novy-pureline-pro-architecture
description: Novy Pureline Pro HA integration architecture, BLE protocol, folder structure, and system overview. Use when understanding where code belongs or navigating the codebase.
metadata:
  skill-type: architecture
  language: python
  framework: home-assistant
  project-type: ha-custom-integration
---

# Novy Pureline Pro - Architecture

## System Overview

Home Assistant custom integration for **Novy Pureline Pro** kitchen hoods via Bluetooth LE. Uses Nordic UART Service (NUS) for bidirectional BLE communication. Implements the DataUpdateCoordinator pattern with notification-driven updates and 5-second polling fallback.

**11 entities:** 1 fan, 1 light, 5 sensors, 1 binary sensor, 1 switch, 3 buttons.

## Project Structure

```
custom_components/novy_pureline_pro/
├── __init__.py          # Entry point: coordinator setup, BLE callbacks, platform forwarding
├── const.py             # Protocol constants, UUIDs, command IDs
├── coordinator.py       # BLE connection manager, packet parser, DataUpdateCoordinator
├── config_flow.py       # Auto-discovery (BLE) + manual config flow
├── manifest.json        # Integration metadata, dependencies
├── strings.json         # Base UI strings
├── fan.py               # Fan speed control (0-100%, 10 steps)
├── light.py             # Brightness + color temperature (2700K-6500K)
├── sensor.py            # 5 diagnostic sensors (timers, hours)
├── binary_sensor.py     # Grease filter alert
├── switch.py            # Recirculate mode toggle
├── button.py            # 3 action buttons (reset grease, delayed off, power)
├── translations/
│   ├── en.json          # English
│   └── nl.json          # Dutch
└── brand/
    └── icon.png         # Integration icon
```

## Layer Architecture

```
┌─────────────────────────────────────────┐
│  Home Assistant Core                     │
│  (Config Entries, Device Registry, UI)   │
├─────────────────────────────────────────┤
│  Entity Platforms                        │
│  fan / light / sensor / binary_sensor    │
│  switch / button                         │
│  (Read state from coordinator,           │
│   send commands via coordinator)         │
├─────────────────────────────────────────┤
│  NovyCoordinator (coordinator.py)        │
│  - DataUpdateCoordinator subclass        │
│  - BLE connection management             │
│  - Command serialization (asyncio.Lock)  │
│  - Packet parsing (context-based)        │
│  - 300ms command throttle                │
│  - NovyState dataclass                   │
├─────────────────────────────────────────┤
│  BLE Transport                           │
│  bleak + bleak-retry-connector           │
│  Nordic UART Service (NUS)               │
└─────────────────────────────────────────┘
```

## Where to Put New Code

| I need to create...              | File                    | Pattern                          |
|----------------------------------|-------------------------|----------------------------------|
| New entity platform              | `{platform}.py`         | `NovyBaseEntity` + platform base |
| New BLE command                  | `coordinator.py`        | `async def {action}()` method    |
| New status parser                | `coordinator.py`        | `_parse_status_{name}()` method  |
| New command ID / constant        | `const.py`              | Add to constant group            |
| New state field                  | `coordinator.py`        | Add to `NovyState` dataclass     |
| Config flow change               | `config_flow.py`        | Extend step methods              |
| New translation                  | `translations/{lang}.json` | Follow existing structure     |
| CI/validation                    | `.github/workflows/`    | GitHub Actions YAML              |

## BLE Protocol Reference

### Nordic UART Service UUIDs
- **Service:** `6e400001-b5a3-f393-e0a9-e50e24dcca9e`
- **TX (device→HA):** `6e400003-b5a3-f393-e0a9-e50e24dcca9e` (notify)
- **RX (HA→device):** `6e400002-b5a3-f393-e0a9-e50e24dcca9e` (write)

### Command Format
ASCII: `[cmd_id;arg1;arg2;...]` encoded as UTF-8

### Key Command IDs
| ID  | Name             | Format         | Purpose              |
|-----|------------------|----------------|----------------------|
| 10  | POWER_TOGGLE     | `[10;0]`       | Toggle power         |
| 11  | DELAYED_OFF      | `[11;0]`       | Start delayed off    |
| 15  | LIGHT_AMBI       | `[15;0]`       | Ambient light mode   |
| 16  | LIGHT_WHITE      | `[16;0]`       | White light mode     |
| 21  | BRIGHTNESS       | `[21;1;val]`   | Set brightness 0-255 |
| 22  | COLOR_TEMP       | `[22;1;val]`   | Set color temp 0-255 |
| 23  | RESET_GREASE     | `[23;0]`       | Reset grease timer   |
| 25  | RECIRCULATE      | `[25;1;0/1]`   | Toggle recirculate   |
| 28  | FAN_SPEED        | `[28;1;pct]`   | Set fan speed 0-100  |
| 29  | FAN_STATE        | `[29;1;0/1]`   | Fan on/off           |
| 36  | LIGHT_OFF        | `[36;0]`       | Turn light off       |
| 400 | STATUS_MAIN      | `[400;0]`      | Request main status  |
| 402 | STATUS_GREASE    | `[402;0]`      | Request grease data  |
| 403 | STATUS_DEFAULTS  | `[403;0]`      | Request defaults     |
| 404 | STATUS_LED       | `[404;0]`      | Request LED hours    |

### Protocol Constraints
- **300ms throttle** between commands (firmware crashes otherwise)
- **15s ACK timeout** → forces reconnect
- **Context-based parsing** — packets carry no ID, parser determined by `_pending_status_cmd`
- **Command serialization** via `asyncio.Lock`

## Key Patterns

| Pattern                        | Usage                                                      |
|-------------------------------|------------------------------------------------------------|
| DataUpdateCoordinator          | Central state manager with polling + notification updates  |
| NovyBaseEntity                 | Shared base entity with safe `_state` accessor             |
| Cached DeviceInfo              | Module-level cache ensures all entities share same object   |
| Context-based packet parsing   | `_pending_status_cmd` routes binary responses to parsers   |
| Command serialization          | `asyncio.Lock` + ACK waiting + 300ms throttle              |
| Declarative buttons            | Class attributes `_suffix` + `_coordinator_method`         |
| Round-robin supplemental polls | STATUS_GREASE/DEFAULTS/LED rotate every 5s interval        |
| Python 3.12+ type alias       | `type NovyConfigEntry = ConfigEntry[NovyCoordinator]`      |

## External Dependencies

| Dependency               | Purpose                               |
|--------------------------|---------------------------------------|
| `bleak>=0.21.0`          | Low-level BLE (Bluetooth Low Energy)  |
| `bleak-retry-connector>=3.0.0` | Connection retry + service cache |
| `bluetooth_adapters`     | HA core Bluetooth component           |

## Quick Reference

- **Run validation:** `hacs/action@main` + `home-assistant/actions/hassfest@master` (CI only)
- **Install:** Copy `custom_components/novy_pureline_pro/` to HA config
- **Debug logging:** Set `custom_components.novy_pureline_pro: debug` in HA logger config
- **BLE discovery:** Matches devices with `local_name: "Pureline*"`
- **Min HA version:** 2024.1.0
