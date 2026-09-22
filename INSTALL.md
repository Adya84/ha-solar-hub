# Installing Solar Hub

1. Add `https://github.com/Adya84/ha-solar-hub` to HACS as an **Integration** custom repository.
2. Download Solar Hub.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**.
5. Search for **Solar Hub**.
6. Enter the inverter/data-adapter IP address.
7. Solar Hub runs a quick basic scan automatically.
8. Open **Solar Hub** from the Home Assistant sidebar.

For battery-cell, BMS and extended inverter information, open **Solar Hub →
Settings** and select **Deep Modbus scan**. This is optional and is kept out
of normal live polling. PredBat plan data appears on the Overview automatically
when PredBat is installed and has published data in Home Assistant.

For the first provider, Home Assistant must be able to reach the GivEnergy device locally on port `8899`.
