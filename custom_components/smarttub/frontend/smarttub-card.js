/*
 * SmartTub card for Home Assistant.
 *
 * Shipped with the SmartTub (resilient) integration and registered
 * automatically; no Lovelace resource needed.
 *
 *   type: custom:smarttub-card
 *   device_id: <optional, first SmartTub spa when omitted>
 *   variant: full | compact            (default: full)
 *   name: <optional title>
 *   show_filtration: true
 *   show_maintenance: true
 *   show_circulation: false
 */

const CARD_VERSION = "1.2.0";

const STRINGS = {
  en: {
    water: "Water",
    target: "target",
    heating_to: "Heating to {t}",
    idle_at_temp: "Idle · at temperature",
    idle: "Idle",
    presets: { none: "Auto", eco: "Eco", day: "Day", ready: "Ready" },
    jets: "Jets",
    light: "Light",
    exterior: "Exterior",
    circulation: "Circulation",
    on: "On",
    off: "Off",
    high: "High",
    low: "Low",
    filtration: "Filtration",
    filtering: "Filtering",
    filtration_at: "filtration at {h}",
    secondary: "Secondary: {m}",
    secondary_modes: { frequent: "frequent", infrequent: "infrequent", away: "away" },
    effects: {
      purple: "Purple", orange: "Orange", red: "Red", yellow: "Yellow", green: "Green",
      aqua: "Aqua", blue: "Blue", white: "White", amber: "Amber", colorloop: "Color loop",
      high_speed_wheel: "Fast wheel", low_speed_wheel: "Slow wheel", full_dynamic_rgb: "Dynamic",
      auto_timer_exterior: "Auto timer", party: "Party", color_wheel: "Color wheel", on: "On",
    },
    hours_short: "h",
    maintenance: "Maintenance",
    days_short: "d",
    due: "due",
    cloud_ok: "Cloud OK",
    cloud_slow: "Cloud slow",
    cloud_slow_title: "Cloud slow — showing last data",
    cloud_slow_detail: "{n} of {max} polls failed · last update {ago}",
    unavailable_title: "SmartTub unavailable",
    unavailable_detail: "No data from the SmartTub cloud · last update {ago}",
    error_title: "Spa reports an error",
    last_update: "Last update {time}",
    failed_polls: "{n} failed polls",
    failed_polls_short: "failed polls",
    last_poll: "last poll",
    interval: "interval",
    refresh: "Refresh",
    ago_now: "just now",
    ago_min: "{n} min ago",
    ago_hour: "{n} h ago",
    not_found: "No SmartTub spa found. Is the SmartTub integration set up?",
    lower_target: "Lower target temperature",
    raise_target: "Raise target temperature",
    states: { normal: "Normal", standby: "Standby", sleep: "Sleep", heat: "Heating" },
    editor: {
      device_id: "Spa",
      variant: "Variant",
      name: "Name (optional)",
      show_filtration: "Show filtration",
      show_maintenance: "Show maintenance",
      show_circulation: "Show circulation pump",
      full: "Full",
      compact: "Compact",
    },
  },
  nl: {
    water: "Water",
    target: "doel",
    heating_to: "Verwarmt naar {t}",
    idle_at_temp: "In rust · op temperatuur",
    idle: "In rust",
    presets: { none: "Auto", eco: "Eco", day: "Dag", ready: "Klaar" },
    jets: "Jets",
    light: "Licht",
    exterior: "Buiten",
    circulation: "Circulatie",
    on: "Aan",
    off: "Uit",
    high: "Hoog",
    low: "Laag",
    filtration: "Filtratie",
    filtering: "Filtert",
    filtration_at: "filtratie om {h}",
    secondary: "Secundair: {m}",
    secondary_modes: { frequent: "vaak", infrequent: "weinig", away: "weg" },
    effects: {
      purple: "Paars", orange: "Oranje", red: "Rood", yellow: "Geel", green: "Groen",
      aqua: "Aqua", blue: "Blauw", white: "Wit", amber: "Amber", colorloop: "Kleurenloop",
      high_speed_wheel: "Snel wiel", low_speed_wheel: "Langzaam wiel", full_dynamic_rgb: "Dynamisch",
      auto_timer_exterior: "Auto-timer", party: "Feest", color_wheel: "Kleurenwiel", on: "Aan",
    },
    hours_short: "u",
    maintenance: "Onderhoud",
    days_short: "d",
    due: "nu",
    cloud_ok: "Cloud OK",
    cloud_slow: "Cloud traag",
    cloud_slow_title: "Cloud traag — laatste data getoond",
    cloud_slow_detail: "{n} van {max} polls mislukt · bijgewerkt {ago}",
    unavailable_title: "SmartTub onbereikbaar",
    unavailable_detail: "Geen data van de SmartTub-cloud · bijgewerkt {ago}",
    error_title: "Spa meldt een fout",
    last_update: "Bijgewerkt {time}",
    failed_polls: "{n} mislukte polls",
    failed_polls_short: "mislukte polls",
    last_poll: "laatste poll",
    interval: "interval",
    refresh: "Vernieuwen",
    ago_now: "zojuist",
    ago_min: "{n} min geleden",
    ago_hour: "{n} u geleden",
    not_found: "Geen SmartTub-spa gevonden. Is de SmartTub-integratie ingesteld?",
    lower_target: "Doeltemperatuur lager",
    raise_target: "Doeltemperatuur hoger",
    states: { normal: "Normaal", standby: "Stand-by", sleep: "Slaap", heat: "Verwarmen" },
    editor: {
      device_id: "Spa",
      variant: "Variant",
      name: "Naam (optioneel)",
      show_filtration: "Filtratie tonen",
      show_maintenance: "Onderhoud tonen",
      show_circulation: "Circulatiepomp tonen",
      full: "Volledig",
      compact: "Compact",
    },
  },
};

// light effect -> colour used for the tub rim and the light tile
const EFFECT_COLORS = {
  purple: "#9b6bff",
  orange: "#f29a45",
  red: "#e5534b",
  yellow: "#e8c547",
  green: "#57c27a",
  aqua: "#3fc8c8",
  blue: "#4f8ef7",
  white: "#e8eaed",
  amber: "#f2b33d",
};
const DEFAULT_LIGHT_COLOR = "#7fd3e0";
// effects in which the spa cycles through colours by itself
const CYCLE_EFFECTS = new Set([
  "colorloop", "color_wheel", "high_speed_wheel", "low_speed_wheel", "full_dynamic_rgb", "party",
]);
const RAINBOW = ["#9b6bff", "#4f8ef7", "#3fc8c8", "#57c27a", "#e8c547", "#f29a45", "#e5534b", "#9b6bff"];

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (_err) {
    return false;
  }
}

const DEFAULTS = {
  variant: "full",
  show_filtration: true,
  show_maintenance: true,
  show_circulation: false,
};

function lang(hass) {
  const code = ((hass && hass.locale && hass.locale.language) || hass?.language || "en")
    .toLowerCase()
    .split("-")[0];
  return STRINGS[code] ? code : "en";
}

function fmt(template, values) {
  return template.replace(/\{(\w+)\}/g, (_, key) => (key in values ? values[key] : ""));
}

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function isAvailable(stateObj) {
  return !!stateObj && stateObj.state !== "unavailable" && stateObj.state !== "unknown";
}

/** Find the SmartTub entities of one spa through the entity registry. */
function discover(hass, deviceId) {
  const entries = Object.values(hass.entities || {}).filter(
    (entry) => entry.platform === "smarttub" && entry.device_id
  );
  if (!entries.length) return null;
  const device = deviceId || entries[0].device_id;
  const own = entries.filter((entry) => entry.device_id === device);
  if (!own.length) return null;

  const deviceInfo = (hass.devices || {})[device] || {};
  const deviceName = deviceInfo.name_by_user || deviceInfo.name || "SmartTub";

  const byKey = (domain, key, suffix) =>
    own
      .filter(
        (entry) =>
          entry.entity_id.startsWith(domain + ".") &&
          (entry.translation_key === key ||
            (!entry.translation_key && suffix && suffix.test(entry.entity_id)))
      )
      .map((entry) => entry.entity_id)
      .sort();

  const first = (domain, key, suffix) => byKey(domain, key, suffix)[0];

  return {
    device,
    deviceName,
    climate: first("climate", "thermostat", /_thermostat$/),
    jets: byKey("switch", "jet", /_jet_[^_]+$/),
    pumps: byKey("switch", "pump", /_pump_[^_]+$/),
    circulation: first("switch", "circulation_pump", /_circulation_pump$/),
    lights: byKey("light", "light_zone", /_light_\d+$/),
    state: first("sensor", "state", /_state$/),
    primary: first("sensor", "primary_filtration_cycle", /_primary_filtration_cycle$/),
    secondary: first("sensor", "secondary_filtration_cycle", /_secondary_filtration_cycle$/),
    reminders: byKey("binary_sensor", "reminder", /_reminder$/),
    error: first("binary_sensor", "error", /_error$/),
    api: first("binary_sensor", "api_connection", /_api_connection$/),
    lastSuccess: first("sensor", "last_successful_poll", /_last_successful_poll$/),
    pollDuration: first("sensor", "last_poll_duration", /_last_poll_duration$/),
    failedPolls: first("sensor", "consecutive_failed_polls", /_consecutive_failed_polls$/),
    refresh: first("button", "refresh", /_refresh$/),
  };
}

/** Strip the device name from a friendly name ("Jacuzzi J-435 Jet P1" -> "Jet P1"). */
function shortName(stateObj, deviceName) {
  const name = stateObj?.attributes?.friendly_name || "";
  return name.startsWith(deviceName + " ") ? name.slice(deviceName.length + 1) : name;
}

const ICONS = {
  check: '<path d="M5 12.5 10 17l9-10"/>',
  flame: '<path d="M12 3c3 4 5 6.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-5 .5 2 1.5 3 3 3-1-3 0-5.5 0-8Z"/>',
  warn: '<path d="M12 4 2.5 20h19L12 4Z"/><path d="M12 10v4M12 17.5v.5"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
  dot: '<circle cx="12" cy="12" r="5"/>',
};

function icon(name, size = 14) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${ICONS[name]}</svg>`;
}

class SmartTubCard extends HTMLElement {
  static getConfigForm() {
    const s = STRINGS[(document.documentElement.lang || "en").split("-")[0]] || STRINGS.en;
    return {
      schema: [
        { name: "device_id", selector: { device: { filter: { integration: "smarttub" } } } },
        {
          name: "variant",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "full", label: s.editor.full },
                { value: "compact", label: s.editor.compact },
              ],
            },
          },
        },
        { name: "name", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "show_filtration", selector: { boolean: {} } },
            { name: "show_maintenance", selector: { boolean: {} } },
            { name: "show_circulation", selector: { boolean: {} } },
          ],
        },
      ],
      computeLabel: (schema) => s.editor[schema.name] || schema.name,
    };
  }

  static getStubConfig(hass) {
    const found = discover(hass);
    return found ? { device_id: found.device } : {};
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._pendingTarget = null;
    this._targetTimer = null;
    this._lastKey = null;
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("contextmenu", (ev) => this._onContext(ev));
  }

  setConfig(config) {
    if (config.variant && !["full", "compact"].includes(config.variant)) {
      throw new Error("variant must be 'full' or 'compact'");
    }
    this._config = { ...DEFAULTS, ...config };
    this._lastKey = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return this._config?.variant === "compact" ? 3 : 9;
  }

  getGridOptions() {
    return this._config?.variant === "compact"
      ? { columns: 6, min_columns: 6, rows: "auto" }
      : { columns: 12, min_columns: 6, rows: "auto" };
  }

  disconnectedCallback() {
    clearTimeout(this._targetTimer);
    clearInterval(this._ticker);
    this._ticker = null;
  }

  connectedCallback() {
    // keep "x min ago" texts current
    if (!this._ticker) {
      this._ticker = setInterval(() => {
        this._lastKey = null;
        if (this._hass) this._render();
      }, 60000);
    }
  }

  // ------------------------------------------------------------- helpers

  _s() {
    return STRINGS[lang(this._hass)];
  }

  _st(entityId) {
    return entityId ? this._hass.states[entityId] : undefined;
  }

  _num(value, digits = 1) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "–";
    return new Intl.NumberFormat(this._hass.locale?.language || "en", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(n);
  }

  _time(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "–";
    return new Intl.DateTimeFormat(this._hass.locale?.language || "en", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  }

  _ago(iso) {
    const s = this._s();
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return "–";
    const minutes = Math.round((Date.now() - d.getTime()) / 60000);
    if (minutes < 1) return s.ago_now;
    if (minutes < 120) return fmt(s.ago_min, { n: minutes });
    return fmt(s.ago_hour, { n: Math.round(minutes / 60) });
  }

  _callService(domain, service, data) {
    return this._hass.callService(domain, service, data);
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true })
    );
  }

  // ------------------------------------------------------------- actions

  _onClick(ev) {
    const el = ev.composedPath().find((node) => node.dataset && node.dataset.action);
    if (!el) return;
    const { action, entity, value } = el.dataset;
    const e = this._entities;
    if (!e) return;
    switch (action) {
      case "toggle":
        this._callService(entity.split(".")[0], "toggle", { entity_id: entity });
        break;
      case "light": {
        const on = this._st(entity)?.state === "on";
        this._callService("light", on ? "turn_off" : "turn_on", { entity_id: entity });
        break;
      }
      case "preset":
        this._callService("climate", "set_preset_mode", {
          entity_id: e.climate,
          preset_mode: value,
        });
        break;
      case "target":
        this._stepTarget(Number(value));
        break;
      case "refresh":
        this._callService("button", "press", { entity_id: e.refresh });
        break;
      case "more-info":
        this._moreInfo(entity);
        break;
      default:
        break;
    }
  }

  _onContext(ev) {
    const el = ev.composedPath().find((node) => node.dataset && node.dataset.entity);
    if (!el) return;
    ev.preventDefault();
    this._moreInfo(el.dataset.entity);
  }

  _stepTarget(step) {
    const climate = this._st(this._entities.climate);
    if (!isAvailable(climate)) return;
    const min = climate.attributes.min_temp ?? 18.5;
    const max = climate.attributes.max_temp ?? 40;
    const current = this._pendingTarget ?? Number(climate.attributes.temperature);
    this._pendingTarget = Math.min(max, Math.max(min, Math.round((current + step) * 2) / 2));
    this._lastKey = null;
    this._render();
    clearTimeout(this._targetTimer);
    this._targetTimer = setTimeout(() => {
      const temperature = this._pendingTarget;
      this._callService("climate", "set_temperature", {
        entity_id: this._entities.climate,
        temperature,
      }).finally(() => {
        this._pendingTarget = null;
        this._lastKey = null;
        this._render();
      });
    }, 900);
  }

  // ------------------------------------------------------------- render

  _render() {
    if (!this._hass || !this._config) return;
    const e = discover(this._hass, this._config.device_id);
    this._entities = e;

    // re-render only when one of the spa's states changed
    const ids = e
      ? [
          e.climate, ...e.jets, ...e.pumps, e.circulation, ...e.lights, e.state, e.primary,
          e.secondary, ...e.reminders, e.error, e.api, e.lastSuccess, e.pollDuration,
          e.failedPolls,
        ].filter(Boolean)
      : [];
    const key =
      ids.map((id) => this._hass.states[id]?.last_updated).join("|") +
      "|" + this._pendingTarget + "|" + lang(this._hass) + "|" +
      (this._hass.themes?.darkMode ? "d" : "l");
    if (key === this._lastKey) return;
    this._lastKey = key;

    const s = this._s();
    if (!e || !e.climate) {
      this.shadowRoot.innerHTML = `${STYLE}<ha-card><div class="empty">${esc(s.not_found)}</div></ha-card>`;
      return;
    }
    const body = this._config.variant === "compact" ? this._compact(e, s) : this._full(e, s);
    this.shadowRoot.innerHTML = `${STYLE}<ha-card><div class="wrap">${body}</div></ha-card>`;
  }

  _model(e, s) {
    const climate = this._st(e.climate);
    const available = isAvailable(climate);
    const attrs = climate?.attributes || {};
    const target = this._pendingTarget ?? attrs.temperature;
    const current = attrs.current_temperature;
    const heating = attrs.hvac_action === "heating";
    // the rim shows the colour of the interior (underwater) lights
    const lightsOn = e.lights
      .map((id) => this._st(id))
      .filter((st) => st?.state === "on" && st.attributes?.zone_type !== "exterior");
    const lightEffect = lightsOn.length ? lightsOn[0].attributes.effect : null;
    const lightCycling = CYCLE_EFFECTS.has(lightEffect);
    const lightColor = lightsOn.length
      ? EFFECT_COLORS[lightEffect] || DEFAULT_LIGHT_COLOR
      : null;
    const api = this._st(e.api);
    const failed = this._st(e.failedPolls);
    const lastSuccess = this._st(e.lastSuccess)?.state;
    let cloud = "none";
    if (api) cloud = api.state === "on" ? "ok" : "slow";
    if (!available) cloud = "down";
    const jetOn = e.jets.map((id) => this._st(id)?.state === "on");
    return {
      climate, available, attrs, target, current, heating, lightColor, lightCycling, api, failed,
      lastSuccess: lastSuccess && lastSuccess !== "unknown" ? lastSuccess : climate?.last_updated,
      cloud, jetOn,
      title: this._config.name || e.deviceName,
    };
  }

  _cloudPill(m, s) {
    if (m.cloud === "ok") {
      const duration = this._st(this._entities.pollDuration)?.state;
      const extra = duration && Number.isFinite(Number(duration))
        ? ` · ${this._num(duration, 2)} s` : "";
      return `<span class="pill ok">${icon("check", 12)}${esc(s.cloud_ok)}${extra}</span>`;
    }
    if (m.cloud === "slow") return `<span class="pill warn">${icon("warn", 12)}${esc(s.cloud_slow)}</span>`;
    return "";
  }

  _banner(e, m, s) {
    const parts = [];
    const error = this._st(e.error);
    if (error?.state === "on") {
      const a = error.attributes || {};
      const detail = [a.error_code, a.error_title].filter(Boolean).join(" · ");
      parts.push(`<div class="banner bad" data-action="more-info" data-entity="${esc(e.error)}">
        ${icon("warn", 18)}<div><div class="b-title">${esc(s.error_title)}</div>
        <div class="b-detail">${esc(detail)}</div></div></div>`);
    }
    if (m.cloud === "down") {
      parts.push(`<div class="banner warn">${icon("warn", 18)}<div>
        <div class="b-title">${esc(s.unavailable_title)}</div>
        <div class="b-detail">${esc(fmt(s.unavailable_detail, { ago: this._ago(m.lastSuccess) }))}</div>
        </div></div>`);
    } else if (m.cloud === "slow") {
      const fa = m.failed?.attributes || {};
      parts.push(`<div class="banner warn" data-action="more-info" data-entity="${esc(e.api)}">
        ${icon("warn", 18)}<div><div class="b-title">${esc(s.cloud_slow_title)}</div>
        <div class="b-detail">${esc(fmt(s.cloud_slow_detail, {
          n: m.failed?.state ?? "?",
          max: fa.failure_threshold ?? "?",
          ago: this._ago(m.lastSuccess),
        }))}</div></div></div>`);
    }
    return parts.join("");
  }

  _heatLine(m, s) {
    if (!m.available) return `<div class="heat">${esc(s.idle)}</div>`;
    if (m.heating) {
      return `<div class="heat on">${icon("flame", 13)}${esc(fmt(s.heating_to, { t: this._num(m.target) + " °C" }))}</div>`;
    }
    const close = Math.abs(Number(m.current) - Number(m.target)) <= 0.5;
    return `<div class="heat">${icon("flame", 13)}${esc(close ? s.idle_at_temp : s.idle)}</div>`;
  }

  _subtitle(e, s) {
    const parts = [];
    const state = this._st(e.state)?.state;
    if (state && state !== "unavailable" && state !== "unknown") {
      parts.push(s.states[state] || state.charAt(0).toUpperCase() + state.slice(1));
    }
    const primary = this._st(e.primary);
    if (primary && isAvailable(primary)) {
      if (primary.state === "active") parts.push(s.filtering);
      else if (primary.attributes.start_hour !== undefined) {
        parts.push(fmt(s.filtration_at, { h: String(primary.attributes.start_hour).padStart(2, "0") + ":00" }));
      }
    }
    return parts.join(" · ");
  }

  _tub(m, e, size) {
    const rim = m.lightCycling ? "url(#st-rainbow)" : m.lightColor || "var(--st-water-line)";
    const spin = reducedMotion()
      ? ""
      : '<animateTransform attributeName="gradientTransform" type="rotate" from="0 0.5 0.5" to="360 0.5 0.5" dur="6s" repeatCount="indefinite"/>';
    const defs = m.lightCycling
      ? `<defs><linearGradient id="st-rainbow" x1="0" y1="0" x2="1" y2="1">${RAINBOW.map(
          (c, i) => `<stop offset="${(i / (RAINBOW.length - 1)).toFixed(3)}" stop-color="${c}"/>`
        ).join("")}${spin}</linearGradient></defs>`
      : "";
    const jet = (on) => (on ? "var(--st-jet-on)" : "var(--st-jet-off)");
    const left = jet(m.jetOn[0]);
    const right = jet(m.jetOn[1] ?? m.jetOn[0]);
    return `<svg class="tub" width="${size}" height="${size}" viewBox="0 0 200 200" role="img"
      aria-label="${esc(m.title)}" data-action="more-info" data-entity="${esc(e.climate)}">
      ${defs}
      <rect x="6" y="6" width="188" height="188" rx="34" class="shell"/>
      <rect x="24" y="24" width="152" height="152" rx="24" class="water" style="stroke:${rim}" stroke-width="${m.lightColor ? 4 : 2}"/>
      <circle cx="100" cy="100" r="44" class="ripple"/>
      <circle cx="100" cy="100" r="22" class="ripple"/>
      <g style="fill:${left}"><circle cx="52" cy="58" r="5.5"/><circle cx="52" cy="84" r="5.5"/><circle cx="52" cy="110" r="5.5"/></g>
      <g style="fill:${right}"><circle cx="148" cy="58" r="5.5"/><circle cx="148" cy="84" r="5.5"/><circle cx="148" cy="110" r="5.5"/></g>
      <g style="fill:var(--st-jet-off)"><circle cx="78" cy="148" r="4"/><circle cx="100" cy="148" r="4"/><circle cx="122" cy="148" r="4"/></g>
    </svg>`;
  }

  _setpoint(m, s) {
    const disabled = m.available ? "" : "disabled";
    return `<div class="setpoint">
      <button class="round" data-action="target" data-value="-0.5" aria-label="${esc(s.lower_target)}" ${disabled}>−</button>
      <div class="sp-val"><div class="sp-num">${this._num(m.target)} °C</div><div class="muted small">${esc(s.target)}</div></div>
      <button class="round" data-action="target" data-value="0.5" aria-label="${esc(s.raise_target)}" ${disabled}>+</button>
    </div>`;
  }

  _presets(m, s) {
    const modes = m.attrs.preset_modes || ["none", "eco", "day", "ready"];
    return `<div class="presets">${modes
      .map((mode) => {
        const active = m.attrs.preset_mode === mode ? "active" : "";
        return `<button class="chip ${active}" data-action="preset" data-value="${esc(mode)}"
          aria-pressed="${active ? "true" : "false"}" ${m.available ? "" : "disabled"}>${esc(s.presets[mode] || mode)}</button>`;
      })
      .join("")}</div>`;
  }

  _tiles(e, s) {
    const tiles = [];
    const pumpTile = (id, kind) => {
      const st = this._st(id);
      const on = st?.state === "on";
      const label = shortName(st, e.deviceName).replace(/^(Jet|Pump)\s*/i, "") || id;
      tiles.push(`<button class="tile ${on ? "on" : ""}" data-action="toggle" data-entity="${esc(id)}"
        aria-pressed="${on}" ${isAvailable(st) ? "" : "disabled"}>
        <span class="t-kind">${esc(kind)}</span><span class="t-label">${esc(label)}</span>
        <span class="t-state">${esc(on ? s.on : s.off)}</span></button>`);
    };
    e.jets.forEach((id) => pumpTile(id, s.jets));
    e.pumps.forEach((id) => pumpTile(id, s.jets));
    if (this._config.show_circulation && e.circulation) pumpTile(e.circulation, s.circulation);
    e.lights.forEach((id) => {
      const st = this._st(id);
      const on = st?.state === "on";
      const effect = st?.attributes?.effect;
      const pct = st?.attributes?.brightness ? Math.round((st.attributes.brightness / 255) * 100) : null;
      const color = EFFECT_COLORS[effect] || DEFAULT_LIGHT_COLOR;
      const cycle = on && CYCLE_EFFECTS.has(effect) ? "cycle" : "";
      const exterior = st?.attributes?.zone_type === "exterior";
      const zone = exterior ? s.exterior : shortName(st, e.deviceName).replace(/^Light\s*/i, "") || id;
      const stateText = on
        ? [effect ? s.effects[effect] || effect.replace(/_/g, " ") : s.on, pct !== null ? pct + "%" : ""]
            .filter(Boolean).join(" ")
        : s.off;
      tiles.push(`<button class="tile light ${on ? "on" : ""} ${cycle}" style="--st-light:${color}" data-action="light"
        data-entity="${esc(id)}" aria-pressed="${on}" ${isAvailable(st) ? "" : "disabled"}>
        <span class="t-kind">${esc(s.light)}</span><span class="t-label">${esc(zone)}</span>
        <span class="t-state">${esc(stateText)}</span></button>`);
    });
    return `<div class="tiles">${tiles.join("")}</div>`;
  }

  _filtration(e, s) {
    const primary = this._st(e.primary);
    const secondary = this._st(e.secondary);
    if (!primary) return "";
    const a = primary.attributes || {};
    const start = a.start_hour !== undefined ? String(a.start_hour).padStart(2, "0") + ":00" : "–";
    const duration = a.duration !== undefined ? `${a.duration} ${s.hours_short}` : "";
    const mode = secondary?.attributes?.mode;
    return `<div class="box" data-action="more-info" data-entity="${esc(e.primary)}">
      <div class="muted small">${esc(s.filtration)}</div>
      <div class="strong">${esc([start, duration].filter(Boolean).join(" · "))}</div>
      ${mode ? `<div class="muted small">${esc(fmt(s.secondary, { m: s.secondary_modes[mode] || mode }))}</div>` : ""}
    </div>`;
  }

  _maintenance(e, s) {
    if (!e.reminders.length) return "";
    const items = e.reminders
      .map((id) => {
        const st = this._st(id);
        const days = st?.attributes?.days;
        const due = st?.state === "on";
        const label = shortName(st, e.deviceName).replace(/\s*reminder$/i, "").replace(/\s*herinnering$/i, "");
        const value = due ? s.due : days !== undefined ? `${days} ${s.days_short}` : "–";
        return `<div class="rem ${due ? "due" : ""}" data-action="more-info" data-entity="${esc(id)}">
          <div class="strong">${esc(value)}</div><div class="muted tiny">${esc(label)}</div></div>`;
      })
      .join("");
    return `<div class="box wide"><div class="muted small">${esc(s.maintenance)}</div>
      <div class="rems">${items}</div></div>`;
  }

  _footer(e, m, s) {
    const parts = [fmt(s.last_update, { time: this._time(m.lastSuccess) })];
    if (m.failed) parts.push(fmt(s.failed_polls, { n: m.failed.state }));
    const refresh = e.refresh
      ? `<button class="ghost" data-action="refresh" aria-label="${esc(s.refresh)}">${icon("refresh", 14)}<span>${esc(s.refresh)}</span></button>`
      : "";
    return `<div class="footer"><span>${esc(parts.join(" · "))}</span>${refresh}</div>`;
  }

  _full(e, s) {
    const m = this._model(e, s);
    const lower = [];
    if (this._config.show_filtration) lower.push(this._filtration(e, s));
    if (this._config.show_maintenance) lower.push(this._maintenance(e, s));
    return `
      <div class="head">
        <div><div class="title">${esc(m.title)}</div><div class="muted small">${esc(this._subtitle(e, s))}</div></div>
        ${this._cloudPill(m, s)}
      </div>
      ${this._banner(e, m, s)}
      <div class="hero ${m.available ? "" : "dim"}">
        ${this._tub(m, e, 168)}
        <div class="hero-info">
          <div class="muted small">${esc(s.water)}</div>
          <div class="temp" data-action="more-info" data-entity="${esc(e.climate)}">${this._num(m.current)}<span class="unit"> °C</span></div>
          ${this._setpoint(m, s)}
          ${this._heatLine(m, s)}
        </div>
      </div>
      ${this._presets(m, s)}
      ${this._tiles(e, s)}
      ${lower.filter(Boolean).length ? `<div class="lower">${lower.join("")}</div>` : ""}
      ${this._footer(e, m, s)}`;
  }

  _compact(e, s) {
    const m = this._model(e, s);
    const buttons = [];
    e.jets.forEach((id) => {
      const st = this._st(id);
      const on = st?.state === "on";
      const label = shortName(st, e.deviceName).replace(/^Jet\s*/i, "");
      buttons.push(`<button class="mini ${on ? "on" : ""}" data-action="toggle" data-entity="${esc(id)}"
        aria-pressed="${on}" aria-label="${esc(s.jets + " " + label)}" ${isAvailable(st) ? "" : "disabled"}>${esc(label)}</button>`);
    });
    if (e.lights.length) {
      const anyOn = e.lights.some((id) => this._st(id)?.state === "on");
      buttons.push(`<button class="mini light ${anyOn ? "on" : ""} ${anyOn && m.lightCycling ? "cycle" : ""}" style="--st-light:${m.lightColor || DEFAULT_LIGHT_COLOR}"
        data-action="light" data-entity="${esc(e.lights[0])}" aria-pressed="${anyOn}">${esc(s.light)}</button>`);
    }
    const sub = m.heating
      ? fmt(s.heating_to, { t: this._num(m.target) + " °C" })
      : `${s.target} ${this._num(m.target)} °C · ${s.idle.toLowerCase()}`;
    const cloud = m.cloud === "ok"
      ? `<span class="pill ok">${icon("dot", 10)}${esc(s.cloud_ok)}</span>`
      : m.cloud === "slow" || m.cloud === "down"
        ? `<span class="pill warn">${icon("warn", 10)}${esc(s.cloud_slow)}</span>` : "";
    return `
      <div class="c-row ${m.available ? "" : "dim"}">
        ${this._tub(m, e, 52)}
        <div class="c-info"><div class="title small-title">${esc(m.title)}</div>
          <div class="muted small ${m.heating ? "heat on" : ""}">${esc(sub)}</div></div>
        <div class="c-temp" data-action="more-info" data-entity="${esc(e.climate)}">${this._num(m.current)}<span class="unit"> °C</span></div>
      </div>
      <div class="c-buttons">${buttons.join("")}${cloud}</div>`;
  }
}

const STYLE = `<style>
  :host {
    --st-accent: var(--smarttub-accent-color, #3fb5c8);
    --st-heat: var(--state-climate-heat-color, #f29a45);
    --st-ok: var(--success-color, #43a047);
    --st-warn: var(--warning-color, #f2a93b);
    --st-bad: var(--error-color, #db4437);
    --st-tile: color-mix(in srgb, var(--primary-text-color, #e8eaed) 6%, transparent);
    --st-border: color-mix(in srgb, var(--primary-text-color, #e8eaed) 12%, transparent);
    --st-water: color-mix(in srgb, var(--st-accent) 30%, #0d2b33);
    --st-water-line: color-mix(in srgb, var(--st-accent) 45%, transparent);
    --st-jet-on: color-mix(in srgb, var(--st-accent) 75%, white);
    --st-jet-off: color-mix(in srgb, var(--primary-text-color, #e8eaed) 25%, transparent);
    display: block;
  }
  ha-card { overflow: hidden; container-type: inline-size; }
  .wrap { padding: 16px; display: flex; flex-direction: column; gap: 14px; color: var(--primary-text-color); }
  .empty { padding: 16px; color: var(--secondary-text-color); }
  button { font: inherit; color: inherit; cursor: pointer; }
  button:disabled { cursor: default; opacity: .5; }
  button:focus-visible, [data-action]:focus-visible { outline: 2px solid var(--st-accent); outline-offset: 2px; }
  .muted { color: var(--secondary-text-color); }
  .small { font-size: 12px; }
  .tiny { font-size: 10px; }
  .strong { font-weight: 600; font-size: 14px; }
  .title { font-size: 17px; font-weight: 600; }
  .small-title { font-size: 14px; }
  .unit { font-size: .45em; color: var(--secondary-text-color); font-weight: 500; }
  .dim { opacity: .55; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 500; white-space: nowrap; }
  .pill.ok { color: var(--st-ok); background: color-mix(in srgb, var(--st-ok) 14%, transparent); }
  .pill.warn { color: var(--st-warn); background: color-mix(in srgb, var(--st-warn) 16%, transparent); }
  .banner { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 12px; cursor: pointer; }
  .banner.warn { color: var(--st-warn); background: color-mix(in srgb, var(--st-warn) 14%, transparent); border: 1px solid color-mix(in srgb, var(--st-warn) 40%, transparent); }
  .banner.bad { color: var(--st-bad); background: color-mix(in srgb, var(--st-bad) 12%, transparent); border: 1px solid color-mix(in srgb, var(--st-bad) 40%, transparent); }
  .b-title { font-weight: 600; font-size: 13px; }
  .b-detail { font-size: 12px; color: var(--primary-text-color); opacity: .85; }
  .hero { display: flex; gap: 20px; align-items: center; }
  .hero-info { display: flex; flex-direction: column; gap: 10px; flex: 1; min-width: 0; }
  .tub { flex: none; cursor: pointer; }
  .tub .shell { fill: var(--st-tile); stroke: var(--st-border); stroke-width: 2; }
  .tub .water { fill: var(--st-water); }
  .tub .ripple { fill: none; stroke: color-mix(in srgb, var(--st-accent) 30%, transparent); stroke-width: 2; }
  .temp { font-size: 52px; font-weight: 600; line-height: 1; letter-spacing: -1px; cursor: pointer; }
  .setpoint { display: flex; align-items: center; gap: 8px; }
  .round { width: 44px; height: 44px; border-radius: 12px; border: 1px solid var(--st-border); background: var(--st-tile); font-size: 20px; }
  .sp-val { display: flex; flex-direction: column; align-items: center; min-width: 76px; }
  .sp-num { font-size: 20px; font-weight: 600; }
  .heat { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--secondary-text-color); }
  .heat.on { color: var(--st-heat); }
  .presets { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
  .chip { height: 40px; border-radius: 12px; border: 1px solid var(--st-border); background: var(--st-tile); font-size: 13px; font-weight: 600; }
  .chip.active { border-color: var(--st-accent); background: color-mix(in srgb, var(--st-accent) 20%, transparent); color: var(--st-accent); }
  .tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
  .tile { min-height: 84px; border-radius: 14px; padding: 10px; display: flex; flex-direction: column; justify-content: space-between; align-items: flex-start; text-align: left; border: 1px solid var(--st-border); background: var(--st-tile); }
  .tile.on { border-color: color-mix(in srgb, var(--st-accent) 55%, transparent); background: color-mix(in srgb, var(--st-accent) 18%, transparent); }
  .tile.light.on { border-color: color-mix(in srgb, var(--st-light) 55%, transparent); background: color-mix(in srgb, var(--st-light) 18%, transparent); }
  .t-kind, .t-state { font-size: 12px; color: var(--secondary-text-color); }
  .t-label { font-size: 15px; font-weight: 600; }
  .lower { display: flex; gap: 8px; }
  .box { flex: 1; background: var(--st-tile); border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 4px; cursor: pointer; }
  .box.wide { flex: 1.5; gap: 8px; cursor: default; }
  .rems { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
  .rem { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 2px; cursor: pointer; }
  .rem.due .strong { color: var(--st-heat); }
  .footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--secondary-text-color); border-top: 1px solid var(--st-border); padding-top: 12px; }
  .ghost { display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 12px; border-radius: 10px; border: 1px solid var(--st-border); background: transparent; font-size: 12px; }
  .c-row { display: flex; align-items: center; gap: 12px; }
  .c-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .c-temp { font-size: 30px; font-weight: 600; cursor: pointer; }
  .c-buttons { display: flex; gap: 6px; align-items: center; }
  .mini { flex: 1; height: 44px; border-radius: 12px; border: 1px solid var(--st-border); background: var(--st-tile); font-size: 12px; font-weight: 600; }
  .mini.on { border-color: color-mix(in srgb, var(--st-accent) 55%, transparent); background: color-mix(in srgb, var(--st-accent) 18%, transparent); }
  .mini.light.on { border-color: color-mix(in srgb, var(--st-light) 55%, transparent); background: color-mix(in srgb, var(--st-light) 18%, transparent); }
  .c-buttons .pill { flex: 1.2; justify-content: center; }

  .tile.light.on.cycle, .mini.light.on.cycle {
    border-color: color-mix(in srgb, #9b6bff 55%, transparent);
    background: linear-gradient(115deg, rgba(155,107,255,.24), rgba(79,142,247,.24), rgba(63,200,200,.24),
      rgba(87,194,122,.24), rgba(232,197,71,.24), rgba(242,154,69,.24), rgba(229,83,75,.24), rgba(155,107,255,.24));
    background-size: 300% 100%;
    animation: st-flow 8s linear infinite;
  }
  @keyframes st-flow { from { background-position: 0% 50%; } to { background-position: 300% 50%; } }
  @media (prefers-reduced-motion: reduce) {
    .tile.light.on.cycle, .mini.light.on.cycle { animation: none; }
  }

  @container (max-width: 460px) {
    .hero { gap: 14px; }
    .hero .tub { width: 112px; height: 112px; }
    .temp { font-size: 42px; }
    .setpoint { position: relative; }
    .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .tile { min-height: 72px; }
    .lower { flex-direction: column; }
    .round { width: 44px; height: 44px; }
  }
  @container (max-width: 340px) {
    .hero { flex-direction: column; align-items: stretch; }
    .hero .tub { align-self: center; }
    .presets { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
</style>`;

if (!customElements.get("smarttub-card")) {
  customElements.define("smarttub-card", SmartTubCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "smarttub-card",
    name: "SmartTub",
    description: "Hot tub control: temperature, presets, jets, lights, filtration, maintenance and cloud health.",
    preview: true,
    documentationURL: "https://github.com/sschouten/Smarttub#-smarttub-card",
  });
  console.info(`%c SMARTTUB-CARD %c ${CARD_VERSION} `, "color:#fff;background:#3fb5c8;font-weight:600", "color:#3fb5c8");
}
