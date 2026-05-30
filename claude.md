# openHAB 2 Configuration

Textual config for an openHAB 2.x instance on a Raspberry Pi (openHABian).

## Layout
- items/        – Item definitions (.items)
- things/       – Thing/binding definitions (.things)
- rules/        – Rules in openHAB DSL (.rules)
- sitemaps/     – UI sitemaps (.sitemap)
- persistence/  – Persistence strategies (.persist)
- transform/    – Map/JS transforms

## Goals when reviewing
- Flag deprecated openHAB 2 syntax and bindings
- Find duplicated/unused Items and Rules
- Suggest rule simplifications and error handling
- Do NOT invent bindings/Things that aren't already present

## Constraints
- openHAB 2.x DSL, not OH3/4 — keep syntax compatible unless I ask to upgrade.