# Tablet energy dashboard design

## Purpose

Solar Hub will provide the primary, always-on Home Assistant dashboard for a
house tablet. It combines live local GivEnergy inverter data with PredBat's
forward plan, while retaining detailed technical views and safe controls.

The dashboard must be useful at a glance, must never invent hardware or
readings, and must work when PredBat is not installed.

## Sources of truth

### Live inverter data

The GivEnergy provider connects directly to the inverter/data adapter using
local Modbus TCP. Its normal refresh supplies the live power-flow view,
standard energy readings, grid values, basic battery information, and the
controls supported by the detected inverter.

### PredBat data

PredBat remains optional. When its Home Assistant entities are available,
Solar Hub uses them for the current action, current tariff decision, plan,
target levels, and manual-override state. Solar Hub does not recreate or
second-guess PredBat's scheduling decisions.

## Setup and scanning

### Basic scan

New installations run a quick basic scan so the main dashboard becomes usable
immediately. It detects the inverter identity, number of batteries, regular
live measurements, and the supported essential controls.

### Deep Modbus scan

The Settings/Hardware tab offers a user-initiated **Deep Modbus scan**. It is
not part of normal refreshes. It reads safely available extended data and
persists a hardware profile containing, where supplied by the inverter:

- battery module serials, BMS firmware, capacity, state and cycle count;
- cell count, individual cell voltage and temperature measurements;
- PV strings and their electrical values;
- inverter model, firmware and device capabilities;
- readable registers and available controls.

The interface shows scan progress, the outcome, and the last successful scan
time. Detailed pages show basic data before a deep scan and enrich themselves
after it. Unsupported values are hidden rather than represented with made-up
data.

## Main overview

The tablet-first Overview is one integrated screen with these areas:

1. **Live status bar** — connection health, current PredBat mode, tariff
   decision, and any active manual override.
2. **Energy-flow centrepiece** — live solar, home, battery, grid and optional
   EV flow. Values and flow direction reflect the current Modbus snapshot.
3. **24-hour PredBat plan** — a full next-24-hours timeline with a prominent
   now marker. Charge/solar windows are green, battery discharge is blue,
   grid import is amber, and export is purple. It states the next action in
   plain language and shows targets/rates when available.
4. **Today's totals and alerts** — generation, consumption, import, export,
   battery charge/discharge, stale-data warnings, and scan/connection errors.

If PredBat is absent, the plan space explains that it is not connected while
the live energy-flow dashboard remains fully operational.

## Detail tabs

- **Battery:** bank summary, each battery/BMS, capacity, cycles, temperature,
  health/status, and per-cell data following a deep scan.
- **Inverter:** identity, firmware, detected Modbus capabilities, PV inputs,
  grid readings, registers, and device state.
- **Solar:** production, PV string readings, and daily/lifetime generation.
- **Grid:** import/export, voltage, frequency, and energy totals.
- **EV:** displayed only if an EV/charger is detected or deliberately enabled.
- **Controls:** only controls confirmed by the basic/deep capability scan;
  includes explicit confirmation before a write.
- **Settings/Hardware:** connection information, basic scan result and the
  on-demand Deep Modbus scan.

## Resilience and safety

- Normal data polling stays lightweight; the exhaustive scan never runs on a
  five-second dashboard cycle.
- If a refresh fails, retain the last good snapshot and label it stale with a
  useful error state.
- No dashboard control is displayed unless the inverter reports it as
  supported. Writes require confirmation and use the provider's supported
  Modbus operation.
- Optional EV and PredBat content never blocks the main dashboard.

## Verification

Implementation must include tests for basic versus deep scan profiles,
available/unavailable cell data, optional PredBat plan states, optional EV,
stale connection behaviour, and dashboard rendering of the 24-hour timeline.
