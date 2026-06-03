# openHAB 2 → 5 Migration — Intake (COMPLETED)

> Discovery complete. This is the filled intake that feeds the runbook
> (`docs/migration-runbook.md`). Secret **values** are deliberately omitted — only their
> existence and location are recorded.

---

## 1. Hardware & OS

| Item | Answer |
|---|---|
| Old Pi model / RAM | Raspberry Pi 4 Model B Rev 1.4 |
| Old OS + bitness | openHABian; stays on OH2 so bitness irrelevant (not upgraded) |
| How OH2 was installed | openHABian |
| Exact OH2 version | **2.5.12** (final 2.5.x) |
| New Pi model / RAM / boot media | Pi 4 (≥2 GB) or Pi 5, **64-bit**, SSD preferred — TBD at purchase |
| New Pi hostname / static IP | openHAB5 / 192.168.0.41 |

## 2. MQTT broker (Mosquitto)

| Item | Answer |
|---|---|
| Where does Mosquitto run? | **On the old Pi** (running since Mar 2026) |
| Broker IP/host + port | 192.168.0.40:1883 |
| Broker credentials / TLS | Confirm in pushover/services; record existence only |
| Move broker or keep? | **KEEP on old Pi** (old Pi stays up for gate tile anyway) |
| Devices point by IP? | Yes — but **Tasmota**, trivial to repoint. No need: broker stays put. |
| MQTT field devices | **Tasmota** (`tasmota/discovery/...`, `tele/.../LWT`, `stat/...`) |
| Action | Give old Pi a **DHCP reservation** so `<OLD_PI_IP>` is permanent |

## 3. Bindings & integrations

| Binding/action | Keep/Drop | Notes |
|---|---|---|
| mqtt (2.x, bridge `mosquitto`) | **KEEP** | Bridge → `<OLD_PI_IP>` |
| hue | **KEEP** | Re-add bridge + press button; ~26 Things (bridge + lights) |
| sonos | **KEEP** | Auto-rediscovers (7 players: PLAY1/3, CONNECT, CONNECTAMP) |
| tplinksmarthome | **KEEP** | LAN-local, no cloud; 3× HS110 |
| astro | **KEEP** | Set system/Thing geolocation on new Pi |
| systeminfo | **KEEP** | No auth |
| pushover (action) | **KEEP** | Keys in `services/pushover.cfg`; ~35 send sites / 9 rule files |
| exec | **DROP** | Unused — no `executeCommandLine`, empty whitelist |
| expire1 | **DROP** | No items use `expire=`; no metadata conversion needed |
| mqtt1 | **DROP** | Already removed earlier |
| smartthings | **DROP** | Binding dead (Groovy shutdown); retire except gate (see §9) |
| ipcamera (HIKVISION) | **DECIDE** | BlueIris topics live; rules commented — keep only if used |
| Transformations | KEEP map, jsonpath, regex | No `.js` files exist → GraalJS change is a non-issue |

## 4. Things & JSONDB

| Item | Answer |
|---|---|
| Textual or UI? | **ALL UI-created** — live in JSONDB, not in repo |
| Approach | **Regenerate as textual `.things`** (Claude Code from JSONDB export) |
| Source files | `org.eclipse.smarthome.core.thing.Thing.json` (508 KB) + `...ItemChannelLink.json` |
| Inventory | ~26 hue, 7 sonos, 3 tplink, 1 mqtt:topic, astro sun×2 + moon, systeminfo, ipcamera (+ ~40 SmartThings sub-Things being retired) |

## 5. Persistence / historian

| Item | Answer |
|---|---|
| Services | influxdb (1.x, `openhab_db`) + mapdb |
| Keep history? | **No time-series.** Keep only `Temp_*` **record** values (sitemap "Records" frame) |
| Method | Copy mapdb `storage.mapdb*` → new Pi for restoreOnStartup; fallback = manual re-seed of `Temp_All_*`/`Temp_Year_*` |
| New Pi persistence | rrd4j (default, future charts) + mapdb (restore). InfluxDB **not** migrated; charts start fresh |
| Note | All-time max = **41.7** looks like a sensor spike → consider re-seeding clean |

## 6. Rules & scripting

| Item | Answer |
|---|---|
| Languages | **DSL only** — no JS/Jython/Groovy. GraalJS/GraalPy changes don't apply |
| External scripts via exec? | None |
| expire usage in rules? | None |
| `.rulesx` (disabled) | **DROP all 5** (blanket, christmas, homebrew, irrigation, presence) — not wanted |

## 7. UI

| Item | Answer |
|---|---|
| UI in use | **Basic UI** (sitemaps) — carries over unchanged |
| HABPanel? | No |
| Custom icons/HTML? | TBD — check `conf/html`, `conf/icons` during Phase 2 |
| Paper UI | Removed in OH5 → admin via **Main UI** (no functional impact) |

## 8. Network, remote access & external integrations

| Item | Answer |
|---|---|
| openHAB Cloud / myopenhab | **In use** (`misc=openhabcloud`) → re-register new instance, same account |
| Alexa / Google Assistant | Not used (gate chosen non-voice) |
| Remote access | Tailscale (confirm new Pi on tailnet at cutover) |
| Grafana | **Not installed** — charts are native openHAB, not Grafana |
| Other IP/hostname refs | BlueIris live (`BlueIris/app`, `BlueIris/status`); ipcamera at 192.168.0.40 |
| Reverse proxy | TBD — none known |

## 9. SmartThings & Z-Wave

| Item | Answer |
|---|---|
| Overall | **Retire as automation platform; keep ONLY the gate** |
| Z-Wave → ZST39 (EU 868.42 MHz) | Multisensor (GH1-MS1, active), Smoke Kitchen (GK1-SA1, active); **revive-or-drop:** Smoke Landing (FL1-SA2, offline'20), Energy Monitor (GO1-EM1, offline'24), Scene Controller (FB1-SC1, offline'23) |
| Zigbee coordinator | **Not needed** — no automated Zigbee devices |
| Blinds (Brunt, cloud-locked) | **Local MQTT→Brunt bridge** (Python `brunt` lib) reusing existing topics → openHAB unchanged. Cloud-dependent; unofficial API risk |
| Gate | Virtual switches = app front-end. **Keep on old Pi's SmartThings** for the **Android Auto tile** (non-voice), state-synced from openHAB via MQTT. openHAB can't provide an AA tile (Samsung/Google first-party only) |
| Cloud-only (Brunt VIPER, Coffee switch) | Not in openHAB — not migrated |

## 10. Secrets handling

| Secret | Location | Transfer |
|---|---|---|
| Pushover token + user key | `services/pushover.cfg` | scp to new Pi, out of git |
| Mosquitto broker creds | broker config (if set) | stays on old Pi |
| Brunt app login | new — for the bridge | `/etc/brunt-bridge/secrets.env`, chmod 600, not in git |
| openHAB Cloud creds | self-generated | new UUID/secret on new Pi |

---

### Status: discovery complete — ready to build per `docs/migration-runbook.md`.
