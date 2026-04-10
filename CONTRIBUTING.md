# Contributing to Novy Pureline Pro

Thanks for your interest in contributing! PRs are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ha-novy-pureline-pro.git
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

1. Copy `custom_components/novy_pureline_pro/` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Enable debug logging by adding to `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.novy_pureline_pro: debug
   ```

## Project Structure

```
custom_components/novy_pureline_pro/
├── __init__.py          # Integration setup and BLE callbacks
├── config_flow.py       # Auto-discovery + manual MAC entry
├── const.py             # Constants, BLE UUIDs, command IDs
├── coordinator.py       # BLE connection manager and packet parser
├── fan.py               # Fan entity (10 speed steps)
├── light.py             # Light entity (brightness + color temp)
├── sensor.py            # 5 diagnostic sensors
├── binary_sensor.py     # Grease filter alert
├── switch.py            # Recirculate mode toggle
├── button.py            # 3 action buttons
├── manifest.json        # Integration metadata
├── strings.json         # English config flow strings
├── translations/        # Localized strings
└── brand/               # Integration icon
```

## BLE Protocol

The BLE protocol is based on the [purelinepro](https://github.com/bwynants/purelinepro) ESPHome C++ implementation by @bwynants. Key details:

- Communication via Nordic UART Service (NUS)
- Commands sent as byte arrays with command ID + payload
- Status updates received as notification packets (IDs 400-404)
- See `const.py` for command/status IDs and `coordinator.py` for packet parsing

## Pull Request Guidelines

- **One feature/fix per PR** — keep changes focused
- **Test on real hardware** if possible (or describe your test setup)
- **Update translations** if you change config flow strings
- **Follow existing code style** — consistent naming, type hints
- **Describe the change** — what and why, not just how

## Reporting Issues

Use the [issue templates](https://github.com/kevinriemens/ha-novy-pureline-pro/issues/new/choose) for bug reports and feature requests. Include your HA version, integration version, and BLE adapter info.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
