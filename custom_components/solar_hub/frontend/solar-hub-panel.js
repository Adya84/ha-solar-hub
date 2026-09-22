class SolarHubPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._tab = "overview";
    this._data = {};
    this._predbat = {};
    this._timer = null;
  }

  set hass(value) {
    this._hass = value;
    if (!this._timer) {
      this._load();
      this._timer = setInterval(() => this._load(), 5000);
    }
  }

  connectedCallback() { this._render(); }
  disconnectedCallback() { if (this._timer) clearInterval(this._timer); this._timer = null; }

  async _load() {
    if (!this._hass) return;
    try {
      const [data, predbat] = await Promise.all([
        this._hass.callWS({ type: "solar_hub/overview" }),
        this._hass.callWS({ type: "solar_hub/predbat" }),
      ]);
      this._data = data || {};
      this._predbat = predbat || {};
    } catch (err) {
      this._data = { connection: { state: "offline", last_error: String(err), stale: true } };
    }
    this._render();
  }

  _escape(value) {
    return String(value ?? "—")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  _metric(metric) {
    if (!metric || metric.available === false || metric.value == null) return "—";
    const value = Number(metric.value);
    if (Number.isFinite(value) && metric.unit === "W" && Math.abs(value) >= 1000) {
      return `${(value / 1000).toFixed(2)} kW`;
    }
    return `${metric.value}${metric.unit ? ` ${metric.unit}` : ""}`;
  }

  _tabs() {
    const tabs = [
      ["overview", "Overview"], ["solar", "Solar"], ["battery", "Battery"],
      ["grid", "Grid"], ["ev", "EV"], ["predbat", "PredBat"],
      ["history", "History"], ["settings", "Settings"],
    ];
    return tabs.map(([key, label]) =>
      `<button data-tab="${key}" class="${this._tab === key ? "active" : ""}">${label}</button>`
    ).join("");
  }

  _stat(label, value, note = "") {
    return `<article class="stat"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>`;
  }

  _predbatTimeline() {
    const plan = this._predbat?.plan_segments || [];
    const action = this._predbat?.current_action || "No PredBat action detected";
    if (!this._predbat?.available) {
      return `<section class="plan"><span class="kicker">NEXT 24 HOURS</span><strong>PredBat is not connected</strong><small>Live energy data remains available.</small></section>`;
    }
    const segments = plan.slice(0, 24).map(segment =>
      `<span class="plan-segment ${this._escape(segment.kind || "unknown")}">${this._escape(segment.label || segment.kind || "Planned")}</span>`
    ).join("");
    return `<section class="plan"><span class="kicker">NEXT 24 HOURS</span><strong>${this._escape(action)}</strong><div class="plan-track"><i class="now-marker" title="Now"></i>${segments || "<small>PredBat is connected but has not published a readable plan.</small>"}</div></section>`;
  }

  _overview() {
    const d = this._data;
    const c = d.connection || {};
    const b = d.battery_bank || {};
    return `
      <section class="heading">
        <div><span class="kicker">LIVE ENERGY</span><h1>Overview</h1><p>Solar, home, battery and grid in one place.</p></div>
        <div class="status ${c.state === "online" ? "online" : ""}"><i></i>${this._escape(c.state || "connecting")}</div>
      </section>
      <section class="flow">
        <div class="node solar"><div class="icon">☀</div><small>Solar</small><strong>${this._metric(d.solar?.power)}</strong></div>
        <div class="connector">→</div>
        <div class="node home"><div class="icon">⌂</div><small>Home</small><strong>${this._metric(d.home?.power)}</strong></div>
        <div class="connector">↔</div>
        <div class="node battery"><div class="icon">▰</div><small>Battery</small><strong>${this._metric(b.soc)}</strong><em>${this._metric(b.power)}</em></div>
        <div class="connector">↔</div>
        <div class="node grid"><div class="icon">⚡</div><small>Grid</small><strong>${this._metric(d.grid?.power)}</strong></div>
      </section>
      ${this._predbatTimeline()}
      <section class="stats">
        ${this._stat("Solar today", this._metric(d.energy_today?.solar_generation), "Generated")}
        ${this._stat("Home today", this._metric(d.energy_today?.consumption), "Consumed")}
        ${this._stat("Grid import", this._metric(d.energy_today?.grid_import), "Today")}
        ${this._stat("Grid export", this._metric(d.energy_today?.grid_export), "Today")}
        ${this._stat("Battery charge", this._metric(d.energy_today?.battery_charge), "Today")}
        ${this._stat("Battery discharge", this._metric(d.energy_today?.battery_discharge), "Today")}
      </section>`;
  }

  _page(title, intro, content) {
    return `<section class="heading"><div><span class="kicker">SOLAR HUB</span><h1>${title}</h1><p>${intro}</p></div></section><section class="stats detail">${content}</section>`;
  }

  _solar() {
    const d = this._data;
    const strings = d.solar?.strings || [];
    return this._page("Solar", "Live generation and detected PV strings.",
      this._stat("Live generation", this._metric(d.solar?.power)) +
      this._stat("Generated today", this._metric(d.energy_today?.solar_generation)) +
      this._stat("Generated total", this._metric(d.energy_total?.solar_generation)) +
      strings.map(s => this._stat(`PV String ${s.index}`, this._metric(s.power), `${this._metric(s.voltage)} · ${this._metric(s.current)}`)).join(""));
  }

  _battery() {
    const d = this._data;
    const bank = d.battery_bank || {};
    const batteries = d.batteries || [];
    const deep = d.system_profile?.deep_data?.batteries || [];
    const cellDetails = deep.map(b => (b.cells || []).map(cell =>
      this._stat(`Battery ${b.index} cell ${cell.index}`, `${this._escape(cell.voltage)} V`, "Deep scan")
    ).join("")).join("");
    return this._page("Battery", "Battery bank status and detected modules.",
      this._stat("State of charge", this._metric(bank.soc)) +
      this._stat("Live power", this._metric(bank.power)) +
      this._stat("Voltage", this._metric(bank.voltage)) +
      this._stat("Temperature", this._metric(bank.temperature)) +
      batteries.map(b => this._stat(`Battery ${b.index}`, this._metric(b.soc), this._escape(b.serial || "Serial unavailable"))).join("") +
      cellDetails);
  }

  _grid() {
    const d = this._data;
    return this._page("Grid", "Import, export and grid conditions.",
      this._stat("Grid power", this._metric(d.grid?.power)) +
      this._stat("Voltage", this._metric(d.grid?.voltage)) +
      this._stat("Frequency", this._metric(d.grid?.frequency)) +
      this._stat("Import today", this._metric(d.energy_today?.grid_import)) +
      this._stat("Export today", this._metric(d.energy_today?.grid_export)));
  }

  _history() {
    const d = this._data;
    return this._page("History", "Lifetime energy totals exposed by the inverter.",
      this._stat("Solar total", this._metric(d.energy_total?.solar_generation)) +
      this._stat("Home total", this._metric(d.energy_total?.consumption)) +
      this._stat("Grid import total", this._metric(d.energy_total?.grid_import)) +
      this._stat("Grid export total", this._metric(d.energy_total?.grid_export)));
  }

  _predbatPage() {
    const p = this._predbat || {};
    const rows = (p.entities || []).slice(0, 50).map(e =>
      `<div class="row"><span><strong>${this._escape(e.name)}</strong><small>${this._escape(e.entity_id)}</small></span><b>${this._escape(e.state)}${e.unit ? ` ${this._escape(e.unit)}` : ""}</b></div>`
    ).join("");
    return `<section class="heading"><div><span class="kicker">OPTIONAL MODULE</span><h1>PredBat</h1><p>Detected planning entities already available in Home Assistant.</p></div></section>
      <section class="module"><strong>${p.available ? "PredBat detected" : "PredBat not detected"}</strong><span>${p.available ? `${p.count} entities found` : "Solar Hub works without PredBat."}</span></section>
      <section class="rows">${rows || "<p>No PredBat entities detected.</p>"}</section>`;
  }

  _settings() {
    const d = this._data;
    const p = d.system_profile || {};
    const c = d.connection || {};
    const controls = p.controls || {};
    const scan = p.deep_scan || { state: "not_run" };
    return this._page("Settings", "Basic hardware is discovered automatically. Run a deep scan for BMS and cell detail.",
      this._stat("Manufacturer", this._escape(p.manufacturer)) +
      this._stat("Model", this._escape(p.model)) +
      this._stat("Serial", this._escape(p.serial)) +
      this._stat("Firmware", this._escape(p.firmware)) +
      this._stat("Phases", this._escape(p.phases)) +
      this._stat("MPPTs", this._escape(p.mppt_count)) +
      this._stat("PV strings", this._escape(p.pv_string_count)) +
      this._stat("Batteries", this._escape(p.battery_count)) +
      this._stat("Controls found", Object.values(controls).filter(Boolean).length) +
      this._stat("Connection", this._escape(c.state)) +
      this._stat("Deep scan", this._escape(scan.state), this._escape(scan.completed_at || scan.error || "Not run")) +
      `<article class="stat"><span>Hardware detail</span><button data-deep-scan ${scan.state === "running" ? "disabled" : ""}>Deep Modbus scan</button><small>Reads extended battery and inverter data.</small></article>`);
  }

  _content() {
    if (this._tab === "overview") return this._overview();
    if (this._tab === "solar") return this._solar();
    if (this._tab === "battery") return this._battery();
    if (this._tab === "grid") return this._grid();
    if (this._tab === "predbat") return this._predbatPage();
    if (this._tab === "history") return this._history();
    if (this._tab === "settings") return this._settings();
    return this._page("EV", "EV charging is an optional Solar Hub module.", this._stat("EV module", "Not configured"));
  }

  _render() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;min-height:100vh;background:#06100e;color:#f4faf7;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
      *{box-sizing:border-box}.shell{max-width:1500px;margin:0 auto;padding:20px}
      header{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:10px 0 22px}.brand{display:flex;align-items:center;gap:12px;font-size:22px;font-weight:900}.mark{width:44px;height:44px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(145deg,#0f3428,#13251f);border:1px solid #295140;font-size:24px}
      nav{display:flex;gap:6px;padding:6px;background:#0b1715;border:1px solid #1b302b;border-radius:15px;overflow:auto}nav button{border:0;background:transparent;color:#829b94;padding:10px 14px;border-radius:10px;font-weight:800;cursor:pointer;white-space:nowrap}nav button.active,nav button:hover{background:#16372c;color:#73e8a7}
      .heading{display:flex;justify-content:space-between;align-items:flex-start;padding:24px 2px}.kicker{font-size:11px;letter-spacing:.18em;color:#64df9d;font-weight:900}.heading h1{font-size:42px;line-height:1;margin:7px 0 9px}.heading p{margin:0;color:#849c95}.status{display:flex;align-items:center;gap:8px;padding:9px 13px;border:1px solid #30433d;border-radius:999px;color:#a8bab4;text-transform:capitalize}.status i{width:9px;height:9px;border-radius:50%;background:#f4b64f}.status.online i{background:#64df9d}
      .flow{display:grid;grid-template-columns:1fr 52px 1fr 52px 1fr 52px 1fr;align-items:center;padding:28px;background:linear-gradient(145deg,#0b1714,#091411);border:1px solid #1c342e;border-radius:24px;box-shadow:0 20px 50px #0005}.node{text-align:center;padding:22px 12px;background:#0e201b;border:1px solid #203d34;border-radius:18px}.node .icon{font-size:31px;margin-bottom:9px}.node small{display:block;color:#7d9890;text-transform:uppercase;font-size:11px;font-weight:900}.node strong{display:block;font-size:27px;margin-top:7px}.node em{display:block;color:#78938a;font-style:normal;margin-top:5px}.connector{text-align:center;color:#55d995;font-size:25px}
      .stats{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-top:14px}.detail{grid-template-columns:repeat(4,1fr)}.stat,.module,.rows,.plan{background:#0b1815;border:1px solid #1b302b;border-radius:18px;padding:18px}.stat span{display:block;color:#819a92;font-size:12px;font-weight:800}.stat strong{display:block;font-size:22px;margin:14px 0 4px}.stat small,.plan small{color:#617a72}.stat button{margin-top:12px;background:#1b5a42;border:0;border-radius:8px;color:white;padding:9px;font-weight:800;cursor:pointer}.module{display:flex;justify-content:space-between;gap:20px}.module span{color:#829b94}.rows{margin-top:14px}.row{display:flex;justify-content:space-between;gap:18px;padding:12px 0;border-top:1px solid #182a26}.row:first-child{border-top:0}.row span strong,.row span small{display:block}.row span small{color:#5f7770;font-size:10px;margin-top:3px}.plan{margin-top:14px}.plan>strong{display:block;font-size:19px;margin:7px 0}.plan-track{position:relative;min-height:45px;display:flex;gap:5px;align-items:stretch;padding:9px 0}.plan-segment{flex:1;min-width:56px;padding:7px;border-radius:7px;font-size:11px;font-weight:800;color:#07100c;background:#777}.plan-segment.charge,.plan-segment.solar{background:#55c985}.plan-segment.discharge{background:#67a7e7}.plan-segment.import{background:#e5ad52}.plan-segment.export{background:#9c7ae6}.now-marker{position:absolute;top:0;bottom:0;left:0;border-left:3px solid white}
      @media(max-width:1050px){.stats{grid-template-columns:repeat(3,1fr)}.flow{grid-template-columns:1fr 30px 1fr 30px 1fr 30px 1fr;padding:16px}.node strong{font-size:20px}}
      @media(max-width:720px){.shell{padding:10px}header{flex-direction:column;align-items:flex-start}nav{width:100%}.heading h1{font-size:32px}.flow{grid-template-columns:1fr 1fr;gap:10px}.connector{display:none}.stats,.detail{grid-template-columns:repeat(2,1fr)}}
    </style><div class="shell"><header><div class="brand"><div class="mark">☀</div>Solar Hub</div><nav>${this._tabs()}</nav></header><main>${this._content()}</main></div>`;

    this.shadowRoot.querySelectorAll("[data-tab]").forEach(button => {
      button.addEventListener("click", () => { this._tab = button.dataset.tab; this._render(); });
    });
    this.shadowRoot.querySelector("[data-deep-scan]")?.addEventListener("click", async () => {
      await this._hass?.callWS({ type: "solar_hub/deep_scan" });
      await this._load();
    });
  }
}

if (!customElements.get("solar-hub-panel")) customElements.define("solar-hub-panel", SolarHubPanel);
