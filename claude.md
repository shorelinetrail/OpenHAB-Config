# openHAB 2 Configuration — Project Context

Textual config for an openHAB 2.x instance on a Raspberry Pi (openHABian).
This repo is version-controlled; changes are pushed from a dev PC and pulled
onto the Pi, where openHAB hot-reloads them.

## Layout
- items/        – Item definitions (.items)
- things/       – Thing/binding definitions (.things)
- rules/        – Rules in openHAB 2 DSL (.rules). NOTE: .rulesx files are DISABLED — ignore them.
- sitemaps/     – UI sitemaps (.sitemap)
- persistence/  – Persistence strategies (.persist)
- transform/    – Map/JS transforms
- docs/FDS.md   – Functional Design Specification (living source of truth)

## Source of truth — Functional Design Specification
- `docs/FDS.md` is the FDS for this system and the authoritative description of behaviour.
- ALWAYS read `docs/FDS.md` at the start of a task, before making any changes.
- WHENEVER you modify any .items/.things/.rules/.sitemap/.persist file, you MUST update
  `docs/FDS.md` in the SAME change so the spec never drifts from the config.
- Append a row to the §1.1 Revision History for every change (date, what, files, why).
- When a change resolves a §14 Known Issue, update that section too.
- If I describe an out-of-repo change (broker, bindings, addons.config on the Pi),
  record it in the FDS — those files are not in this repo and you can't see them.

## Naming conventions
See FDS §6. Items follow: <ZONE><index><DEVICE-TYPE><n>_<measurement>
(e.g. FB1SS6_temp). Groups use a `g` prefix (e.g. gTemperature). Preserve this scheme;
flag deviations rather than "correcting" them silently.

## System facts
- MQTT is 100% the 2.x binding (channel="mqtt:topic:mosquitto:..."). The legacy v1
  MQTT binding (mqtt1) and v1 mqtt action have been removed — do NOT reintroduce v1 syntax.
- Active bindings: mqtt(2.x), hue, sonos, tplinksmarthome, smartthings, astro,
  systeminfo, exec, expire. Outbound alerts via the pushover action.

## When reviewing
- Flag deprecated openHAB 2 syntax and bindings.
- Find duplicated/unused Items and Rules — but treat "unused" as a CANDIDATE list;
  Items may be referenced in sitemaps/UI you can verify, so do not delete without confirming.
- Cross-check: list Items referenced in rules/sitemaps that are not defined in items/.
- Suggest rule simplifications, null/undef handling, and timer-leak fixes.

## Constraints
- This is openHAB 2.x DSL, NOT OH3/4. Keep syntax compatible unless I explicitly ask to upgrade.
- Do NOT invent bindings, Things, or behaviour not present in the files. Mark gaps as TODO.
- Propose edits as diffs for review; do not assume runtime state I haven't told you.

## Migration in progress
Migrating OH 2.5.12 → OH5 on a new Pi (parallel build). Intake: docs/migration-intake.md.
Runbook: docs/migration-runbook.md. Old Pi 4 stays as Mosquitto broker + SmartThings gate host.