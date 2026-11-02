# Upstream pull request: SmartTub polling timeouts

Minimal fix for the built-in integration, prepared from this fork. Apply on
top of `home-assistant/core` `dev`:

```bash
git apply upstream/core-smarttub-timeouts.patch
pytest tests/components/smarttub
```

The patch was tested on the 2026.10.4 tag (46 tests pass). Re-check that it
applies on `dev` before opening the PR.

---

**Title:** Fix SmartTub becoming unavailable when the cloud API is slow

## Proposed change

The SmartTub cloud API currently answers in up to ~15 s per call. The
coordinator fetches `fullStatus`, `reminders` and `errors` together inside one
10 s timeout, so a single slow call fails the whole update and makes every
entity unavailable, even when the status itself arrived.

- `fullStatus` gets its own timeout, raised to 30 s.
- `reminders` and `errors` get their own 20 s timeout. If one of them fails,
  the last known value is kept and the update still succeeds.
- `TimeoutError` and `aiohttp.ClientError` are converted to `UpdateFailed`.
- The first refresh uses `async_config_entry_first_refresh()`. Previously a
  failing first poll left `coordinator.data` empty and the platforms crashed;
  now setup is retried. The diagnostics test for "no coordinator data" is
  removed because that state can no longer occur.

## Type of change

- [x] Bugfix (non-breaking change which fixes an issue)

## Additional information

- Fixes #188209, fixes #188892

## Checklist

- [x] Tests have been added to verify that the new code works.
- [x] The code has been formatted using Ruff.
