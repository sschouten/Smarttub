# Changelog

## 1.5.1 — 2026-11-10

- Removed: the comparison with the built-in SmartTub integration and its
  repair issue *Built-in SmartTub integration changed*. The issue appeared
  after every Home Assistant release that touched the built-in integration
  (such as 2026.11) and suggested removing this integration. An issue left
  behind by an earlier version is removed automatically.
- Home Assistant 2026.11: the config entry methods return `None` and unload
  with `async_unload_platforms_or_raise`, as the new convention asks; earlier
  releases keep the boolean.
- Tests run against Home Assistant 2026.10.4 and 2026.11.1.

## 1.5.0 — 2026-11-03

- New: energy sensors *Energy today*, *Energy yesterday* and *Energy this
  month* (kWh), fetched every 30 minutes. *Today* and *this month* can be added
  to the Energy dashboard. The SmartTub cloud reports energy in 1/22 kWh; the
  values match the SmartTub app ("estimates based on 240 V", UTC days).
- `smarttub.get_energy_usage` returns `kwh` for every bucket.
- Confirmed: setting the spa clock (1.4.1) works; it has minute resolution.

## 1.4.1 — 2026-11-03

- Fix: setting the spa clock failed with *405 Method Not Allowed*.
  python-smarttub sends the date/time with `POST /config`; the cloud only
  accepts `PATCH /config` (like temperature and heat mode). The fork now sends
  it itself and remembers which payload shape the cloud accepts.
- Clock offset sensor shown without decimals.

## 1.4.0 — 2026-11-03

- New: *Clock offset* sensor — how many minutes the spa clock is ahead or
  behind Home Assistant. The filtration schedule runs on the spa clock, so a
  missed daylight saving time change shifts the filtration cycles.
- New: *Sync clock* button — sets the spa clock to Home Assistant's time.
- New: action `smarttub.set_date_time` — set the spa date and/or time
  manually; without data it syncs with Home Assistant.
- New option *Keep the spa clock in sync* (off by default): corrects the spa
  clock automatically when it is 3 minutes or more off (at most once an hour).

## 1.3.0 — 2026-11-03

Adopted from Home Assistant 2026.11:

- Error details are only fetched while the spa reports an error code (this was
  often the slowest call).
- Multiple spas are polled concurrently.
- Thermostat uses the native temperature API on 2026.11+ (no deprecation
  warnings) and the old API on earlier releases.
- Services are registered once at startup (`services.py`).
- Password field marked as secret.

New:

- Lock entities for the spa's control locks (temperature and spa lock enabled;
  access/maintenance disabled by default).
- Diagnostic sensors: cellular signal strength and quality, last Wi-Fi
  connection (only for spas that report them).
- Action `smarttub.get_energy_usage`: energy usage per day or month as
  reported by the SmartTub cloud.
- Device info shows the controller firmware and SmartTub link version.

Fixed:

- A spa in REST heat mode no longer breaks the thermostat (not mapped
  upstream); `rest` is shown as preset while active.
- Diagnostics downloads no longer contain the spa's GPS location (not
  redacted upstream).

## 1.2.0 — 2026-11-03

- Card: colour-cycling light modes (colour wheel, colour loop, party,
  dynamic, slow/fast wheel) show a slowly rotating rainbow on the tub rim and
  the light tile. Respects the system's reduced-motion setting.
- Note: the SmartTub cloud reports the selected light mode, not the colour
  that is lit at a given moment while a cycling mode runs.

## 1.1.1 — 2026-11-03

- Fix: exterior light zones (e.g. corner lights) now turn on in white. They
  only support white; the default purple was accepted by the SmartTub cloud
  but ignored by the spa. Exterior zones offer only the `white` effect and
  report `zone_type: exterior`.
- Changing only the brightness of a light that is on keeps its current effect.
- Card: exterior zones are labelled *Exterior* / *Buiten*; the tub rim follows
  the interior lights only.

## 1.1.0 — 2026-11-02

- New: `custom:smarttub-card`, shipped with the integration and registered
  automatically. Full and compact variant, automatic spa discovery, light/dark
  theme, English and Dutch, visual editor, responsive layout.
- New: ready-made dashboards in `dashboards/` (built-in cards, Mushroom, and
  the SmartTub card; English and Dutch).

## 1.0.1 — 2026-11-02

- Neutral wording for the "built-in integration changed" repair issue (EN/NL).
- Documentation: extended README, issue and pull request templates,
  contributing guide.

## 1.0.0 — 2026-11-02

Initial release, based on the built-in SmartTub integration of Home Assistant
2026.10.4.

- `fullStatus` gets its own timeout (default 30 s instead of a shared 10 s).
- `reminders` and `errors` get their own timeout (default 20 s); on failure the
  last known values are kept and the update does not fail.
- The last good data is kept until N polls in a row failed (default 5).
- Poll interval backs off with jitter while failing (up to 600 s).
- Commands: 45 s timeout, readable errors, optimistic state for commands the
  API accepted but did not confirm in time.
- Failing first poll retries the setup instead of crashing the platforms.
- Reminders that appear after setup get an entity.
- Diagnostic entities: API connection, last successful poll, last poll
  duration, consecutive failed polls, refresh button.
- Options flow for all timeouts, threshold and back-off.
- Repair issues: API unreachable; built-in integration changed.
- Poll statistics in the diagnostics download.
- English and Dutch translations.
