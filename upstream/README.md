# Upstream patch for Home Assistant core

This folder contains the core of the fix as a minimal patch for the built-in
SmartTub integration in [home-assistant/core](https://github.com/home-assistant/core):

| File | Contents |
|---|---|
| [`core-smarttub-timeouts.patch`](core-smarttub-timeouts.patch) | Separate timeouts for status and reminders/errors, last known reminders/errors on failure, retry setup when the first poll fails, plus tests |
| [`PR.md`](PR.md) | Pull request description |

The patch contains only the minimal bug fix. The extra features of this
integration (stale-data hold, back-off, diagnostic entities, options flow,
repairs) are not part of it.

Tested against Home Assistant 2026.10.4 (46 tests pass). Apply on core `dev`:

```bash
git apply upstream/core-smarttub-timeouts.patch
pytest tests/components/smarttub
```
