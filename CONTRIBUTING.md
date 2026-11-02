# Contributing

Bug reports, ideas and pull requests are welcome.

## Ground rules

- **Never change unique IDs** of existing entities — users' entities, history
  and automations depend on them. `tests/test_resilience.py::test_unique_ids_unchanged`
  guards this.
- Keep the code close to the built-in integration, so changes from Home
  Assistant core can be merged easily.
- New user-facing text goes into both `translations/en.json` and
  `translations/nl.json`.

## Running the tests

The tests use the Home Assistant core test harness. The script clones the
matching core release, installs Home Assistant and runs the suite:

```bash
scripts/run_core_tests.sh 2026.10.4
```

Requirements: `git` and [uv](https://docs.astral.sh/uv/).

## Releasing

1. Update `version` in `custom_components/smarttub/manifest.json`.
2. Add an entry to `CHANGELOG.md`.
3. Create a GitHub release with tag `v<version>` (the release workflow checks
   that the tag matches the manifest).
