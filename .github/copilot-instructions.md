# AFIRE Fireplace (`custom_components/afire`) Copilot Instructions

## 1) What this integration is
- Home Assistant custom integration for AFIRE water vapor fireplaces.
- Cloud polling integration using Gizwits API (`iot_class: cloud_polling`).
- Major components:
  - `__init__.py`: config entry setup/unload, coordinator creation.
  - `afire_api.py`: REST adapter wrapping `requests` with login, device discovery, status, control.
  - `coordinator.py`: `DataUpdateCoordinator`, 30s polling, refreshes statuses in parallel.
  - `switch.py`, `number.py`, `light.py`: entities exposed to HA, map `attrs` keys to controls.
  - `config_flow.py`: credential flow + option reconfigure.

## 2) Structure and data flow
- `AfireConfigFlow` -> create config entry (`username/password`).
- `async_setup_entry`: login + first refresh and then `async_forward_entry_setups` to platforms.
- `AfireCoordinator._async_update_data`: `api.get_devices`, then `api.get_status` for each DID via `asyncio.gather`.
- Entities read from `coordinator.data[did]["attrs"]`.
- User actions call `api.set_attr(did, { .. })`, update local coordinator cache, then `async_request_refresh`.

## 3) Behaviors and project business rules
- Strict mode in entities: non-power controls are blocked if `POWERSW` is off (e.g., in `AfireSwitch.async_turn_on` and `AfireNumber.async_set_native_value` and `AfireColorLight.async_turn_on`).
- Color/entity mapping is fixed via constants:
  - `SUPPORTED_SWITCHES`: `POWERSW`, `COLOR_SW`, `LED_SW`
  - `SUPPORTED_NUMBERS`: `FLAME`, `SPEED` (0..5)
  - `COLOR_PRESETS`/`EFFECT_ONLY` in `light.py` maps effects to API keys.
- Unique IDs use `f"{did.lower()}_{key.lower()}"` for switches/numbers; `f"{did.lower()}_color"` for light.

## 4) API details
- Base URL: `https://api.gizwits.com/app`
- Headers require `X-Gizwits-Application-Id` (constant `DEFAULT_APPID`) and `X-Gizwits-User-token`.
- `get_devices` hits `/bindings`; each device has `did`, `product_key`, etc.
- `get_status` hits `/devdata/{did}/latest`; control hits `/control/{did}` with `{"attrs": {...}}`.
- Token refresh via `ensure_token` (re-login when expired or absent).

## 5) Development and debugging pointers
- There are no unit tests in this repo; use manual HA integration tests.
- `manifest.json` declares `requests>=2.31.0`.
- To debug, watch HA logs and `logger` outputs from module (e.g., "AFIRE update error" or "AFIRE auth failed").
- Update interval is `UPDATE_INTERVAL = 30` in `const.py`, intended for cloud poll frequency.

## 6) Repair/extension patterns
- Keep `coordinator` as source of truth for entity states; do not store independent state.
- For new attributes, add to `SUPPORTED_*` maps and keyed checks in entities only when attribute exists.
- Preserve existing behavior in `async_set_native_value` / `async_turn_on` by gating with `is_fireplace_on`.

## 7) Quick file map
- `custom_components/afire/__init__.py`
- `custom_components/afire/config_flow.py`
- `custom_components/afire/afire_api.py`
- `custom_components/afire/coordinator.py`
- `custom_components/afire/switch.py`
- `custom_components/afire/number.py`
- `custom_components/afire/light.py`
- `custom_components/afire/manifest.json`

---

> Feedback request: Is there any part of the appliance flow (`AfireCoordinator` lock/unlock, `set_attr` semantics, strict mode) that is unclear in this set of instructions? If you'd like, I can add a brief "common bug fix" section next.