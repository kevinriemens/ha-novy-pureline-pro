# ha-novy-pureline-pro Changelog

| Date | Epic | Feature | Summary |
|------|------|---------|---------|
| 2026-08-14 | USER_CHANGE_REQUEST | Fix permanent "unavailable" latch | Entities latched unavailable ~5 min after every connect: the hood stops advertising once connected, so HA's `async_track_unavailable` fired and `set_unavailable()` cleared the flag with nothing to restore it (only `_async_connect()` set it, and the client stayed connected). `set_unavailable()` now ignores the scanner callback while the BLE link is up, and `_on_notification()` self-heals the flag on any inbound traffic. Released as v0.1.1. |
