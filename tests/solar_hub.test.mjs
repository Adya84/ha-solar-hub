import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";

async function text(path) {
  return readFile(new URL(`../${path}`, import.meta.url), "utf8");
}

test("manifest is the current stable Solar Hub release", async () => {
  const manifest = JSON.parse(await text("custom_components/solar_hub/manifest.json"));
  assert.equal(manifest.domain, "solar_hub");
  assert.equal(manifest.name, "Solar Hub");
  assert.equal(manifest.version, "0.0.4-beta.5");
});

test("release workflow supports normal stable releases", async () => {
  const workflow = await text(".github/workflows/release.yml");
  assert.match(workflow, /Publish release/);
  assert.match(workflow, /if \[\[ "\$VERSION" == \*-\* \]\]/);
});

test("normal setup asks only for inverter IP", async () => {
  const flow = await text("custom_components/solar_hub/config_flow.py");
  assert.match(flow, /vol\.Required\(CONF_HOST\)/);
  assert.doesNotMatch(flow, /vol\.Required\(CONF_PORT\)/);
  assert.match(flow, /DEFAULT_PORT/);
  assert.match(flow, /async_scan/);
});

test("provider architecture is separate from the dashboard", async () => {
  const base = await text("custom_components/solar_hub/providers/base.py");
  const provider = await text("custom_components/solar_hub/providers/givenergy.py");
  assert.match(base, /class SolarProvider/);
  assert.match(provider, /from givenergy_modbus\.client\.client import Client/);
  assert.match(provider, /HardwareProfile/);
  for (const key of ["pv_string_count", "battery_count", "controls"]) {
    assert.match(provider, new RegExp(key));
  }
  assert.match(base, /async def async_deep_scan/);
  assert.match(base, /async def async_set_control/);
  assert.match(provider, /async def async_deep_scan/);
  assert.match(provider, /async def async_set_control/);
});

test("a completed hardware scan survives Home Assistant restarts", async () => {
  const setup = await text("custom_components/solar_hub/__init__.py");
  const coordinator = await text("custom_components/solar_hub/coordinator.py");
  assert.match(setup, /Store\(hass, 1, f"\{DOMAIN\}\.\{entry\.entry_id\}"\)/);
  assert.match(setup, /cached_snapshot = await store\.async_load\(\)/);
  assert.match(setup, /coordinator\.async_restore_snapshot\(cached_snapshot\)/);
  assert.match(setup, /hass\.async_create_task\(coordinator\.async_request_refresh\(\)\)/);
  assert.match(coordinator, /def async_restore_snapshot/);
  assert.match(coordinator, /async_delay_save/);
});

test("Solar Hub keeps deep scans separate from live refreshes", async () => {
  const coordinator = await text("custom_components/solar_hub/coordinator.py");
  const provider = await text("custom_components/solar_hub/providers/givenergy.py");
  assert.match(coordinator, /async def async_deep_scan/);
  assert.match(coordinator, /"state": "failed"/);
  assert.match(coordinator, /asyncio\.wait_for\(self\.provider\.async_deep_scan\(report\), timeout=120\)/);
  assert.match(coordinator, /"progress": progress/);
  const deepScan = provider.slice(provider.indexOf("async def async_deep_scan"), provider.indexOf("async def async_set_control"));
  assert.match(deepScan, /await self\._client\.load_config\(timeout=5\.0, retries=1, retry_delay=0\.75\)/);
  assert.match(deepScan, /await self\._client\.refresh\(timeout=5\.0, retries=1, retry_delay=0\.75\)/);
  assert.match(provider, /f"v_cell_\{cell:02d\}"/);
});

test("dashboard can trigger its optional deep scan", async () => {
  const websocket = await text("custom_components/solar_hub/websocket.py");
  const constants = await text("custom_components/solar_hub/const.py");
  assert.match(constants, /WS_DEEP_SCAN = "solar_hub\/deep_scan"/);
  assert.match(websocket, /WS_DEEP_SCAN/);
  assert.match(websocket, /async_deep_scan\(\)/);
});

test("PredBat snapshot exposes a dashboard-friendly plan payload", async () => {
  const predbat = await text("custom_components/solar_hub/predbat.py");
  assert.match(predbat, /"current_action"/);
  assert.match(predbat, /"plan_segments"/);
});

test("dashboard has the Solar Hub primary tabs", async () => {
  const ui = await text("custom_components/solar_hub/frontend/solar-hub-panel.js");
  for (const label of ["Overview", "Solar", "Battery", "Grid", "EV", "PredBat", "History", "Settings"]) {
    assert.match(ui, new RegExp(label));
  }
  assert.match(ui, /_predbatTimeline\(/);
  assert.match(ui, /NEXT 24 HOURS/);
  assert.match(ui, /Deep Modbus scan/);
  assert.match(ui, /takes up to two minutes/);
  assert.match(ui, /scan-progress/);
  assert.match(ui, /battery-section/);
  assert.match(ui, /Battery \$\{index\} cells/);
  assert.match(ui, /metric\.unit === "kWh"/);
  assert.match(ui, /toFixed\(1\)/);
});

test("repository contains no legacy component folder", async () => {
  const components = await readdir(new URL("../custom_components", import.meta.url));
  assert.deepEqual(components, ["solar_hub"]);
});
