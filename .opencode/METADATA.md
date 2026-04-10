# Project: ha-novy-pureline-pro

**Initialized:** 2026-04-10

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `screenshot_tests_enabled` | `false` | No frontend UI to validate |

## Tech Stack

| Type | Technology | Version |
|------|------------|---------|
| Language | Python | 3.12+ |
| Platform | Home Assistant | 2024.1.0+ |
| Integration Type | Custom Component | HACS-compatible |
| BLE Library | bleak | >=0.21.0 |
| BLE Retry | bleak-retry-connector | >=3.0.0 |
| CI | GitHub Actions | HACS + Hassfest validation |

## Architecture

### System Overview

Home Assistant custom integration for **Novy Pureline Pro** kitchen hoods via Bluetooth LE. Uses Nordic UART Service (NUS) for bidirectional BLE communication. Implements the DataUpdateCoordinator pattern with notification-driven updates and 5-second polling fallback.

**11 entities:** 1 fan, 1 light, 5 sensors, 1 binary sensor, 1 switch, 3 buttons.

### Project Structure

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
├── translations/        # en.json, nl.json
└── brand/               # Integration icon
```

### Layer Architecture

```
┌─────────────────────────────────────────┐
│  Home Assistant Core                     │
│  (Config Entries, Device Registry, UI)   │
├─────────────────────────────────────────┤
│  Entity Platforms                        │
│  fan / light / sensor / binary_sensor    │
│  switch / button                         │
├─────────────────────────────────────────┤
│  NovyCoordinator (coordinator.py)        │
│  - DataUpdateCoordinator subclass        │
│  - BLE connection + command serialization│
│  - Packet parsing (context-based)        │
│  - NovyState dataclass                   │
├─────────────────────────────────────────┤
│  BLE Transport (bleak + retry-connector) │
│  Nordic UART Service (NUS)               │
└─────────────────────────────────────────┘
```

### Where to Put New Code

| I need to create...              | File                    | Pattern                          |
|----------------------------------|-------------------------|----------------------------------|
| New entity platform              | `{platform}.py`         | `NovyBaseEntity` + platform base |
| New BLE command                  | `coordinator.py`        | `async def {action}()` method    |
| New status parser                | `coordinator.py`        | `_parse_status_{name}()` method  |
| New command ID / constant        | `const.py`              | Add to constant group            |
| New state field                  | `coordinator.py`        | Add to `NovyState` dataclass     |
| Config flow change               | `config_flow.py`        | Extend step methods              |
| New translation                  | `translations/{lang}.json` | Follow existing structure     |

### Key Patterns

| Pattern | Usage |
|---------|-------|
| DataUpdateCoordinator | Central state manager with polling + notification updates |
| NovyBaseEntity | Shared base with safe `_state` accessor and cached DeviceInfo |
| Context-based packet parsing | `_pending_status_cmd` routes binary responses to parsers |
| Command serialization | `asyncio.Lock` + ACK waiting + 300ms throttle |
| Declarative buttons | Class attributes `_suffix` + `_coordinator_method` |
| Round-robin supplemental polls | STATUS_GREASE/DEFAULTS/LED rotate every 5s |
| Python 3.12+ type alias | `type NovyConfigEntry = ConfigEntry[NovyCoordinator]` |

### BLE Protocol

- **Service:** Nordic UART Service (NUS)
- **Command format:** ASCII `[cmd_id;arg1;arg2;...]` encoded as UTF-8
- **Response:** Binary packets, context-based parsing (no ID in payload)
- **Constraints:** 300ms command throttle, 15s ACK timeout, asyncio.Lock serialization

### Quick Reference

- **Install:** Copy `custom_components/novy_pureline_pro/` to HA config dir
- **Debug:** Set `custom_components.novy_pureline_pro: debug` in HA logger
- **CI:** HACS validation + Hassfest (GitHub Actions)
- **BLE discovery:** Matches `local_name: "Pureline*"`

## Notes

- BLE protocol based on [purelinepro](https://github.com/bwynants/purelinepro) C++ ESPHome component
- ESPHome Bluetooth Proxy **not supported** — requires direct BLE connection
- No unit tests currently — relies on real hardware testing
- HACS custom repository (not default)
- Countries: NL, BE
