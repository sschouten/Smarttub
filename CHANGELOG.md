# Changelog

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
