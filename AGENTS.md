# Agent guidelines

Home Assistant custom integration for Orange Livebox routers
(`custom_components/livebox`), talking to the router through `aiosysbus`.

## Running checks

```bash
python -m pytest tests -q        # coverage must stay >= 85 %
pre-commit run --all-files       # ruff check/format, codespell, yamllint
```

## Writing tests

### Principle: drive the integration through the `AIOSysbus` mock

Every test goes through the real integration setup, with only the router API
mocked. Prepare the mock, set up the config entry, then assert on what Home
Assistant exposes.

```python
@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_something(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """One sentence describing the expected behaviour."""
    # 1. Arrange: edit the mocked API responses BEFORE setup.
    AIOSysbus.__devices["status"].append({...})

    # 2. Act: real setup, real coordinator, real platforms.
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # 3. Assert: HA states, entity/device registries, or coordinator data.
    state = hass.states.get("device_tracker.test_device")
    assert state is not None
```

Do **not**:

- instantiate `LiveboxDataUpdateCoordinator(...)` or use `object.__new__`;
- build fake coordinators or config entries with `SimpleNamespace`;
- call platform `async_setup_entry` or `async_add_new_*_entities` by hand;
- call coordinator methods (`async_get_devices`, `async_get_topology`, ...)
  directly, or set private attributes such as `_topology_cache`;
- assign `coordinator.data` to inject a state;
- hard-code `Devices.async_get_devices` query expressions in tests.

To test a coordinator method, assert on the key it fills in
`config_entry.runtime_data.data` (`devices`, `reboot_log`, `stats`,
`topology_repeaters`, `count_wireless_devices`, ...). To exercise a second
update, change the mock and call `await coordinator.async_refresh()`
(or `async_request_refresh()` followed by `hass.async_block_till_done()`).

Pure functions that need no coordinator (formatters, value helpers) may be
tested directly.

### Fixtures (`tests/conftest.py`)

| Fixture                              | Purpose                                                                                                                                                                      |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AIOSysbus`                          | Patched `aiosysbus` client. Parametrize indirectly with the model: `"3"`, `"5"`, `"7"` (default), `"7.1"`, `"7.2"`, mapped to `tests/fixtures/Livebox *.json`.               |
| `api_overlay`                        | Partial `api_raw` fixture file loaded on top of the model, e.g. a sanitized issue capture: `@pytest.mark.parametrize("api_overlay", ["issue_191_....json"], indirect=True)`. |
| `reboot_log`                         | Responses of `_auth.post` (`NMC.Reboot.Reboot`, `NMC.Reboot`), editable per test.                                                                                            |
| `config_entry`                       | Registered `MockConfigEntry` with default options.                                                                                                                           |
| `entity_registry_enabled_by_default` | Enables entities created with `entity_registry_enabled_default=False` (per-device sensors, ...). Use with `@pytest.mark.usefixtures`.                                        |

When a test needs the mock active but never reads it, use
`@pytest.mark.usefixtures("AIOSysbus")` instead of an unused argument.

### Shaping the mocked API

- `AIOSysbus.__devices["status"]`: raw device list. `async_get_devices`
  evaluates the expression sent by the coordinator against it
  (`tests/helpers.py::devices_response`), so tags, `.Active==true` and
  `.PhysAddress!=""` behave like on the router.
- `AIOSysbus.api_raw[...]`: every raw response, keyed like the fixture files.
  Mutate it **in place, before setup**: most mocks hold references to these
  objects, so replacing a top-level key has no effect after the fixture ran.
- `AIOSysbus.<service>.<method>.return_value = {...}`: replace a single response.
  To change only some calls, wrap the existing `side_effect` rather than
  dropping it.
- Options: `hass.config_entries.async_update_entry(config_entry, options={**config_entry.options, CONF_LAN_TRACKING: True})`
  before setup.

### Fixture files (`tests/fixtures/`)

- `Livebox *.json`: full `{"api_raw": {...}}` captures per model.
- `issue_<n>_*_sanitized.json`: captures from bug reports. Prefer a partial
  `api_raw` holding only the responses needed (used through `api_overlay`).
  When only a diagnostics dump exists, rebuild the raw responses from it in
  the test instead of injecting coordinator data.
- Load files with `tests/helpers.py::load_fixture` / `load_api_fixture`, never
  redefine a local loader.
- Sanitize captures: fake but **distinct** MAC addresses / keys
  (`AA:AA:AA:AA:AA:01`, ...). Identical redacted keys make the coordinator
  merge devices and hide bugs (all keys in `Livebox 7.json` are
  `**REDACTED**`: give a device its own key when a test targets it).

### Assertions

- Look up entities through the registry rather than guessing entity ids when
  the id depends on the serial number:
  `er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{unique_id}_{key}")`.
- Devices: `dr.async_get(hass).async_get_device_by_identifier((DOMAIN, key), config_entry.entry_id)`.
  `async_get_device(identifiers=...)` is deprecated and raises in tests.
- Sensor states are in the suggested unit (bytes are shown in MB, ...).

### Shared helpers

Shared non-fixture code goes in `tests/helpers.py` and is imported with
`from .helpers import ...`. Never import from `conftest.py`.
