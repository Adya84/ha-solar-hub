import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";

async function text(path) {
  return readFile(new URL(`../${path}`, import.meta.url), "utf8");
}

test("manifest is Solar Hub beta", async () => {
  const manifest = JSON.parse(await text("custom_components/solar_hub/manifest.json"));
  assert.equal(manifest.domain, "solar_hub");
  assert.equal(manifest.name, "Solar Hub");
  assert.match(manifest.version, /^\d+\.\d+\.\d+-beta\.\d+$/);
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
  assert.match(provider, /HardwareProfile/);
  for (const key of ["pv_string_count", "battery_count", "controls"]) {
    assert.match(provider, new RegExp(key));
  }
});

test("dashboard has the Solar Hub primary tabs", async () => {
  const ui = await text("custom_components/solar_hub/frontend/solar-hub-panel.js");
  for (const label of ["Overview", "Solar", "Battery", "Grid", "EV", "PredBat", "History", "Settings"]) {
    assert.match(ui, new RegExp(label));
  }
});

test("repository contains no legacy component folder", async () => {
  const components = await readdir(new URL("../custom_components", import.meta.url));
  assert.deepEqual(components, ["solar_hub"]);
});
