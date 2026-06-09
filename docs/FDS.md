# Functional Design Specification — Home Automation System

> **How to use this file:** Place at `docs/FDS.md` in the repo. It is the living
> source of truth for system behaviour. Claude Code reads it before every task and
> updates it (plus the Revision History) with every change — see the FDS rule in
> `CLAUDE.md`. Sections marked _(TODO: confirm)_ contain values inferred from the
> config and must be verified against the running system.

---

## 1. Document Control

| Field | Value |
|---|---|
| Document title | Home Automation System — Functional Design Specification |
| System | openHAB 2.x on Raspberry Pi (openHABian) |
| Owner | _(TODO: name)_ |
| Status | Draft |
| Source repo | `<github>/OpenHAB-Config` |

### 1.1 Revision History

_Newest at top. One row per change. Claude Code appends a row for every modification._

| Date | Version | Change | Files affected | Author |
|---|---|---|---|---|
| 2026-06-09 | 0.21 | Added the first Sonos **preset** ("BBC Radio 2"): new `Sonos_Preset_BBCR2` sitemap switch (ON=start/OFF=stop) + a rule (`sonos.rules`) that groups Office/Sun Room/Bedroom under Kitchen (coordinator, hard-coded UDN), sets all four to 25 %, and plays the saved "My Radio Stations" entry "BBC Radio 2" via the Kitchen `radio` channel; Stop pauses the group (stays grouped). Added `Sonos_Kitchen_Radio` + `Sonos_Kitchen_Favorite` (fallback) Items and a sitemap "Presets" frame | items/items.items, rules/sonos.rules, sitemaps/main.sitemap, docs/FDS.md | Claude Code |
| 2026-06-09 | 0.20 | Reworded all smoke-detector Pushover notifications (`smoke.rules`): title is now `🔥 <Location> Smoke Detector` (e.g. "🔥 Kitchen Smoke Detector") and the body carries the event — `SMOKE DETECTED`/`HEAT DETECTED`/`Tamper alarm`/`System fault`/`Low battery` (active), `✅ <event> cleared` (recovery, title without the fire emoji), `Battery low (<pc>%)`, `Offline - …` (liveness). No change to priority/emergency-receipt logic or triggers | rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-09 | 0.19 | Hardened the `Water Butt Level` rule's rain-overflow drain (`irrigation.rules`): NULL/UNDEF guard + early return; compute level-% locally and threshold on it (fixes the async stale-state race that delayed the drain by one sample); `!=OFF`/`!=ON` valve guards so an unknown relay state still drives the drain; and a **flow-verified drain** — 30 s after opening at >95%, if `GY1FT1_flow3` shows no flow while still full, retry the open + one high-priority Pushover ("OVERFLOW RISK"). Added a `pushoverHigh` (priority-1) lambda. Routine open/close stays log-only (no alert spam) | rules/irrigation.rules, docs/FDS.md | Claude Code |
| 2026-06-09 | 0.18 | Migration (out-of-repo Pi setting): the new Pi5's 7 Sonos players showed `OFFLINE / COMMUNICATION_ERROR / "not available in local network"`. Root cause was openHAB jUPnP binding UPnP discovery to a non-LAN interface on the multi-homed Pi (`eth0` 192.168.0.57 + Tailscale `100.x`); fixed by setting **Network Settings → Primary Address = `192.168.0.57/24`**. No config change — Sonos Items/Things/rules/sitemap were already correct and OH5-valid (verified thing types + channels against the OH5 binding). Also corrected the new-Pi IP (`.41`→`.57`) in migration-intake and added the Tailscale UPnP caveat to the runbook | docs/FDS.md, docs/migration-intake.md, docs/migration-runbook.md | Claude Code |
| 2026-06-08 | 0.17 | Fix: the `Fibaro Smoke Detector Last Update` rule threw `getName() on null` — `triggeringItem` is not reliably populated for `received update` triggers. Split it into per-detector rules (`Kitchen`/`Landing Smoke Detector Last Update`) that reference their own `_LastUpdate` directly, so the stamp no longer depends on `triggeringItem` | rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.16 | Added `GK1SA1_LastUpdate` / `FL1SA2_LastUpdate` (DateTime) for the Fibaro detectors, mirroring the shed's last-seen. New `Fibaro Smoke Detector Last Update` rule stamps them on each `_temp`/`_battpc` report (real wakeups; excludes the alarm-seed so it isn't faked at startup). Added to the Kitchen/Landing sitemap frames | items/items.items, rules/smoke.rules, sitemaps/main.sitemap, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.15 | `smoke.rules` liveness: replaced deprecated `DateTimeType.getZonedDateTime()` with `getInstant()` (compared against `now.minusHours(2).toInstant`) to clear the OH5 model-validation deprecation warning. No behaviour change | rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.14 | Smoke/heat emergency alerts now auto-cancel on recovery: added a `cancelPushoverEmergency` lambda + an in-memory `emergencyReceipts` map (Item name → receipt) to `smoke.rules`; the Alarm rule stores the priority-2 receipt on `_smoke`/`_heat` alarm and `cancelPriorityMessage`s it on the `0→1` clear (wiring up what gate/heating/status only scaffolded) | rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.13 | Added Pushover titles (`🔥 <location> <type>`, `✅ … Cleared`) to all smoke alerts, and mirrored the alerting onto the shed MQTT unit `GY1SA4`: added `GY1SA4_smoke/_tamper` to `gSmokeAlarm` (reusing the Alarm rule), `GY1SA4_battpc` to the Battery Low rule, and a Shed heartbeat-staleness check (`GY1SA4_LastUpdate` >2 h) to the Liveness rule | items/items.items, items/mqtt.items, rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.12 | Built smoke-detector alerting: added `gSmokeAlarm` group (the 10 Fibaro alarm Items) and three rules in `smoke.rules` — **Smoke Detector Alarm** (`Member of gSmokeAlarm changed`; Pushover emergency pri-2 for smoke/heat, normal for tamper/fault/battery, all-clear on recovery), **Smoke Detector Battery Low** (`_battpc` < 20 %), **Smoke Detector Liveness** (6-hourly Z-Wave Thing-status watchdog). Refactored the Init rule onto `gSmokeAlarm`. Uses the standard per-file `pushover`/`pushoverEmergency` lambdas | items/items.items, rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.11 | Added `Smoke Detector Alarm Init` rule (`System started`): seeds any unreported (NULL/UNDEF) `gSmoke` alarm Item to `1` (OK), so the Fibaro Z-Wave notification channels show "OK" instead of "Unknown" until their first event/wakeup; a real `0`=Alarm report overrides. Excludes `_temp`/`_battpc` | rules/smoke.rules, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.10 | Fibaro FGSD002 fix after first link-up: the `alarm_*` channels deliver a **numeric notification** (`0`/`1`), not Switch, so changed the 10 alarm Items from `Switch` to `Number`; corrected `alarm.map` polarity to **0=Alarm, 1=OK** (confirmed from idle detectors reporting `1`, matching the old MQTT `smoke.map` convention) and added `0`/`1` keys. `_temp`/`_battpc` unchanged and working | items/items.items, transform/alarm.map, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.9 | Added two revived **Fibaro FGSD002** Z-Wave smoke detectors — `GK1SA1_*` (Kitchen, `zwave:device:a76def7407:GK1-SA1`) and `FL1SA2_*` (Landing, `…:FL1-SA2`), 7 channels each (smoke/heat/tamper/system/battery alarms + temperature + battery level). Items defined unbound in `items.items` (channel→item links UI-managed in JSONDB, per the Z-Wave convention) and added to `gSmoke` (previously empty); added `transform/alarm.map` (ON=Alarm/OFF=OK) and Kitchen/Landing frames to the sitemap Smoke Detection page | items/items.items, sitemaps/main.sitemap, transform/alarm.map, docs/FDS.md | Claude Code |
| 2026-06-08 | 0.8 | Renamed the smoke detector from `GK1SA1` (Kitchen) to `GY1SA4` (Shed): all six Items + `_LastUpdate`, the six MQTT Things and their `stateTopic` base (`GK1-SA1/…` → `GY1-SA4/…`, per new device firmware config), the `smoke.rules` trigger/action, and the sitemap "Smoke Detection" frame (Kitchen → Shed) | items/mqtt.items, things/mqtt.things, rules/smoke.rules, sitemaps/main.sitemap, docs/FDS.md | Claude Code |
| 2026-06-02 | 0.7 | Sonoff Status rule: add missing `GY1SS27_Online` (the only `gSonoff_IP` member with no `_Online` switch — once `ScriptServiceUtil` resolved, `getItem` threw "could not be found" and aborted the sweep), and wrap the per-member lookup in try/catch so any future IP↔Online mismatch logs a warning instead of killing the rule | items/items.items, rules/status.rules, docs/FDS.md | Claude Code |
| 2026-06-02 | 0.6 | Fix: the Phase-2a `itemRegistry` change in status.rules was invalid (`itemRegistry` is not a resolvable name in OH5 Rules DSL — runtime ERROR at line 173); reverted to `ScriptServiceUtil.getItemRegistry.getItem(...)` with `import org.openhab.core.model.script.ScriptServiceUtil` (the correct OH2→OH5 namespace move) | rules/status.rules, docs/FDS.md | Claude Code |
| 2026-06-02 | 0.5 | SmartThings→Z-Wave cutover for the Hall multisensor: added `GH1MS1_temperature` (Z-Wave MS6; gMultisensor/gTemperature) and uncommented its Hall row in the Temperature frame; moved `GH1MS1_motion` into items.items as an unbound `String` (UI-linked via `motion.map`) and removed the MQTT passthrough Item + Thing | items/items.items, items/mqtt.items, things/mqtt.things, sitemaps/main.sitemap, docs/FDS.md | Claude Code |
| 2026-06-02 | 0.4 | OH5: adopted Z-Wave binding (`binding=…,zwave` in addons.cfg); recorded that Z-Wave Things + channel links are UI-managed in JSONDB (off-repo) by design; added `transform/motion.map` to map a Z-Wave binary motion channel (ON/OFF) onto the `String GH1MS1_motion` ("active"/"inactive") via a link profile (rules unchanged); stopped tracking openHAB runtime-generated files (`runtime.cfg`, `basicui.cfg`, `rrd4j.cfg`, `automation/`, `tags/`, `yaml/`); added Basic UI (`ui = basic`) | services/addons.cfg, docs/FDS.md, transform/motion.map, .gitignore | Claude Code |
| 2026-05-31 | 0.3 | Generated textual Things from JSONDB for hue/sonos/tplinksmarthome/astro/systeminfo/ipcamera; pointed mqtt broker bridge at the old Pi (192.168.0.40); confirmed `astro:sun:c7d0dedc` is the real −30-min "Offset" sun Thing | things/hue·sonos·tplinksmarthome·astro·systeminfo·ipcamera.things, things/mqtt.things, docs/FDS.md | Claude Code |
| 2026-05-31 | 0.2 | Fixed duplicate "Gate Offline" rule name, all-time temp copy-paste bug, and Online-switch mislabels; removed orphaned `GY1SS25_Online`/`myClock` + `de.map`/`en.map`/`numberToClock.js`; left `gHeating` OR-order unchanged (drives boiler) | status.rules, temperatures.rules, items.items, main.sitemap, transform/ | Claude Code |
| 2026-05-30 | 0.1 | Initial FDS populated from config | (all) | Claude Code |

---

## 2. Purpose & Scope

This system provides whole-home monitoring and automation for a two-storey house and
its garden/outbuildings, running on openHAB 2.x. It covers: zoned central-heating
control (per-room thermostatic radiator switching with scheduling and boiler firing),
schedule- and sensor-driven lighting (Philips Hue + Sonoff relays, motion, dusk/evening/
night and "dark-daytime" modes), motorised blinds, presence-based behaviour, multi-room
Sonos audio, smart-plug energy metering and tariff costing, irrigation/water-butt
management, gate control, smoke detection, environmental telemetry (temperature,
humidity, pressure, illuminance, gas, flow), device health monitoring, and Pushover
notifications.

This FDS describes **how** the configuration is implemented to meet the owner's
requirements. It does **not** cover: provisioning of the Raspberry Pi/openHABian OS,
the Mosquitto broker, network hardware, the Tasker phone app that feeds presence, the
Blue Iris CCTV server, or any binding/add-on state held outside this repo (JSONDB).

---

## 3. Reference Documents & Standards

| Reference | Relevance |
|---|---|
| openHAB 2.x documentation | Platform behaviour, binding/Thing/Item model |
| ISA-88 | _Informative_ — sequence/phase terminology (if any sequences exist) |
| ISA-95 | _Informative_ — functional hierarchy of the model |
| IEC 61511 (functional safety) | **Not applicable** — no safety-instrumented functions |
| Mosquitto MQTT broker docs | Broker configuration (out-of-repo) |

---

## 4. System Architecture

Field devices are predominantly Tasmota-flashed Sonoff/ESP nodes that publish telemetry
and accept commands over MQTT to a local Mosquitto broker; openHAB bridges to the broker
and also talks directly to Philips Hue, Sonos, TP-Link Kasa plugs, SmartThings and Astro.
Rules run the automation; InfluxDB stores history for charts; Pushover delivers alarms.

```
  Tasmota/ESP nodes (Sonoff SS/FT/EM/NM, smoke SA) --MQTT--+
  SmartThings (Arrival, Multisensor, Scene, SwitchBot) --+ |
  Philips Hue bridge --------------+                     | |
  Sonos speakers ----------+       |                     v v
  TP-Link Kasa plugs ---+  |       |                Mosquitto broker (localhost:1883)
                        v  v       v                       |
                    +-----------------------------------------+
                    |              openHAB 2.x                |
                    |  Items - Things - DSL Rules - Sitemap   |
                    +---+-------------+------------+----------+
                        |             |            |
                  BasicUI/sitemap   InfluxDB     Pushover
                  (HMI)             (trend)      (alarms)
                        |
                  Tasker (phone, Wi-Fi presence -> REST -> XM1AS1_presence)
```

| Element | Detail |
|---|---|
| Controller hardware | Raspberry Pi _(TODO: model)_ |
| Distribution | openHABian |
| OS | _(TODO: Raspberry Pi OS / Debian version)_ |
| Java runtime | _(TODO: confirm)_ |
| openHAB version | 2.x _(TODO: exact, e.g. 2.5.x)_ |
| MQTT broker | Mosquitto, openHAB Thing bridge id `mosquitto` (`host=localhost`, `port=1883`, `secure=false`, user `openhabian`) |
| Config storage | Textual (`/etc/openhab2/`), version-controlled in this repo |
| Out-of-repo state | Bindings/add-ons, managed Things (e.g. `ipcamera`, `astro`), Pushover credentials, broker config, persistence DBs |

---

## 5. External Interfaces & Bindings

| Binding / action | Version | Protocol / target | Purpose |
|---|---|---|---|
| mqtt | 2.x | MQTT → Mosquitto (`mosquitto`) | Tasmota telemetry (`tele/.../SENSOR`), status (`stat/.../STATUS5/11`), relay commands (`cmnd/.../POWER`), blinds (`POSITION`), energy meter, smoke alarm, gate, water/irrigation, and a SmartThings motion passthrough topic |
| hue | 2.x | Philips Hue bridge `001788678581` | All `*HB*_dimmer`/`_colour` bulbs (hall, landing, kitchen, glass, front door, yard), and the Hue dimmer-switch button (`GK1HS1_event`) used to toggle presence |
| sonos | 2.x | Sonos (CONNECT, CONNECT:AMP, PLAY:1, PLAY:3) | 7 speakers (Living Room, Kitchen, Office, Bedroom, Sun Room, Sun Room Aux, Workshop) — control/volume/mute/track/coordinator/add/standalone + whole-house group rules. **OH5 discovery note:** players are found via UPnP/jUPnP; on the multi-homed new Pi (eth0 + Tailscale) the UPnP interface must be pinned via Network Settings **Primary Address = `192.168.0.57/24`**, or players report "not available in local network" (see §1.1 v0.18) |
| tplinksmarthome | 2.x | TP-Link Kasa HS110 | 3 smart plugs (Office `GO1SP1`, Living Room `GL1SP2`, Bedroom `FB1SP3`) — switch/power/energy/LED/rssi/current/voltage |
| smartthings | 2.x | SmartThings | Arrival Sensor (`XM1AS1_battery`), Multisensor (`GH1MS1_*`), Hank Scene Controller (`FB1SC1_power`), Coffee Machine (`GK1SW04`) — **being migrated to Z-Wave** (sensors) on OH5 |
| zwave | (OH5) | Z-Wave mesh via serial controller (Thing UID assigned at node inclusion) | Replacing SmartThings sensors. Nodes: Hall multisensor → `GH1MS1_*`; Fibaro FGSD002 smoke detectors → `GK1SA1_*` (Kitchen, `zwave:device:a76def7407:GK1-SA1`) and `FL1SA2_*` (Landing, `zwave:device:a76def7407:FL1-SA2`). **Things + channel→item links are UI-managed in JSONDB, not in this repo** — see note below |
| astro | 2.x | Computed sun/moon (Thing `astro:sun:local`; a second UID `astro:sun:c7d0dedc` is also referenced — see §14) | Sunrise/sunset/-30-min triggers for lighting and blinds; `Astro_SunriseEnd` |
| ipcamera | 2.x | Blue Iris / IP camera snapshot (`ipcamera:HTTPONLY:cd166936`) | `cctv` Image item (Thing is managed/UI, not in repo) |
| systeminfo | 2.x | Local host metrics | **Not evidenced in repo** — no Items/Things reference it |
| exec | 2.x | Shell commands | **Not evidenced in repo** — no Items/Things reference it |
| expire | 1.x | Item auto-expiry | **Not evidenced in repo** — no Item uses `expire` |
| pushover (action) | — | Pushover API | Outbound notifications/alarms via `sendPushoverMessage(pushoverBuilder(...))` (API/user key configured out-of-repo) |

_Note: legacy MQTT v1 binding (`mqtt1`) and v1 `mqtt` action removed — system is 100% MQTT 2.x (channel-based)._

_Note (Z-Wave, OH5): Z-Wave **Things and their channel→item links are kept in openHAB's JSONDB (UI-managed, off-repo) by design** — a node's Thing UID is assigned at inclusion time and the mesh is administered live in the UI, so it cannot be authored on the dev PC and pushed. The `GH1MS1_*` Items stay textual in this repo and are linked to the UI-discovered channels. A Z-Wave binary motion channel reports `ON`/`OFF`; it is mapped onto the existing `String GH1MS1_motion` (`"active"`/`"inactive"`) via a MAP transform profile (`transform/motion.map`) on the link, so the motion rules are unchanged. The serial controller bridge holds the network security key (secret). Back up JSONDB via `openhab-cli backup`, not git._

---

## 6. Naming Conventions

Most physical-device Items follow `[Zone][Device][Index]_[measurement]`, e.g.
`FB1SS6_temp` = First-floor Bedroom #1, Sonoff sensor #6, temperature. Decoded from the
Item labels and units present; device-type letters are inferred and marked accordingly.

| Element | Pattern | Meaning |
|---|---|---|
| Floor letter | `G`, `F`, `X` | `G` = Ground floor, `F` = First floor, `X` = mobile/external _(TODO: confirm)_ |
| Room letter | `O`,`K`,`L`,`S`,`H`,`Y`,`B`,`M` | Evidenced by labels: `GO`=Office, `GK`=Kitchen, `GL`=Living Room, `GS`=Sun Room, `GH`=Hall, `GY`=Yard/Garden, `FB`=Bedroom, `FL`=Landing, `XM`=Mobile _(TODO: confirm)_ |
| Zone index | digit after room (e.g. `FB1`) | Instance of that room/zone |
| Device-type code | `SS`,`MS`,`BE`,`SP`,`NM`,`HB`,`HS`,`SA`,`SC`,`EM`,`FT`,`MC`,`AS`,`DB`,`SW`,`HT` | Inferred: `SS`=Sonoff sensor/switch, `MS`=Multisensor, `BE`=Blind Engine, `SP`=Smart Plug, `NM`=NodeMCU/sensor node, `HB`=Hue Bulb, `HS`=Hue Switch, `SA`=Smoke Alarm, `SC`=Scene Controller, `EM`=Energy Meter, `FT`=Flow/Tank (water butt), `MC`=freezer/chiller, `AS`=Arrival Sensor, `DB`=Doorbell, `SW`=SwitchBot, `HT`=Hive Thermostat _(TODO: confirm all)_ |
| Measurement suffix | `_temp`,`_humid`,`_press`,`_dew`,`_gas`,`_illuminance`,`_position`,`_switch`,`_power`,`_energy`,`_current`,`_voltage`,`_flow`,`_level`,`_distance`,`_moisture`,`_delta`,`_dimmer`,`_colour` | Telemetry/actuation quantity |
| Status suffix | `_Online`, `_IPAddress`, `_rssi`, `_Uptime` | Device health/identity (Tasmota `STATUS5`/`STATUS11`) |
| Heating prefix | `h…` | `hSP_`=active setpoint; `hSPm/d/e/n/w/h_`=morning/daytime/evening/night/weekend/holiday setpoint banks; `hMode`/`hSchedule`/`hStatus`/`hOverride`; `h<room>_Radiator`=fault flag |
| Lighting state vars | `A`,`B`,`C`,`D` | Single-letter Number Items: `A`=lighting mode, `B`=motion-restore mode, `C`=hall dark-day, `D`=kitchen dark-day (see §9) |
| Group prefix | `g` (e.g. `gTemperature`) | Functional group |

---

## 7. I/O Inventory (Items & Channels)

_Grouped by function. Regular families are enumerated compactly (each named member listed
in one row). Channels shown as `binding:…`; `mqtt:topic:mosquitto:<id>` abbreviated `mqtt:<id>`._

### 7.1 Telemetry / Sensors
| Item | Type | Units | Channel | Groups | Purpose |
|---|---|---|---|---|---|
| `FB1SS6_temp` | Number | °C | `mqtt:FB1SS6_temp` (BME680) | gTemperature, gTemperatureAvg | Master Bedroom temperature |
| `FB1SS6_humid` / `_press` / `_dew` / `_gas` | Number | %, mbar, °C, kΩ | `mqtt:FB1SS6_humid/_press/_dew/_gas` (BME680) | gHumidity (humid only) | Master Bedroom humidity / pressure / dew point / gas |
| `FB2SS7_temp` | Number | °C | `mqtt:FB2SS7_temp` (BMP280) | gTemperatureAvg | Workshop temperature |
| `FB3SS20_temp` | Number | °C | `mqtt:FB3SS20_temp` (BMP280) | gTemperature, gTemperatureAvg | Guest Bedroom temperature |
| `GK1SS3_temp` | Number | °C | `mqtt:GK1SS3_temp` (BMP280) | gTemperature, gTemperatureAvg | Kitchen temperature |
| `GK1SS3_temp_avg` | Number | °C | — (computed) | gAverage | Kitchen 15-min average |
| `GL1SS5_temp` / `_humid` | Number | °C / % | `mqtt:GL1SS5_temp/_humid` (BME280) | gTemperature, gTemperatureAvg / gHumidity | Living Room temperature / humidity |
| `GL1NM1_temp` | Number | °C | `mqtt:GL1NM1_temp` | — | Portable/BBQ temperature |
| `GO1SS4_temp` / `_illuminance` | Number | °C / lux | `mqtt:GO1SS4_temp` (BMP280) / `mqtt:GO1SS4_illuminance` (BH1750) | gTemperature, gTemperatureAvg / — | Office temperature / illuminance |
| `GS1SS10_temp` / `_press` | Number | °C / mbar | `mqtt:GS1SS10_temp/_press` (BMP280) | gTemperature, gTemperatureAvg | Sun Room temperature / pressure |
| `GY1SS8_temp` / `_press` | Number | °C / mbar | `mqtt:GY1SS8_temp/_press` (BMP280) | gOutside / gPressure | Outdoor temperature / pressure |
| `GY1SS24_temp` / `_humid` / `_press` | Number | °C / % / mbar | `mqtt:GY1SS24_*` (BME280) | (humid→gHumidity) | Shed temperature / humidity / pressure |
| `GK1SS1_illuminance` | Number | lux | `mqtt:GK1SS1_illuminance` (BH1750) | — | Kitchen illuminance (drives kitchen dark-day) |
| `GH1MS1_temperature` / `_illuminance` / `_humidity` / `_motion` | Number/Number/Number/String | °C / lux / % / "active"/"inactive" | Z-Wave multisensor (MS6) — UI-managed channel links (JSONDB); motion mapped ON/OFF→active/inactive via `motion.map` profile | gMultisensor + gTemperature / gIlluminance / gHumidity | Hall multisensor temp / lux / humidity / motion |
| `GH1MS1_illuminance_avg` | Number | lux | — (computed) | gMultisensor, gIlluminance | Hall lux 15-min average |
| `GH1MS1_illuminance_switch` | Switch | — | — | — | "Front Illuminance Bypass" (copies office lux into hall) |
| `XM1SS16_temp` | Number | °C | `mqtt:XM1SS16_temp` (DS18B20) | — | XM1-SS16 temperature |
| `GY1MC1_temp` | Number | °C | `mqtt:GY1MC1_temp` | — | Freezer temperature |
| `GY1NM2_temp1` / `_temp2` / `_delta` | Number | °C | `mqtt:GY1NM2_temp1/_temp2` / computed | gBoiler | Boiler flow / return / differential |
| `GY1SS22_distance` / `_level` / `_level_avg` / `_MO` | Number/Switch | mm / % | `mqtt:GY1SS22_distance` / computed | — | Water-butt distance sensor + derived level (+override) |
| `GY1FT1_level` / `_level_mm` / `_level_pc` / `_level_vol` | Number | % / mm / % / l | `mqtt:GY1FT1_level` (ANALOG) / computed | — | Water-butt tank level (raw + scaled mm/%/volume) |
| `GY1SS27_flow` / `GY1FT1_flow1` / `_flow3` | Number | l/min | `mqtt:GY1SS27_flow`, `GY1FT1_flow1/flow3` | — | Front / top-up / irrigation-drain flow rates |
| `GY1SS28_moisture` | Number | % | `mqtt:GY1SS28_moisture` | — | Front irrigation soil moisture |
| `GO1EM1_I/V/P/Q/PF/F/TE` | Number | A/V/W/VAR/—/Hz/kWh | `mqtt:GO1EM1_*` | gPower (P, Q) | Whole-house energy meter |
| `GO1EM1_M` | Number | kWh | — (computed offset) | — | Absolute meter reading |
| `GY1SA4_smoke/_tamper` | Number | MAP(smoke.map) | `mqtt:GY1SA4_smoke/_tamper` | gSmokeAlarm | Shed smoke / tamper (0=Alarm,1=OK) — alerted by `smoke.rules` like the Fibaros |
| `GY1SA4_battV/_battpc/_temp` | Number | mV / % / °C | `mqtt:GY1SA4_battV/_battpc/_temp` | — | Smoke detector battery / chip temp |
| `GY1SA4_online` / `GY1SA4_LastUpdate` | String/DateTime | — | `mqtt:GY1SA4_online` / rule | — | Smoke detector connection + last-seen |
| `GK1SA1_smoke/_heat/_tamper/_fault/_battalarm` | Number | MAP(alarm.map) | zwave `GK1-SA1` — UI link (JSONDB) | gSmoke, gSmokeAlarm | Kitchen Fibaro FGSD002 alarm channels: `alarm_smoke`/`_heat`/`_tamper`/`_system`/`_battery` (numeric notification: **0=Alarm, 1=OK**) |
| `GK1SA1_temp/_battpc` | Number | °C / % | zwave `GK1-SA1` — UI link (JSONDB) | gSmoke | Kitchen detector `sensor_temperature` / `battery-level` |
| `FL1SA2_smoke/_heat/_tamper/_fault/_battalarm` | Number | MAP(alarm.map) | zwave `FL1-SA2` — UI link (JSONDB) | gSmoke, gSmokeAlarm | Landing Fibaro FGSD002 alarm channels: `alarm_smoke`/`_heat`/`_tamper`/`_system`/`_battery` (numeric notification: **0=Alarm, 1=OK**) |
| `FL1SA2_temp/_battpc` | Number | °C / % | zwave `FL1-SA2` — UI link (JSONDB) | gSmoke | Landing detector `sensor_temperature` / `battery-level` |
| `GK1SA1_LastUpdate` / `FL1SA2_LastUpdate` | DateTime | — | rule (`smoke.rules`) | — | Kitchen/Landing Fibaro last-seen (stamped on each temp/battery report; not the alarm seeds) |
| `GO1SS4_temp_delta … FB3SS20_temp_delta` (7) | Number | °C | — (computed) | gTemperatureDelta | Per-room (temp − setpoint) deltas: GO1SS4, GK1SS3, GL1SS5, GS1SS10, FB1SS6, FB2SS7, FB3SS20 |
| `Temp_{Today,Week,Month,Year,All}_{Max,Min}` (10) | Number | °C | — (computed) | — | Outdoor min/max records |
| `Temp_{…}_{Max,Min}_Time` / `_Time_Format` (20) | String | — | — (computed) | — | Timestamps for the above records |
| `GL1NM1_temp` (BBQ) | Number | °C | `mqtt:GL1NM1_temp` | — | BBQ/remote temperature (Pushover when enabled) |

### 7.2 Blinds / Positions
| Item | Type | Units | Channel | Groups | Purpose |
|---|---|---|---|---|---|
| `GO1BE1_position` | Dimmer | % | `mqtt:GO1BE1_position` (`cmnd/GO1-BE1/POSITION`) | — | Office blind position |
| `GL1BE2_position` | Dimmer | % | `mqtt:GL1BE2_position` | — | Living Room blind position |
| `FB1BE3_position` | Dimmer | % | `mqtt:FB1BE3_position` | — | Master Bedroom blind position |
| `FB1BE3_release` / `FB1BE3_block` | Number | — | — | — | Bedroom blind morning-release / block flags |
| `Blinds_Auto` / `Blinds_Bedroom_Mode` / `Blinds_Lux_On` / `Blinds_Christmas` | Switch | — | — | — | Mode toggles (auto, bedroom sunrise, sun-shade, Christmas) |
| `Blinds_Sunset` / `Blinds_Pre_Sunset` / `Blinds_Post_Sunset` / `_Post_Sunset_T` | Number | % / min | — | — | Sunset positions + post-sunset timer |
| `Blinds_Sunrise` / `_Sunrise_Trigger` / `_Sunrise_After` / `Blinds_Post_Sunrise` / `_Post_Sunrise_T` | Number | % / min | — | (some gVariables) | Sunrise positions, trigger flags, post-sunrise timer |
| `Blinds_Lux` / `Blinds_Lux_Hys` | Number | lux | — | — | Auto sun-shade threshold + hysteresis |
| `gBlinds` / `gGBlinds` | Group:Dimmer | % | — | — | All-blinds / ground-blinds aggregate (sitemap control) |

### 7.3 Plugs / Switches
| Item | Type | Channel | Groups | Purpose |
|---|---|---|---|---|
| `GO1SP1_switch/_led` | Switch | `tplinksmarthome:hs110:26D077:switch/led` | gPlugSP1, gPlugs | Office plug on/off + LED |
| `GO1SP1_power/_energy/_current/_voltage/_rssi` | Number | `tplinksmarthome:hs110:26D077:*` | gPlugSP1 | Office plug metering |
| `GL1SP2_*` (switch/led/power/energy/current/voltage/rssi) | Switch/Number | `tplinksmarthome:hs110:26249D:*` | gPlugSP2, gPlugs | Living Room plug |
| `FB1SP3_*` (switch/led/power/energy/current/voltage/rssi) | Switch/Number | `tplinksmarthome:hs110:2647A8:*` | gPlugSP3, gPlugs | Bedroom plug |
| `GK1SS1_switch` / `GK1SS2_switch` | Switch | `mqtt:GK1SS1_switch/GK1SS2_switch` | gSonoff | Kitchen cooker / side lights (Sonoff) |
| `GL1SS18_switch` / `GS1SS17_switch` / `GO1SS15_switch` | Switch | `mqtt:…` | — | Xmas/aux relays (Living Room, Sun Room, Office) |
| `XM1SS16_switch` / `XM1SS21_switch` | Switch | `mqtt:…` | — | XM1-SS16 relay / Camera Lamp |
| `GL1SS5_switch` / `GL1SS11_switch` / `GO1SS12_switch` / `GS1SS10_switch` | Switch | `mqtt:…` | gHeating | Radiator relays (Kitchen, Living Room, Office, Sun Room) |
| `FB1SS13_switch1` / `_switch2` / `FB3SS19_switch` | Switch | `mqtt:…` | gHeating | Radiator relays (Master Bedroom, Workshop, Guest Bedroom) |
| `FB1SS6_switch` / `FB2SS7_switch` | Switch | `mqtt:…` | — | M.Bedroom / Workshop sensor-node relays |
| `GY1SS8_switch` | Switch | `mqtt:GY1SS8_switch` | — | Boiler call-for-heat relay |
| `GY1SS9_switch` / `_switch1` / `_switch2` | Switch | `mqtt:GY1SS9_*` | — | Gate relay + 2 limit switches |
| `GY1SS22_switch` / `GY1SS23_switch` / `GY1SS26_switch` | Switch | `mqtt:…` | — | Water-butt / spare / front-irrigation valve |
| `GY1FT1_switch1/2/3` | Switch | `mqtt:GY1FT1_switch1/2/3` | — | Irrigation / drain / top-up valves |
| `GK1SW04_switch` | Switch | `smartthings:switch:…Coffee_Machine` | — | Coffee machine (SwitchBot) |
| `gPlugs` / `gSonoff` / `gHeating` / `gChristmas` | Group:Switch | — | — | Aggregate switch groups (OR; see §8) |

### 7.4 Online / Health Status
| Item | Type | Channel | Purpose |
|---|---|---|---|
| `*_Online` (24) | Switch | — (set by rule) | Device online flags: GK1SS1/2/3, GO1SS4/12/15, GL1SS5/11/18, FB1SS6/13, FB2SS7, FB3SS19/20, GS1SS10/17, GY1SS8/9/24/25/26, XM1SS16/21 |
| `*_IPAddress` (~22) | String | `mqtt:<id>:STATUS5` JSONPATH `$.StatusNET.IPAddress` | Tasmota IP (member `gSonoff_IP`, `autoupdate=false`) |
| `*_rssi` (~22) | Number | `mqtt:<id>:state` STATUS11 `$.StatusSTS.Wifi.RSSI` | Wi-Fi RSSI (member `gSonoff_RSSI`) |
| `*_Uptime` (~22) | String | `mqtt:<id>:state` STATUS11 `$.StatusSTS.Uptime` | Uptime (member `gSonoff_Uptime`) |
| `Sonoff_Refresh` | Switch | — | Manual trigger to poll all Sonoff status |
| `GY1SA4_online` | String | `mqtt:GY1SA4_online` | Smoke detector MQTT connection |

### 7.5 Heating Control
| Item(s) | Type | Purpose |
|---|---|---|
| `hSP_GO1 … hSP_FB3` (7) | Number | Active per-room setpoints (gHeatingSP) |
| `hSPm_* / hSPd_* / hSPe_* / hSPn_* / hSPw_* / hSPh_*` (7×6=42) | Number | Morning/Daytime/Evening/Night/Weekend/Holiday setpoint banks (gHeatingSP1…6) |
| `hMode` / `hSchedule` / `hStatus` / `hOverride` | Number/String | Manual(0)/Auto(1); schedule code 1–5; status text; manual override of schedule |
| `hAway` / `hWork` | Switch | Holiday mode / Work mode |
| `hHysteresis` / `hStandby` / `hStandbyNumber` / `hRetryFlag` | Number | Control band, relax/standby flags, boiler retry flag |
| `hGO1_Radiator … hFB3_Radiator` (7) | Number | Per-room radiator fault/enable flags (gHeatingFault) |
| `hRuntimeToday/Yesterday/ThisWeek/LastWeek/ThisMonth/LastMonth` (6) | Number | Boiler run-time accumulators |
| `gHeatingSP`, `gHeatingSP1…6`, `gHeatingFault`, `gBoiler` | Group | Setpoint banks, fault flags, boiler telemetry |

### 7.6 Lighting Control & Setpoints
| Item(s) | Type | Purpose |
|---|---|---|
| `GH1HB1_*`, `FL1HB2_*`, `FL1HB3_*` | Dimmer/Switch/String | Hall + Landing Hue (brightness/switch/alert) — gHueDimmer |
| `GK1HB4…GK1HB9_dimmer`, `GK1B10/B13/B14_dimmer` | Dimmer | Kitchen spots/table Hue — gHueKitchen, gHueTable |
| `GK1HB11/HB12_dimmer/_colour` | Dimmer | Kitchen "glass" Hue — gHueGlass/gHueColour |
| `GH1HB18/HB19_dimmer/_colour` | Dimmer | Front-door Hue — gHueFront/gHueFrontColour |
| `GY1HB15…HB24_dimmer/_colour` | Dimmer | Yard / rear-yard Hue — gHueYard/gHueYardColour |
| `GK1HS1_event` / `GK1_mode` | Number | Hue dimmer-switch event / kitchen lighting mode (1/2/3) |
| `A` / `B` / `C` / `D` | Number | Lighting state machine (gVariables; see §9) |
| `Lighting_Mode` / `Light_Status` / `Motion_Lights_Status` | String | Mode select + status text |
| `Motion_Lights` / `Motion_Time` / `Motion_Setpoint` / `Bed_Time` | Switch/Number | Motion enable, timeout, brightness, bed-lamp delay |
| `Lux_Min_Hall/Max_Hall/Min_Kitchen/Max_Kitchen`, `Hall_Test_Lux`, `Kitchen_Test_Lux` | Number | Dark-day thresholds/hysteresis |
| `DarkHall/DarkKitchen/DarkMorning/Dusk/Evening/KitDusk/KitEvening/NightHallFront/Mid/Rear_Setpoint` | Number | Per-mode brightness setpoints |
| `HueFrontTrigger/Midnight/Dusk/DarkDaytime/DarkMorning/Evening_Setpoint`, `HueFront/RearTrigger_Timer`, `HueRearTrigger_Setpoint` | Number | Front/rear outdoor Hue setpoints + camera-trigger timers |
| `gHueDimmer/Kitchen/Table/Glass/Colour/Front/FrontColour/Yard/YardColour/YardR/YardRColour`, `gLighting`, `gPhilipsHue` | Group | Hue groupings (sitemap + rule control) |

### 7.7 Presence, Audio, Gate, Misc
| Item(s) | Type | Purpose |
|---|---|---|
| `XM1AS1_presence` / `_presence_S` / `_presence_J` / `_presence_trig` / `XM1AS1_battery` | String/Switch/Number | Home/away flag (Tasker-driven), per-person + trigger (legacy), arrival-sensor battery |
| `Presence_Override` | Switch | Force-present override (today) |
| `Sonos_<Room>_Control/_Volume/_Mute/_CurrentTrack/_Coordinator/_Add/_Standalone` ×7 rooms | Player/Dimmer/Switch/String | Per-speaker control |
| `Sonos_All_PlayPause/Next/Prev/Mute/Unmute/VolUp/VolDown`, `Sonos_<Room>_JoinGroup/_LeaveGroup`, `Sonos_CurrentMaster` | Switch/String | Whole-house transport + dynamic grouping |
| `Sonos_Kitchen_Radio` / `Sonos_Kitchen_Favorite` | String | Kitchen `radio`/`favorite` channels — drive saved-station presets (Kitchen is the preset coordinator) |
| `Sonos_Preset_BBCR2` | Switch | Preset proxy (ON=start/OFF=stop): grouped "BBC Radio 2" in Office/Kitchen/Sun Room/Bedroom @ 25 % |
| `gateRemoteControl/Single/Enable`, `gateRecloseEnable`, `gateTimerActive`, `gateRemoteTimer`, `gatePosition`, `gatePositionHold`, `gateBinDay`, `gateMove`, `gateSamsung`, `gateSamsungOnline`, `GY1SS9_status` | Switch/Number/String | Gate control, position, auto-reclose, bin-day, SmartThings bridge |
| `Iri_F_SP/_Total/_Switch`, `Iri_F_SP_R/_Total_R/_Switch_R` | Number | Front / rear irrigation setpoint, totaliser, control |
| `Power_Day/Start/End/Today/Cost/CostToday`, `Power_EUnit/EStand/GUnit/GStand` | Number | Energy usage + tariff/cost |
| `Christmas_Auto/_Override/_Menu`, `gChristmas` | Switch/Number | Christmas lighting schedule/menu |
| `phoneCharging/_Release/_Delay/_Timer` | Switch/Number | Tasker phone wireless-charging status |
| `Blanket_control/_status/_autotime/_expiretime` | Number/String | Electric blanket |
| `cctv` | Image | `ipcamera` snapshot |
| `BlueIris_Test`, `BlueIris_trigger`, `BlueIris_rearEnable` | Switch/String | Blue Iris control (see §14 for inactive motion items) |
| `remoteTempEnable`, `Scene`, `HallTemp`, `HallMotion`, `A/B/C/D`, `Chart_Period` | various | Misc flags/variables (`HallTemp`/`HallMotion` reference a `Home:Multisensor` channel — verify) |

---

## 8. Group Hierarchy

Aggregation functions: `gPlugs`/`gSonoff` = `OR(ON,OFF)`, `gHeating` = `OR(OFF,ON)` (note
inverted argument order vs the others), `gTemperatureAvg` = `AVG`, `gTemperatureDelta` =
`Number:MIN`. `gHueDimmer/Kitchen/Table/Blinds/GBlinds` = `Dimmer` (no function). All Items
are persisted with `restoreOnStartup` (MapDB) and `everyChange` (InfluxDB) — see §12.

```
gDevices
 ├─ gLighting            ["Lighting"]   (all Hue dimmers/switches)
 ├─ gSceneControl        ["Scene Controller"]  → FB1SC1_power
 ├─ gMultisensor         ["Multisensor"] → GH1MS1_illuminance/_avg/_motion/_humidity
 ├─ gPhilipsHue          ["Hue"]        (all Hue bulbs/switches)
 ├─ gHueYard / gHueYardColour / gHueYardR / gHueYardRColour   ["Yard Lighting"]
 ├─ gHueFront / gHueFrontColour                               ["Front Door Lighting"]
 ├─ gSmoke               ["Smoke"]      → GK1SA1_* (Kitchen) + FL1SA2_* (Landing) Fibaro Z-Wave detectors
 ├─ gSmokeAlarm          (no tag)       → all detector alarm Items (0=Alarm): 10 Fibaro alarm_* + shed GY1SA4_smoke/_tamper; watched by smoke.rules
 └─ gPlugSP1 / gPlugSP2 / gPlugSP3      ["Smart Plugs"]  (per-plug channel groups)

gHueColour, gHueGlass                    (kitchen "glass" colour/brightness)
gHueDimmer  (Dimmer)  → GH1HB1, FL1HB2, FL1HB3
gHueKitchen (Dimmer)  → GK1HB4…HB9, GK1B10/B13/B14
gHueTable   (Dimmer)  → GK1B10/B13/B14
gBlinds / gGBlinds (Dimmer)              (sitemap blind control)

gPlugs   (Switch OR(ON,OFF))  → GO1SP1/GL1SP2/FB1SP3 _switch
gSonoff  (Switch OR(ON,OFF))  → GK1SS1_switch, GK1SS2_switch
gHeating (Switch OR(OFF,ON))  → radiator relays GL1SS5/GL1SS11/GO1SS12/GS1SS10/FB3SS19/FB1SS13_switch1/2

gTemperature                  → all room PV temps
 └─ gTemperatureAvg (AVG)     "Average Indoor Temperature"
gTemperatureDelta (Number:MIN)→ 7× *_temp_delta
gPressure / gOutside / gHumidity / gIlluminance / gPower / gAverage / gBoiler
gWeather → Astro_SunriseEnd
gVariables → A,B,C,D, Blinds_Sunrise*, Astro_SunriseEnd
gSetpoints → all lighting/motion/lux setpoints
gCharts → Chart_Period

gHeatingSP                    → hSP_GO1…hSP_FB3 (active setpoints)
gHeatingSP1…gHeatingSP6       → morning/daytime/evening/night/weekend/holiday banks
gHeatingFault                 → hGO1_Radiator…hFB3_Radiator

gSonoff_IP / gSonoff_RSSI / gSonoff_Uptime   → Tasmota STATUS5/STATUS11 telemetry
```

---

## 9. Control Philosophy & Operating Modes

The system is event-driven with several explicit state machines:

**Lighting mode — Item `A` (var `a`):**

| `A` | Meaning | Entered by |
|---|---|---|
| 0 | Daytime / off | Sunrise (before 07:00), `Lights Off`, manual `Lighting_Mode=3` |
| 1 | Dusk (sunset −30 min) | `Sunset -30 Minutes` |
| 2 | Evening (sunset) | `Sunset`, return-from-away at night |
| 3 | Night | `Bedtime` (scene button 4), 23:00 if away |
| 4 | Dark morning | 07:00 if before sunrise, or pre-dawn motion |
| 5 | Night, away | `Night lights`/`Left Home` when away at night |
| 100 | Motion active | `Motion Timer` (var `B` holds prior mode to restore) |

**Dark-daytime sub-modes — Items `C` (hall) / `D` (kitchen):** `0`=idle, `1`=pending
(debouncing), `2`=active. Active only while `A==0`; reset whenever `A>0`. Engaged by the
continuous `Dark Daytime Hall`/`Kitchen` rules (lux < `Lux_Min_*`, 5-min debounce) and on
entry to daytime by `Lights Off`.

**Presence — Item `XM1AS1_presence`** (`"present"`/`"not present"`): set automatically by
Tasker (phone Wi-Fi) via REST; the Hue dimmer button (`hue.rules`) is a manual backup.
Drives away-lighting (`Left Home`, occupied-look in dusk/evening), heating daytime
schedule, and bedroom blinds.

**Heating — `hMode`** (0 Manual / 1 Auto) and **`hSchedule`** (1 Morning, 2 Daytime,
3 Evening, 4 Night, 5 Weekend) selected by cron/presence; **`hAway`** applies the Holiday
bank; per-room hysteresis (`hHysteresis`) switches radiator relays and fires the boiler
(`gHeating` → `GY1SS8_switch`) with a relax/standby override (`hStandby`).

**Other modes:** `Blinds_Auto` (auto blinds on/off), `Blinds_Christmas`, `Christmas_Auto`/
`Christmas_Menu` (Christmas lighting), `Motion_Lights` (hall motion enable).

---

## 10. Functional Logic (Rules)

### 10.1 `rules.rules` (lighting / presence state machine)
| Rule | Trigger | Conditions | Actions | Purpose |
|---|---|---|---|---|
| Reload Variables | System started | — | Restore `a,b,c,d` from A/B/C/D; load `motionTimeoutMins` | Restore lighting state on boot |
| Motion Timer | `GH1MS1_motion` → active | timer null, `Motion_Lights` ON, A∈{2,3} | Save B=A, A=100, dim hall (GH1HB1/FL1HB2/FL1HB3) to `Motion_Setpoint`; timer restores A=B | Hall motion lighting w/ timeout |
| Motion Lights Status | `A` changed | — | Set `Motion_Lights_Status` Standby/Active/Unavailable | Status text |
| Dark Mornings | cron 07:00 | before `Astro_SunriseEnd` | A=4 | Dark-morning detect |
| Dark Mornings Override | `GH1MS1_motion` → active | 03:00–07:00, A≠0, A≠100 | A=4 | Pre-dawn motion → dark morning |
| Dark Daytime Hall | `GH1MS1_illuminance` changed | lux<`Lux_Min_Hall`, A=0, C=0 | C=1, 5-min timer → C=2 if still dark | Detect hall darkness |
| Dark Daytime Hall Recovered | `GH1MS1_illuminance` changed | lux>`Lux_Max_Hall`, C=2 | 5-min timer → C=0, turn hall/yard/front off | Hall brightness recovery |
| Dark Day Hall Lights Present | `C` → 2 | — | Yard 33, front `HueFrontDarkDaytime`, GY1HB15 25; if home: GO1SP1/XM1SS21 on, `gHueDimmer`=`DarkHall` | Apply hall dark-day lights |
| Dark Daytime Kitchen | `GK1SS1_illuminance` changed | lux<`Lux_Min_Kitchen`, A=0, D=0 | D=1, 5-min timer → D=2 | Detect kitchen darkness |
| Dark Daytime Kitchen Recovered | `GK1SS1_illuminance` changed | lux>`Lux_Max_Kitchen`, D=2 | 5-min timer → D=0, `gHueKitchen` 0, `gSonoff` OFF | Kitchen brightness recovery |
| Dark Day Kitchen Lights Present | `D` → 2 | if home | `gHueKitchen`=`DarkKitchen` (if dim<5), `gSonoff` ON | Apply kitchen dark-day lights (home only) |
| Dark Daytime Status (Hall) / (Kitchen) | `C` / `D` changed | — | Set `Light_Status` text | Status text |
| Left Home | `XM1AS1_presence` → not present | 5-min grace | Per mode: dark-day→interior off; dusk/evening→occupied look (hall+plugs+exterior on, kitchen off); night→A=5 + interior dark; daytime→kitchen off | Away lighting |
| Dark Day Lights Return | `XM1AS1_presence` → present | branch on A/C/D | Restore hall/kitchen/dusk/evening lights | Return-home lighting |
| Morning Override | `Lighting_Mode` → 4 | — | A=4 | Manual dark-morning |
| Light Mornings | astro `rise#event` START | hour<7 | A=0 | Sunrise → daytime |
| Sunset -30 Minutes | astro `c7d0dedc:set#event` END | — | A=1; `GY1SS24_switch` ON; `gChristmas` ON | Dusk + Christmas on (see §14: UID) |
| Midnight | cron 00:00 | — | Shed off; front=`HueFrontMidnight`; yard 30; `Presence_Override` OFF | Midnight outdoor levels |
| Sunset | astro `local:set#event` END | — | A=2 | Sunset → evening |
| Bedtime | `FB1SC1_power` → 4 | — | A=3; reset FB1SC1_power | Scene button → night |
| Night Lights Away | cron 23:00 | away | A=3 | Auto-night when away |
| Night Lights Reset Arrive Home | `XM1AS1_presence` → present | late & A=5 / A=1 / A=2 | A=2 + kitchen evening / kitchen dusk / kitchen evening | Late return lighting |
| Reset Dark Day Variables | `A` changed | A>0 | C=0, D=0 | Clear dark-day on mode change |
| Dark Morning Lights On | `A` → 4 | — | Plugs/Sonoff on; `gHueDimmer`=`DarkMorning`; yard 33; front; GY1HB15 25 | Morning boost lights |
| Dark Morning Lights Off | astro `rise#event` START | +30 min; if light turn off yard/front/GY1HB15; if A=4 → A=0 | End morning boost; hand to `Lights Off`/dark-day | Morning boost end |
| Dusk Lights | `A` → 1 | if home: kitchen | `gPlugs` on, `gHueDimmer`=`Dusk`, yard 15, front, GY1HB15 25, (home) kitchen | Dusk scene |
| Evening Lights | `A` → 2 | if home: kitchen | `gPlugs` on, `gHueDimmer`=`Evening`, yard 45, front, GY1HB15 66, (home) kitchen; `Lighting_Mode`=1 | Evening scene |
| Kitchen Lights | `GK1_mode` changed | 1/2/3 | Evening / Dinner (per-bulb) / Bright kitchen scenes | Kitchen scene selector |
| Night lights | `A` → 3 | away→A=5 + FB1SP3 off; home→bed-lamp timer | Plugs/Sonoff off; hall night setpoints; `gHueKitchen` 0; `FB1BE3_position` 1; `Lighting_Mode`=2 | Night scene |
| Lights Off | `A` → 0 | per zone: dark→engage dark-day (away→ceiling/kitchen off); light→Hue off | `gPlugs`/`gSonoff` off; `Lighting_Mode`=3 | Daytime/off (dark-aware) |
| Bedside Lamp Toggle | `FB1SC1_power` → 3 | — | Toggle `FB1SP3_switch` | Scene button → bedroom plug |
| Lighting Mode Override | `Lighting_Mode` changed | 1/2/3 | A=2/3/0 | Map UI mode → state |
| Test3 | `FB1SC1_power` → 1 | — | A=2 | Test/scene |

### 10.2 `status.rules` (device health, phone, Sonoff polling)
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Hall Illuminance Bypass | `GO1SS4_illuminance` changed | if bypass ON → copy office lux to `GH1MS1_illuminance` | Use office lux for hall |
| Phone Charging Status (OFF) / (ON) | `phoneCharging` OFF / ON | timer → `phoneChargingRelease` ON / OFF | Phone charge release timing |
| Sonoff Refresh | `Sonoff_Refresh` → ON | reset OFF | Manual poll button |
| Shed Power On / Off Notification | `GY1SS24_Online` ON / OFF | Pushover "Shed power on/off" | Shed power alert |
| Gate Offline ×2 | `GY1SS9_Online` OFF / ON | Pushover "Gate offline/online"; `gateSamsungOnline` OFF/ON | Gate connectivity (⚠ both rules named "Gate Offline", §14) |
| Boiler Online / Offline | `GY1SS8_Online` ON / OFF | Pushover "Boiler connected" / "disconnected" (emergency) | Boiler connectivity |
| Poll Sonoff | cron `0 0/15` or `Sonoff_Refresh` ON | UNDEF then send STATUS5/STATUS11 to `gSonoff_IP`/`_Uptime` members | Refresh device status |
| Sonoff Status | cron `0 1/15` | Set each `*_Online` = ON/OFF from its `*_IPAddress` UnDef state | Derive online flags |

### 10.3 `heating.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Office / Kitchen / Living Room / Sun Room / Master Bedroom / Workshop / Guest Bedroom | room temp / `hSP_*` / `hMode`→1 / `h<room>_Radiator` changed | hysteresis on temp vs `hSP_*`±`hHysteresis` → radiator relay ON/OFF (GO1SS12, GL1SS5, GL1SS11, GS1SS10, FB1SS13_switch1/2, FB3SS19) | Per-room thermostatic control |
| Heating Deltas | cron `0/10` or `gHeatingSP` changed | compute 7× `*_temp_delta` | Temp-vs-setpoint deltas |
| Heating Relax | cron `0/10` / `gHeatingSP` | warm enough/over setpoint → `gHeating` OFF + `hStandby`=1; cool → ON + standby 0 | Standby/relax mode |
| Heating ON / OFF | `gHeating` → OFF / ON | (6-min delay on) fire/stop boiler `GY1SS8_switch`, verify `GY1SS8_power`, retry ×3, Pushover emergency on fail | Boiler firing w/ verify |
| Auto Resume | `hMode` → 1 | restore boiler to match `gHeating` | Re-enter auto |
| Schedule Morning/Daytime/Evening/Night/Weekend | cron / presence / `A`→3 | set `hSchedule`, `hStatus`, apply matching `hSP*` bank | Time-of-day setpoints |
| Schedule Holiday ON / OFF | `hAway` ON / OFF | apply holiday bank / restore prior bank | Holiday setpoints |
| Heating Manual / Auto Status | `hMode` → 0 / 1 | set `hStatus` | Mode status text |
| Sensor (Office…Sun Room) ×7 | room temp changed | temp>40 or <10 → MQTT `cmnd/<dev>/restart`; 2-min recheck → `h<room>_Radiator`=0 + Pushover "<dev> temperature bad" | Sensor fault detect/reset |

### 10.4 `boiler1.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Boiler Differential | `GY1NM2_temp1` changed | `GY1NM2_delta` = temp1 − temp2 | Flow/return differential |
| Boiler Run Time | cron `0/1` | if flow>60 °C increment runtime → today/week/month | Accumulate run minutes |
| Boiler Run Time Reset Daily / Weekly / Monthly | cron midnight / Sun / 1st | roll over to yesterday/last-week/last-month, reset | Period rollovers |

### 10.5 `temperatures.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Min/Max Temperatures Daily/Weekly/Monthly/Yearly/All-Time | `GY1SS8_temp` changed | track outdoor max/min + time (per period) | Outdoor records (⚠ All-Time copy-paste bug, §14) |
| Clear Min/Max … (Daily/Weekly/Monthly/Yearly) | cron per period | reset records to current temp | Period resets |

### 10.6 `average.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Average Values | cron `0/1` | `GH1MS1_illuminance_avg` (15 min), `GK1SS3_temp_avg` (15 min), `GY1SS22_level_avg` (3 min) from persistence | Rolling averages |

### 10.7 `power.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Log Daily Power Start / End | cron 00:00 / 23:59 | capture `GO1EM1_TE`; compute `Power_Day`, `Power_Cost` | Daily kWh + cost |
| Log Power Today | cron `0/5` | `Power_Today`, `Power_CostToday` | Running usage/cost |
| Electricity Meter | cron `0/1` | `GO1EM1_M` = TE + offset | Absolute meter |

### 10.8 `irrigation.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Front / Rear Irrigation Control | `Iri_F_Switch` / `_R` changed | start/stop valve, seed totaliser, 30-s no-flow → cancel + Pushover | Start/stop irrigation |
| Front / Rear Irrigation Totaliser | cron `0/10` | integrate flow → `Iri_F_Total` / `_R` | Volume integration |
| Front / Rear Irrigation Stop | `Iri_F_Total` / `_R` changed | ≥ setpoint → stop + Pushover "complete" | Auto-stop at target |
| Water Butt Level | `GY1FT1_level` changed | scale to mm/%/vol; manage top-up/drain valves at 90/95%. Drain (`GY1FT1_switch2`) is **fail-safe: OFF=open/draining, ON=closed**, opened at >95% to dump rain overflow and closed at ≤90% (3 s settle). NULL/UNDEF-guarded; decides on the freshly-computed `%` (not the stale async item). **Flow-verified:** 30 s after opening, if still >95% with no drain flow (`GY1FT1_flow3` ≤ 0.2 l/min) it retries the open and sends one high-priority Pushover ("OVERFLOW RISK") — catches a stuck/blocked drain | Tank level + valves (overflow-safe drain) |

### 10.9 `blinds.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Blinds Sunset -30 Minutes | astro `c7d0dedc:set#event` END | `Blinds_Auto` ON → pre-sunset positions to GO1BE1/GL1BE2/FB1BE3 | Pre-close before sunset |
| Blinds Sunset | astro `local:set#event` END | sunset positions + post-sunset timer | Close at sunset |
| Blinds Sunrise before / after 07:00 | cron 07:00 / astro `rise#event` END | open blinds at 07:00 or actual sunrise | Open in morning |
| Blinds Post-Sunrise | `Blinds_Sunrise_Trigger` → 1 | post-sunrise position timer | Secondary AM position |
| Bedroom Blind Open/Close | `FB1SC1_power` → 2 | toggle `FB1BE3_position` 1/100 | Scene-button bedroom blind |
| Bedroom Blind Morning Release (+ Delayed) | `GH1MS1_motion` active / `phoneChargingRelease` ON | weekday/weekend morning → raise bedroom blind | Morning bedroom blind |

### 10.10 `gate.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Gate Pulse | `GY1SS9_switch` → ON | 200 ms → OFF | Momentary relay pulse |
| Gate Samsung Smartthings | `gateSamsung` → ON | pulse `GY1SS9_switch`, reset | SmartThings trigger |
| Bin Day | cron Thu 06:40 | open gate, verify, retry, Pushover (+emergency on fail) | Auto-open bin day |
| Gate Notifications | `gatePosition` changed | Pushover closed/open/in-between; 10-min open → emergency | Gate state alerts |
| Gate Position | `GY1SS9_switch1/2` changed | decode limit switches → `gatePositionHold`, `gateMove` | Position decode |
| Gate Position De-Bounce | `gatePositionHold` changed | 2-s debounce → `gatePosition` | Debounce position |
| Gate Remote / Remote Single | `gateRemoteControl` / `gateRemoteSingle` → ON | enabled → pulse, optional auto-reclose timer | Remote open |

### 10.11 `sonos.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Play All / Next All / Prev All / Mute All / Unmute All | `Sonos_All_*` command ON | broadcast transport/mute to 7 speakers | Whole-house transport |
| Vol All Up / Down | `Sonos_All_VolUp/Down` ON | ±5 each `_Volume` (cap 0/100) | Whole-house volume |
| `<Room>` Join Group ×6 | `Sonos_<Room>_JoinGroup` ON | pick coordinator (priority LivingRoom→…), `_Add`=coord, set `Sonos_CurrentMaster` | Join room to group |
| `<Room>` Leave Group ×6 | `Sonos_<Room>_LeaveGroup` ON | `_Standalone` ON | Remove from group |
| Sonos Preset BBC Radio 2 | `Sonos_Preset_BBCR2` command | ON: Kitchen standalone → add Office/Sun Room/Bedroom to Kitchen's group → set all to 25 % → play "BBC Radio 2" on Kitchen `radio` + PLAY (2 s gaps between steps). OFF: pause Kitchen (group stays grouped) | Sitemap-button radio preset (Kitchen = coordinator) |

### 10.12 `smoke.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Update Last MQTT message timestamp | `GY1SA4_online` update | `GY1SA4_LastUpdate` = now | Shed (MQTT) last-seen |
| Kitchen Smoke Detector Last Update | `GK1SA1_temp`/`_battpc` received update | `GK1SA1_LastUpdate` = now | Kitchen (Z-Wave) last-seen, stamped on real wakeup reports |
| Landing Smoke Detector Last Update | `FL1SA2_temp`/`_battpc` received update | `FL1SA2_LastUpdate` = now | Landing (Z-Wave) last-seen, stamped on real wakeup reports |
| Smoke Detector Alarm Init | System started | Seed any NULL/UNDEF `gSmokeAlarm` member to `1` (OK) | Z-Wave notification channels report only on event/wakeup, so unreported alarms show "Unknown" until seeded |
| Smoke Detector Alarm | `Member of gSmokeAlarm` changed | On `0` (Alarm): Pushover **titled `🔥 <Location> Smoke Detector`**, body = the event (`SMOKE DETECTED`/`HEAT DETECTED`/`Tamper alarm`/`System fault`/`Low battery`) — **emergency (pri 2)** for `_smoke`/`_heat` (receipt stored per Item), normal for `_tamper`/`_fault`/`_battalarm`; on `0→1`: `cancelPriorityMessage` the stored emergency receipt + Pushover titled `<Location> Smoke Detector` (no fire), body `✅ <event> cleared` | Smoke/heat/tamper/fault/low-battery alerting for all three detectors (Kitchen/Landing Fibaro + Shed MQTT). Smoke/heat ack-loop auto-cancels on recovery (in-memory receipts; lost on restart → falls back to ack/expire) |
| Smoke Detector Battery Low | `GK1SA1`/`FL1SA2`/`GY1SA4` `_battpc` changed | Pushover titled `🔥 <Location> Smoke Detector`, body `Battery low (<pc>%)` when crossing **below 20 %** (once) | Battery-level backstop to the devices' own low-battery signals |
| Smoke Detector Liveness | cron `0 7 0/6 * * ?` (6-hourly) | Pushover (titled `🔥 <Location> Smoke Detector`, body `Offline - …`) if a Fibaro Z-Wave Thing is not `ONLINE`, or the Shed `GY1SA4_LastUpdate` heartbeat is >2 h stale | Catch a dead/non-responding detector that would otherwise sit on its seeded "OK" |

### 10.13 `hue.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Hue Present / Not Present | Hue button event `1002` / `2002` | `XM1AS1_presence` = present / not present | Manual presence backup |

### 10.14 `blueiris.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| Doorbell | `XM1DB1_doorbell` → ON | `BlueIris_trigger` front | ⚠ trigger item undefined → never fires (§14) |
| Gate Open | `gatePosition` → 3 | `BlueIris_trigger` rear | Rear camera on gate open |
| Front Trigger / Rear Trigger | `BlueIris_motionFront` / `Rear` → ON | flash `gHueFront` / `GY1HB15` | ⚠ trigger items undefined → never fire (§14) |
| Activate / De-Activate Rear Motion | `BlueIris_rearEnable` ON / OFF | `BlueIris_trigger` profile=2 / 1 | Toggle rear camera profile |

### 10.15 `pushover.rules`
| Rule | Trigger | Actions | Purpose |
|---|---|---|---|
| BBQ Temperature | cron `0/20` | if `remoteTempEnable` ON → Pushover BBQ temp (`GL1NM1_temp`) | Remote BBQ temp |

_Disabled `.rulesx` files (not loaded): `blanket.rulesx`, `christmas.rulesx`,
`homebrew.rulesx`, `irrigation.rulesx`, `presence.rulesx`._

---

## 11. Alarms & Notifications

All notifications use the Pushover action (`sendPushoverMessage(pushoverBuilder(...))`);
default priority unless `.withEmergencyPriority()` shown. Recipient = owner's Pushover
account (configured out-of-repo).

| Alarm / notification | Trigger condition | Priority | Channel | Action / recipient |
|---|---|---|---|---|
| Boiler call for heat failed | Boiler relay verify fails after 3 retries | **Emergency** | Pushover | Owner — boiler not firing |
| Boiler failed to switch off | Boiler off verify fails after retries | **Emergency** | Pushover | Owner |
| Boiler connected / disconnected | `GY1SS8_Online` ON / OFF | Normal / **Emergency** (disconnect) | Pushover | Owner |
| `<dev>` temperature bad ×7 | Room temp >40 or <10 °C, persists 2 min | Normal | Pushover | Owner — sensor fault |
| Shed power on / off | `GY1SS24_Online` ON / OFF | Normal | Pushover | Owner |
| Gate offline / online | `GY1SS9_Online` OFF / ON | Normal | Pushover | Owner |
| Gate closed / open / in between | `gatePosition` = 1 / 3 / 4 | Normal | Pushover | Owner |
| Gate open alert | `gatePosition` = 3 for 10 min | **Emergency** | Pushover | Owner |
| Gate open for bin day / failed | Bin-day open success / failure | Normal / **Emergency** | Pushover | Owner |
| Front / Rear irrigation: no flow, cancelled | No measured flow 30 s after start | Normal | Pushover | Owner |
| Front / Rear irrigation complete | Totaliser ≥ setpoint | Normal | Pushover | Owner |
| BBQ Temperature | every 20 min while `remoteTempEnable` ON | Normal | Pushover | Owner |

_Commented-out (inactive): "Outside Temperature" hourly summary, "Daily Electricity"
(pushover.rules); "Boiler Failed to Start" (boiler1.rules)._

---

## 12. Persistence & Trending

| Service | Strategy | Items / Groups | Purpose |
|---|---|---|---|
| InfluxDB (`influxdb.persist`) | `everyChange` for `*` (all Items) | All Items | Historian for sitemap `Chart` widgets (temperatures, boiler, pressure, humidity, gas, power, moisture, water-butt) and for the rolling-average rules (`average.rules` `historicState`/`averageSince`) |
| MapDB (`mapdb.persist`) | `everyChange, restoreOnStartup` for `*`; default `everyUpdate` | All Items | State restore on boot — relied on by `Reload Variables` (A/B/C/D) and many rules that read last value after restart |

Charts are time-bucketed via `Chart_Period` (0=Hour…4=Year) with `visibility=[Chart_Period==N]`.
Retention/downsampling configured in the InfluxDB service (out-of-repo).

---

## 13. HMI / Sitemap Structure

`sitemap main label="Main Menu"`

```
Main Menu
├─ Frame "Dashboard"
│   ├─ Outdoor temp, indoor avg, Light_Status, gHeating/standby, hStatus
│   ├─ Gate (GY1SS9_switch, gatePosition), Electric Blanket, Presence_Override
│   └─ Energy Meter (GO1EM1_P) → Live data · Consumption · Tariff · V/I/P charts · Settings
├─ Frame "Devices"
│   ├─ Central Heating → System · Room-temp chart · Boiler chart · Radiator status ·
│   │     Temperature control (hSP_* setpoints) · Deltas · Settings (hAway/hWork,
│   │     6 setpoint banks, Boiler run-time, Advanced: hHysteresis/hOverride/radiator overrides)
│   ├─ Sonos → Whole-house transport + Presets (BBC Radio 2 start/stop) + 7 per-room frames (track/volume/mute/transport/join-leave)
│   ├─ Blinds → Settings/Advanced + All/Downstairs/Office/Living Room/Bedroom position controls
│   ├─ Lighting → Hall/Landing dimmers · Kitchen mode/spots/table/glasses/cooker/side ·
│   │     Front Door · Yard · Rear Yard · Camera Lamp
│   ├─ Smart Plugs → Office/Living Room/Bedroom (switch/LED/V/I/P/E/RSSI)
│   ├─ Electric Blanket · Smoke Detection (GY1SA4_*) · Gate (status/remote)
│   ├─ Group gSceneControl · Group gMultisensor
│   ├─ Room Sensors → Temperature/Humidity/Dew/Pressure/Illuminance/Gas
│   ├─ CCTV (only BlueIris_Test live; camera Image/Video widgets commented out)
│   ├─ Irrigation → Front/Rear control + Moisture & Water-butt charts
│   └─ Christmas (visibility=[Christmas_Menu==ON]) → schedule + per-room Xmas relays
└─ Frame "Data"
    ├─ Records → outdoor min/max time-format texts
    ├─ Group gSetpoints "Control" → SwitchBot, Lighting Mode, Motion, Dark-day thresholds,
    │     schedule setpoints, front-light setpoints, timers, Diagnostics (presence, doorbell,
    │     motion, phone — incl. some inactive items, see §14)
    ├─ Charts → gTemperature/gBoiler/gOutside/gPressure/gHumidity/gas
    └─ Sonoff Status → Refresh · Online (~23) · IP · RSSI · Uptime
```

Widgets: `Setpoint`, mapping `Switch` buttons (gate, blinds, lighting mode, kitchen mode,
heating override), `Chart` (period-switched), `Slider` (Sonos volume). No `Webview`;
camera was via `Image`/`Video` (now commented).

---

## 14. Known Issues & TODO

**Seeded findings (status updated against current config):**

- **Duplicate definition — RESOLVED:** `GH1MS1_motion` is now defined once in `items.items`
  (unbound `String`, linked to the Z-Wave multisensor motion channel in the UI via a
  `motion.map` profile). The old MQTT passthrough Item + Thing were removed at the
  SmartThings→Z-Wave cutover (2026-06-02).
- **Group-name mismatch — RESOLVED:** plug groups are now `gPlugSP1/2/3` matching the plug
  membership (`items.items:35-37`).
- **Undefined parent groups — RESOLVED:** `Whg` / `gSpeedtest` removed (Speedtest feature deleted).
- **Label typos — OPEN:** `gIlluminance` labelled "Iluminance" (`items.items:14`); `gPressure`
  and `gOutside` both labelled "Temperature" (`items.items:12-13`).

**New findings (referenced but undefined / dead, cross-checked this pass):**

- **Live widgets/rules on undefined Items:** `BlueIris_motionFront`, `BlueIris_motionRear`
  and `XM1DB1_doorbell` are commented out in `mqtt.items` (no Thing channel) but are still
  referenced by `blueiris.rules` (`Doorbell`, `Front Trigger`, `Rear Trigger` — these rules
  never fire) and `BlueIris_motionFront`/`XM1DB1_doorbell` appear as **live** switches in the
  sitemap "Diagnostics" frame. Define them or remove the references.
- **Astro Thing-UID — RESOLVED (2026-05-31):** `astro:sun:c7d0dedc` is a genuine Astro Thing
  ("Local Sun (Offset)") whose `set#start`/`set#event` channels carry a −30-min offset
  (confirmed from the JSONDB export). So `Sunset -30 Minutes` and `Blinds Sunset -30 Minutes`
  are correct, not stale. The Thing is now declared textually in `things/astro.things`.
- **Duplicate rule name — RESOLVED (2026-05-31):** the second `status.rules` rule (on
  `GY1SS9_Online changed to ON`) was renamed from "Gate Offline" to **"Gate Online"**.
- **All-time temperature bug — RESOLVED (2026-05-31):** "Min/Max Temperatures All Time" now
  formats `Temp_All_*_Time` (not `Temp_Year_*_Time`) and posts `Temp_All_Min.state` into
  `Temp_All_Min_Time_Format`.
- **Mislabelled Online switches — RESOLVED (2026-05-31):** `GS1SS17_Online` label fixed to
  "GS1-SS17" and `GY1SS26_Online` to "GY1-SS26".
- **`GY1SS25_Online` — RESOLVED (2026-05-31):** orphaned (no `GY1SS25` device/Thing); Item
  and its sitemap "Status" entry removed.
- **`HallTemp` / `HallMotion`** (`items.items:526-527`) bind to a `smartthings:…Home:Multisensor`
  channel that doesn't match the `d5f94ca3` instance used elsewhere — verify these resolve.
- **Group aggregation `gHeating` — BY DESIGN, NOT CHANGED:** `gHeating` uses `OR(OFF, ON)`
  vs `OR(ON, OFF)` on `gPlugs`/`gSonoff`. This is **not** display-only — `gHeating`'s
  aggregated state drives the boiler-firing rules (`Heating ON` triggers on `gHeating changed
  to OFF`, `Heating OFF` on `changed to ON`, and `Heating Relax` writes it). Flipping the OR
  order would invert when the gas boiler fires, so it was deliberately left as-is. Change only
  alongside a reviewed/tested rework of the boiler rules.
- **Orphaned transforms — RESOLVED (2026-05-31):** `transform/de.map`, `transform/en.map` and
  `transform/numberToClock.js` removed, along with the now-unused `myClock` Item and its
  commented-out sitemap widget.

---

## 15. Traceability

_No owner requirements document exists in the repo, so this mapping cannot be populated from
config. Provide the requirements list to complete it._

| Requirement | Implemented by | Section |
|---|---|---|
| _(TODO)_ | _(TODO)_ | _(TODO)_ |
