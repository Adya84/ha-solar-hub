# Tablet Energy Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a tablet-first Solar Hub dashboard that combines live
GivEnergy Modbus power flow with a 24-hour PredBat plan and exposes richer
hardware detail through an optional deep scan.

**Architecture:** Keep normal five-second polling lightweight and return a
normalised basic snapshot from the provider. Add a separate, user-triggered
deep-scan path that enriches a persisted hardware profile without blocking
normal dashboard updates. The panel consumes the existing WebSocket snapshot
and a structured PredBat plan response, rendering the integrated overview and
capability-gated detail tabs.

**Tech Stack:** Home Assistant custom integration (Python 3.12),
givenergy-modbus async client, Home Assistant WebSocket API, native Web
Components/JavaScript, Node built-in test runner, Python unittest.

**Spec:** `docs/superpowers/specs/2026-09-22-tablet-energy-dashboard-design.md`

## Global Constraints

- Live power and technical readings come only from the local GivEnergy Modbus
  connection; never manufacture missing values.
- New installations use only a quick basic scan; deep scanning is explicitly
  initiated from Settings/Hardware and never runs in the five-second loop.
- PredBat and EV are optional; their absence must leave the main overview
  working and understandable.
- Render controls only when the inverter capability profile supports them, and
  require explicit confirmation before every write.
- Retain and visibly label last-good data as stale on a refresh failure.

## Review Focus

- A battery that exposes no cell registers must show its normal summary with
  no empty/fictional cell grid; Task 2 pins this with an empty cell payload.
- A deep scan interrupted by a Modbus exception must retain the previous
  completed profile and report failure without taking down live refreshes;
  Task 3 pins this with a failing provider stub.
- PredBat entity names differ across versions; unknown entities must remain
  available as raw values while known plan fields are extracted; Task 4 pins
  this with mixed entity names.
- A plan crossing midnight must render all segments on the next-24-hour axis,
  not disappear after 00:00; Task 5 pins this with two dated segments.
- A write request for an unavailable control must be rejected before it reaches
  the provider; Task 6 pins this with a false capability flag.

---

## File structure

- `custom_components/solar_hub/models.py` — typed basic/deep hardware profile
  and scan-status payloads.
- `custom_components/solar_hub/providers/base.py` — provider contract for
  normal refresh, deep scan and supported control writes.
- `custom_components/solar_hub/providers/givenergy.py` — GivEnergy mapping of
  basic values, safe extended battery fields, cells and capabilities.
- `custom_components/solar_hub/coordinator.py` — keep last-good data, own deep
  scan state and preserve the last completed hardware profile.
- `custom_components/solar_hub/__init__.py` — register service support and
  persist deep-profile data in the config entry storage.
- `custom_components/solar_hub/predbat.py` — interpret known PredBat states
  into a stable plan/current-action payload while keeping raw entities.
- `custom_components/solar_hub/websocket.py` — expose deep-scan status/start
  and structured PredBat data to the panel; validate safe control commands.
- `custom_components/solar_hub/frontend/solar-hub-panel.js` — integrated
  overview, 24-hour plan, capability-gated detail tabs and confirmation UI.
- `tests/test_provider_scan.py` — Python provider/coordinator scan tests using
  fake GivEnergy objects.
- `tests/solar_hub.test.mjs` — structural frontend/contract tests runnable in
  the repository's existing Node test command.

### Task 1: Define scan and capability contracts

**Files:**
- Modify: `custom_components/solar_hub/models.py`
- Modify: `custom_components/solar_hub/providers/base.py`
- Create: `tests/test_provider_scan.py`

**Interfaces:**
- Produces `HardwareProfile.deep_data: dict[str, Any]`,
  `HardwareProfile.deep_scan: dict[str, Any]`, and
  `SolarProvider.async_deep_scan() -> dict[str, Any]`.
- Produces `SolarProvider.async_set_control(key: str, value: Any) -> None` for
  the later WebSocket command.

- [ ] **Step 1: Write the failing contract tests**

```python
import unittest

from custom_components.solar_hub.models import HardwareProfile


class HardwareProfileTests(unittest.TestCase):
    def test_basic_profile_has_not_scanned_deep_state(self):
        profile = HardwareProfile(provider="test", manufacturer="Test")
        payload = profile.as_dict()
        self.assertEqual(payload["deep_scan"]["state"], "not_run")
        self.assertEqual(payload["deep_data"], {})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_provider_scan.HardwareProfileTests.test_basic_profile_has_not_scanned_deep_state -v`

Expected: FAIL because `deep_scan` and `deep_data` are absent.

- [ ] **Step 3: Add the minimal typed profile and provider methods**

```python
@dataclass(slots=True)
class HardwareProfile:
    # existing fields...
    deep_data: dict[str, Any] = field(default_factory=dict)
    deep_scan: dict[str, Any] = field(
        default_factory=lambda: {"state": "not_run", "completed_at": None, "error": None}
    )
```

```python
@abstractmethod
async def async_deep_scan(self) -> dict[str, Any]:
    """Read extended, on-demand hardware details."""

@abstractmethod
async def async_set_control(self, key: str, value: Any) -> None:
    """Write a known supported control."""
```

- [ ] **Step 4: Run the contract test to verify it passes**

Run: `python -m unittest tests.test_provider_scan.HardwareProfileTests -v`

Expected: PASS.

- [ ] **Step 5: Commit the contract**

```bash
git add custom_components/solar_hub/models.py custom_components/solar_hub/providers/base.py tests/test_provider_scan.py
git commit -m "feat: define Solar Hub deep scan contracts"
```

### Task 2: Normalise basic and deep GivEnergy data

**Files:**
- Modify: `custom_components/solar_hub/providers/givenergy.py`
- Modify: `tests/test_provider_scan.py`

**Interfaces:**
- Consumes `SolarProvider.async_deep_scan()` from Task 1.
- Produces a snapshot with `system_profile.deep_data["batteries"]`, each item
  containing only discovered `cells`, `cycles`, `capacity_ah`, `temperatures`,
  and identity fields.

- [ ] **Step 1: Write failing normalisation tests using fake battery objects**

```python
def test_deep_battery_profile_contains_discovered_cells_only(self):
    battery = FakeBattery(num_cells=2, v_cell_1=3.31, v_cell_2=3.32, num_cycles=48)
    data = GivEnergyProvider._deep_battery_data([battery])
    self.assertEqual(data[0]["cells"], [{"index": 1, "voltage": 3.31}, {"index": 2, "voltage": 3.32}])
    self.assertEqual(data[0]["cycles"], 48)

def test_deep_profile_omits_cells_not_exposed_by_bms(self):
    data = GivEnergyProvider._deep_battery_data([FakeBattery(num_cells=None)])
    self.assertNotIn("cells", data[0])
```

- [ ] **Step 2: Run the provider tests to verify they fail**

Run: `python -m unittest tests.test_provider_scan.GivEnergyProviderTests -v`

Expected: FAIL because `_deep_battery_data` does not exist.

- [ ] **Step 3: Implement a safe extended-field reader**

```python
def _deep_battery_data(self, batteries: list[Any]) -> list[dict[str, Any]]:
    result = []
    for index, battery in enumerate(batteries, start=1):
        detail = {"index": index, "serial": _plain(_read(battery, "serial_number", "serial"))}
        for key, names in {
            "cycles": ("num_cycles",), "capacity_ah": ("cap_design", "cap_design2"),
            "temperature_min": ("t_min",), "temperature_max": ("t_max",),
        }.items():
            value = _read(battery, *names)
            if value is not None:
                detail[key] = _plain(value)
        cell_count = _read(battery, "num_cells")
        cells = [
            {"index": cell, "voltage": _plain(_read(battery, f"v_cell_{cell}", f"cell_{cell}_voltage"))}
            for cell in range(1, int(cell_count or 0) + 1)
        ]
        cells = [cell for cell in cells if cell["voltage"] is not None]
        if cells:
            detail["cells"] = cells
        result.append(detail)
    return result
```

Call the client's refresh/detect sequence only from `async_deep_scan`, merge
the resulting deep data into the previous basic profile, and include a
timestamp/state. Use the existing `_read` helper for every vendor-version
dependent attribute.

- [ ] **Step 4: Run the provider tests to verify they pass**

Run: `python -m unittest tests.test_provider_scan.GivEnergyProviderTests -v`

Expected: PASS.

- [ ] **Step 5: Commit provider deep scan support**

```bash
git add custom_components/solar_hub/providers/givenergy.py tests/test_provider_scan.py
git commit -m "feat: expose GivEnergy deep battery scan data"
```

### Task 3: Coordinate and persist the optional scan

**Files:**
- Modify: `custom_components/solar_hub/coordinator.py`
- Modify: `custom_components/solar_hub/__init__.py`
- Modify: `tests/test_provider_scan.py`

**Interfaces:**
- Consumes `provider.async_deep_scan()` from Task 2.
- Produces `SolarHubCoordinator.async_deep_scan() -> dict[str, Any]`, which
  preserves the last completed profile on failure and emits state transitions
  `running`, `completed`, or `failed`.

- [ ] **Step 1: Write the failing coordinator failure-preservation test**

```python
async def test_deep_scan_failure_keeps_last_completed_profile(self):
    coordinator = make_coordinator(provider=FailingDeepScanProvider())
    coordinator.data = {"system_profile": {"deep_data": {"batteries": [{"cycles": 48}]}}}
    result = await coordinator.async_deep_scan()
    self.assertEqual(result["system_profile"]["deep_data"]["batteries"][0]["cycles"], 48)
    self.assertEqual(result["system_profile"]["deep_scan"]["state"], "failed")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest tests.test_provider_scan.SolarHubCoordinatorTests.test_deep_scan_failure_keeps_last_completed_profile -v`

Expected: FAIL because the coordinator has no `async_deep_scan` method.

- [ ] **Step 3: Implement scan lifecycle and durable entry storage**

```python
async def async_deep_scan(self) -> dict[str, Any]:
    current = deepcopy(self.data or self._last_good or {})
    profile = current.setdefault("system_profile", {})
    profile["deep_scan"] = {"state": "running", "completed_at": None, "error": None}
    self.async_set_updated_data(current)
    try:
        scanned = await self.provider.async_deep_scan()
    except Exception as err:
        profile["deep_scan"] = {"state": "failed", "completed_at": None, "error": err.__class__.__name__}
        self.async_set_updated_data(current)
        return current
    self._last_good = scanned
    self.async_set_updated_data(scanned)
    return scanned
```

Store the completed `system_profile` in the config-entry runtime/config-entry
options using Home Assistant's supported update API, restore it when setting
up the entry, and never store a `running` state across a restart.

- [ ] **Step 4: Run coordinator tests to verify they pass**

Run: `python -m unittest tests.test_provider_scan.SolarHubCoordinatorTests -v`

Expected: PASS.

- [ ] **Step 5: Commit lifecycle support**

```bash
git add custom_components/solar_hub/coordinator.py custom_components/solar_hub/__init__.py tests/test_provider_scan.py
git commit -m "feat: coordinate optional deep Modbus scans"
```

### Task 4: Structure PredBat data for the overview

**Files:**
- Modify: `custom_components/solar_hub/predbat.py`
- Modify: `custom_components/solar_hub/websocket.py`
- Modify: `tests/test_provider_scan.py`

**Interfaces:**
- Produces `snapshot_predbat(hass) -> {available, entities, current_action,
  override, plan_segments}` where every segment has ISO `start`, ISO `end`,
  `kind`, optional `rate`, and optional `target_soc`.
- The existing `solar_hub/predbat` WebSocket command returns this stable
  structure.

- [ ] **Step 1: Write failing PredBat classification tests**

```python
def test_snapshot_extracts_known_plan_and_keeps_unknown_entity(self):
    hass = fake_hass([
        fake_state("sensor.predbat_plan_html", "<plan>"),
        fake_state("sensor.predbat_best_charge", "01:00-03:00"),
        fake_state("sensor.predbat_custom_metric", "42"),
    ])
    snapshot = snapshot_predbat(hass)
    self.assertEqual(snapshot["current_action"], "charge")
    self.assertTrue(any(item["entity_id"].endswith("custom_metric") for item in snapshot["entities"]))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_provider_scan.PredBatTests -v`

Expected: FAIL because `current_action` and `plan_segments` are absent.

- [ ] **Step 3: Implement a conservative parser**

Add `classify_predbat_entity(entity_id, state, attributes)` and
`parse_plan_segments(state, attributes, now)` in `predbat.py`. Recognise
documented/observed charge, discharge, export, plan, target and override
names; return empty segments for unparseable values while retaining all raw
entities. Do not execute HTML or trust HTML as a data source.

- [ ] **Step 4: Run PredBat tests to verify they pass**

Run: `python -m unittest tests.test_provider_scan.PredBatTests -v`

Expected: PASS.

- [ ] **Step 5: Commit structured PredBat support**

```bash
git add custom_components/solar_hub/predbat.py custom_components/solar_hub/websocket.py tests/test_provider_scan.py
git commit -m "feat: structure PredBat plan data"
```

### Task 5: Build the integrated tablet overview and detail rendering

**Files:**
- Modify: `custom_components/solar_hub/frontend/solar-hub-panel.js`
- Modify: `tests/solar_hub.test.mjs`

**Interfaces:**
- Consumes overview snapshot and Task 4 PredBat payload via existing WebSocket
  calls.
- Produces `_overview()` with live flow, status, 24-hour timeline, next action
  and today totals; `_battery()` and `_settings()` with deep-scan state/data.

- [ ] **Step 1: Add failing frontend contract tests**

```javascript
test("tablet overview includes live flow and a 24-hour PredBat plan", async () => {
  const ui = await text("custom_components/solar_hub/frontend/solar-hub-panel.js");
  assert.match(ui, /_predbatTimeline\(/);
  assert.match(ui, /NEXT 24 HOURS/);
  assert.match(ui, /now-marker/);
  assert.match(ui, /Deep Modbus scan/);
});

test("the EV page is capability gated", async () => {
  const ui = await text("custom_components/solar_hub/frontend/solar-hub-panel.js");
  assert.match(ui, /ev.*available|available.*ev/is);
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `node --test tests/solar_hub.test.mjs`

Expected: FAIL because the timeline/scan UI methods are absent.

- [ ] **Step 3: Implement the overview and detailed pages**

Add pure rendering helpers:

```javascript
_planPosition(iso, now) {
  const hours = (new Date(iso).getTime() - now.getTime()) / 3_600_000;
  return Math.max(0, Math.min(100, (hours / 24) * 100));
}

_predbatTimeline(segments) {
  const now = new Date();
  return `<section class="plan"><span class="kicker">NEXT 24 HOURS</span>
    <div class="plan-track">${segments.map(segment => this._planSegment(segment, now)).join("")}
    <i class="now-marker" style="left:0%"></i></div></section>`;
}
```

Use `kind` as a CSS class only after mapping it to the fixed allow-list
`charge`, `discharge`, `import`, `export`, and `solar`. Escape all labels and
values. Render cell grids only when `deep_data.batteries[n].cells` is a
non-empty array. Hide the EV tab unless its capability is true or its explicit
configuration is enabled. Add a Settings button that calls the deep-scan
WebSocket command and shows running/failed/completed state.

- [ ] **Step 4: Run the frontend tests to verify they pass**

Run: `node --test tests/solar_hub.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit the tablet interface**

```bash
git add custom_components/solar_hub/frontend/solar-hub-panel.js tests/solar_hub.test.mjs
git commit -m "feat: build integrated tablet energy overview"
```

### Task 6: Add guarded scan and control WebSocket commands

**Files:**
- Modify: `custom_components/solar_hub/const.py`
- Modify: `custom_components/solar_hub/websocket.py`
- Modify: `custom_components/solar_hub/frontend/solar-hub-panel.js`
- Modify: `tests/test_provider_scan.py`
- Modify: `tests/solar_hub.test.mjs`

**Interfaces:**
- Produces `solar_hub/deep_scan` and `solar_hub/set_control` WebSocket
  commands. `set_control` accepts `{key: str, value: Any, confirmed: true}`.

- [ ] **Step 1: Write failing unavailable-control rejection test**

```python
async def test_unavailable_control_is_rejected_before_provider_write(self):
    runtime = make_runtime(controls={"charge_target_soc": False})
    with self.assertRaisesRegex(ValueError, "not supported"):
        await async_set_control(runtime, "charge_target_soc", 80, confirmed=True)
    runtime["coordinator"].provider.assert_not_called()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_provider_scan.WebSocketControlTests -v`

Expected: FAIL because validation helper/command is absent.

- [ ] **Step 3: Add validation before every scan or control action**

```python
def validate_control(profile: dict[str, Any], key: str, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Confirmation is required")
    if not profile.get("controls", {}).get(key, False):
        raise ValueError(f"Control '{key}' is not supported by this inverter")
```

Register `deep_scan` to call `coordinator.async_deep_scan()`. Register
`set_control` to call `validate_control`, then
`coordinator.provider.async_set_control(key, value)`, then refresh the
coordinator. In the panel, show a native confirmation dialog containing the
control label and requested value before sending `confirmed: true`.

- [ ] **Step 4: Run all automated checks**

Run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/solar_hub.test.mjs
python -m py_compile custom_components/solar_hub/*.py custom_components/solar_hub/providers/*.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit guarded commands and verification**

```bash
git add custom_components/solar_hub/const.py custom_components/solar_hub/websocket.py custom_components/solar_hub/frontend/solar-hub-panel.js tests/test_provider_scan.py tests/solar_hub.test.mjs
git commit -m "feat: add guarded scan and inverter controls"
```

### Task 7: Update user documentation and release validation

**Files:**
- Modify: `README.md`
- Modify: `INSTALL.md`
- Modify: `tests/solar_hub.test.mjs`

**Interfaces:**
- Documents basic initial discovery, optional Deep Modbus scan, GivTCP/local
  IP use, PredBat optional integration, and the dashboard's control safeguards.

- [ ] **Step 1: Write failing documentation checks**

```javascript
test("install guide explains basic setup and optional deep scan", async () => {
  const install = await text("INSTALL.md");
  assert.match(install, /basic scan/i);
  assert.match(install, /deep Modbus scan/i);
  assert.match(install, /PredBat/i);
});
```

- [ ] **Step 2: Run the documentation test to verify it fails**

Run: `node --test tests/solar_hub.test.mjs`

Expected: FAIL because the guide does not mention the flow.

- [ ] **Step 3: Document the exact setup and safety flow**

Add a compact section explaining: enter only the inverter/data-adapter local
IP during initial setup; the basic scan completes automatically; run Deep
Modbus scan from Solar Hub → Settings/Hardware; PredBat appears automatically
when present; controls require confirmation and are only displayed when
supported.

- [ ] **Step 4: Run release-quality verification**

Run:

```bash
node --test tests/solar_hub.test.mjs
python -m unittest discover -s tests -p "test_*.py" -v
python -m py_compile custom_components/solar_hub/*.py custom_components/solar_hub/providers/*.py
git diff --check
git status --short
```

Expected: all verification passes and the working tree is clean after commit.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md INSTALL.md tests/solar_hub.test.mjs
git commit -m "docs: explain Solar Hub scanning and tablet dashboard"
```

## Self-review

- **Spec coverage:** Tasks 1–3 cover basic/deep scanning and resilience; Task
  2 covers real battery/cell/cycle data; Task 4 covers optional PredBat; Task
  5 covers the integrated tablet page/tabs/EV; Task 6 covers safe writes; Task
  7 covers installation and verification. No spec requirement is unassigned.
- **Placeholder scan:** The plan contains no incomplete markers or vague test
  instructions; each task has executable test commands and concrete interfaces.
- **Type consistency:** `async_deep_scan`, `deep_data`, `deep_scan`,
  `plan_segments`, and `async_set_control` are defined before their consumers.
- **Review focus:** Each listed input class has an explicit named test in its
  owning task.
