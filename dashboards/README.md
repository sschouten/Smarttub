# Dashboards

Ready-made dashboards for the SmartTub integration. All use the **sections**
layout: one column on a phone, up to three on a desktop.

| File | Cards | Language | Entity IDs to replace |
|---|---|---|---|
| [`smarttub-card.yaml`](smarttub-card.yaml) | `custom:smarttub-card` (ships with this integration) | automatic EN/NL | only in the two history graphs |
| [`builtin.en.yaml`](builtin.en.yaml) / [`builtin.nl.yaml`](builtin.nl.yaml) | Built-in cards only | English / Dutch | yes |
| [`mushroom.en.yaml`](mushroom.en.yaml) / [`mushroom.nl.yaml`](mushroom.nl.yaml) | [Mushroom](https://github.com/piitaya/lovelace-mushroom) + built-in | English / Dutch | yes |

## Using a dashboard

1. **Settings → Dashboards → Add dashboard → New dashboard from scratch**.
2. Open it, then **⋮ → Edit dashboard → ⋮ → Raw configuration editor**.
3. Paste the file's contents and save.
4. Replace `jacuzzi_j_435` with your spa's entity prefix (the part between
   the dot and `_thermostat` of your thermostat entity), using search & replace
   in the editor (Ctrl/Cmd + F).

The reminder entities depend on your spa model (Jacuzzi spas have
ProClarity/ClearRay/water reminders); remove or rename the ones you don't have.
