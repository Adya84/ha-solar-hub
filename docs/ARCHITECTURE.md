# Solar Hub architecture

Solar Hub has four layers:

1. **Providers** — manufacturer or service-specific connectivity.
2. **Normalised snapshot** — one shared solar/home/grid/battery model.
3. **Home Assistant layer** — native entities plus a small WebSocket API for the dashboard.
4. **Frontend** — a standalone tablet-first Solar Hub panel.

The first provider is GivEnergy local Modbus. Future manufacturers should implement the provider contract rather than adding manufacturer logic to the dashboard.

PredBat, EV and tariff support are optional modules and must not become hard dependencies of the core solar dashboard.
