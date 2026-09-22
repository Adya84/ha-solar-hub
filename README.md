# Solar Hub

Solar Hub is a clean, tablet-first Home Assistant integration for solar, battery, grid, EV and energy-planning data.

## Current release

`0.0.1`

## First provider

The first supported provider connects directly to supported GivEnergy hardware over local Modbus.

Setup is intentionally simple:

1. Install Solar Hub.
2. Add the integration.
3. Enter the inverter or data-adapter IP address.
4. Solar Hub scans the hardware automatically.
5. Native Home Assistant entities and the Solar Hub dashboard are created from the detected system.

The default GivEnergy local Modbus port is `8899` and is not shown in the normal setup flow.

## Automatic discovery

Solar Hub discovers as much useful hardware information as the provider exposes, including inverter model/serial/firmware, phases, MPPTs, PV strings, batteries and available controls.

## Dashboard

The sidebar dashboard is split into:

**Overview · Solar · Battery · Grid · EV · PredBat · History · Settings**

PredBat is optional and does not block the core integration.

## HACS

Add this repository as a custom **Integration** repository:

`https://github.com/Adya84/ha-solar-hub`

## Architecture

Solar Hub is provider-based. Manufacturer-specific code lives under `providers/`, while the entity and dashboard layers consume a shared normalised snapshot. This keeps future inverter manufacturers independent from the frontend.

## Release channel

Stable releases are published on GitHub using normal semantic version numbers.

## Licence

MIT.
