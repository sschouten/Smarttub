# SmartTub (resilient) for Home Assistant

A drop-in replacement for the built-in Home Assistant **SmartTub** integration
(Jacuzzi, Sundance, …) that keeps working while the SmartTub cloud API is slow.

> **Temporary fork.** Remove it as soon as Home Assistant ships a fix for
> [home-assistant/core#188209](https://github.com/home-assistant/core/issues/188209) /
> [#188892](https://github.com/home-assistant/core/issues/188892). The integration
> raises a repair issue when the built-in integration changes, so you know when
> to check.

## The problem

Since late October 2026 the SmartTub cloud API answers in 0.3–15 s per call.
The built-in integration fetches `fullStatus`, `reminders` and `errors`
together inside a single **10 s** timeout. When one of them is slow, the whole
update fails and *every* entity becomes `unavailable` — even though the status
itself arrived. Users see hundreds of interruptions a day and
`Timeout fetching smarttub data` in the log.

Commands are affected as well: jets are toggled with a 5 s timeout while the
library waits for a confirmation that takes longer, so toggles report an error
although the tub executes them.

## What this fork changes

| | Built-in (2026.10) | This fork (default, configurable) |
|---|---|---|
| `fullStatus` timeout | 10 s, shared | **30 s**, own timeout |
| `reminders` / `errors` | must succeed | own **20 s** timeout, last known values kept on failure |
| One failed poll | everything `unavailable` | last good data kept until **5** polls in a row failed |
| While failing | polls every 60 s | interval doubles (with jitter) up to **600 s**, restored on success |
| Commands | 5 s (pumps), no timeout (heater) | **45 s**, unconfirmed commands shown optimistically |
| First poll fails | entry loads without data, platforms crash | setup is retried |
| Reminder missing at setup | never created | added as soon as it appears |

Additions:

* **Diagnostic entities** (enabled by default): *API connection*,
  *Last successful poll*, *Last poll duration* (per-call durations as
  attributes), *Consecutive failed polls*, and a *Refresh* button.
* **Options flow** (Settings → Devices & services → SmartTub → Configure):
  poll interval, status timeout, reminders/errors timeout, command timeout,
  failed polls before unavailable, maximum back-off.
* **Repairs**: an issue when the API is unreachable past the threshold (cleared
  automatically), and one when the built-in integration has changed and this
  fork may no longer be needed.
* **Diagnostics download** includes poll statistics (credentials redacted).
* English and Dutch translations.

Domain (`smarttub`) and all unique IDs are identical to the built-in
integration, so existing entities, history, dashboards and automations keep
working. This is covered by a test.

## Installation

### HACS (public repository)

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/sschouten/Smarttub`,
   type **Integration**.
2. Install **SmartTub (resilient)** and restart Home Assistant.

### Manual

1. Copy `custom_components/smarttub` to `/config/custom_components/smarttub`.
2. Restart Home Assistant.

No reconfiguration is needed: the existing SmartTub config entry is picked up
by the custom integration. Home Assistant logs a warning that a custom
integration overrides the built-in `smarttub`; that is expected.

## Verifying

* Settings → System → Logs: no more `Timeout fetching smarttub data`.
* `binary_sensor.<spa>_api_connection` is `on`; `sensor.<spa>_last_poll_duration`
  shows the real API latency, its attributes the per-call durations.
* `sensor.<spa>_consecutive_failed_polls` stays low; entities only become
  unavailable after the configured threshold.

## Removing (rollback)

1. Delete `/config/custom_components/smarttub` (or remove it in HACS).
2. Restart Home Assistant.

The built-in integration takes over the same config entry and entities. The
five diagnostic entities become orphaned; remove them under
Settings → Entities if you like. Options are ignored by the built-in
integration.

## Development

Tests run inside the Home Assistant core test harness against the release the
fork was built on:

```bash
scripts/run_core_tests.sh 2026.10.4
```

## Credits and license

Based on the built-in SmartTub integration of
[Home Assistant](https://github.com/home-assistant/core) (Apache License 2.0,
original code owner [@mdz](https://github.com/mdz)) and the
[python-smarttub](https://github.com/mdz/python-smarttub) library. This fork is
also Apache-2.0 licensed. Not affiliated with Jacuzzi or SmartTub.
