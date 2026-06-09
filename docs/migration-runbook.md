# openHAB 2.5.12 → 5.1 Migration Runbook

> **Strategy:** parallel build. The old Pi (Pi 4, OH 2.5.12) keeps running untouched
> throughout and is **never** decommissioned — it stays on permanently as the Mosquitto
> broker and the SmartThings gate-tile host. The new Pi gets a clean openHABian 5.1 build;
> config is migrated on a git branch; cutover is a hostname/IP swap once validated.
>
> Fill the placeholders before starting:
> `<OLD_PI_IP>`=192.168.0.40  `<NEW_PI_IP>`=192.168.0.57  `<OLD_PI_HOST>`=openhabianpi.local  `<NEW_PI_HOST>`=openHAB5
>
> **Key path/name changes (OH2 → OH5):** `/etc/openhab2`→`/etc/openhab`,
> `/var/lib/openhab2`→`/var/lib/openhab`, `/var/log/openhab2`→`/var/log/openhab`,
> service `openhab2`→`openhab`, CLI `openhab-cli` unchanged.

---

## Decisions locked in (from discovery)

| Area | Decision |
|---|---|
| Broker | Mosquitto **stays on old Pi**; new OH5 connects to `<OLD_PI_IP>`. Tasmota devices untouched. |
| Things | All in JSONDB → **regenerate as textual `.things`** (Claude Code from export). |
| Bindings keep | mqtt, hue, sonos, tplinksmarthome, astro, systeminfo, pushover(action) |
| Bindings drop | exec, expire1, mqtt1, smartthings |
| ipcamera (BlueIris) | **Decide in Phase 2** — BlueIris topics are live but rules commented |
| Persistence | mapdb restore of `Temp_*` records only; InfluxDB **not** migrated; charts start fresh |
| Rules | DSL only; migrate active `.rules`; **drop all `.rulesx`** |
| UI | Basic UI sitemaps carry over; Paper UI → Main UI (admin only) |
| openHAB Cloud | Re-register new instance under existing myopenhab account |
| SmartThings | **Retire except gate.** Z-Wave → ZST39; Brunt → local bridge; gate tile stays on old Pi |
| Secrets | pushover.cfg, broker creds, Brunt login → scp, **never** in git |

---

## Phase 0 — Preparation (no changes to live system)

1. **Buy hardware**
   - Zooz **ZST39 EU (868.42 MHz)** Z-Wave stick — *not* the "LR"/US variant.
   - New Pi: Pi 4 (≥2 GB) or Pi 5, 64-bit, SSD boot preferred. (OH5 is 64-bit only.)

2. **Stabilise the broker address.** On your router, give the **old Pi** a DHCP reservation so `<OLD_PI_IP>` never changes. Everything (Tasmota, SmartThings, new OH5, Brunt bridge) will point here.

3. **Git branch for the migration** (on the dev PC, in the repo):
   ```bash
   git checkout main && git pull
   git checkout -b oh5-migration
   ```
   All transforms happen here; `main` stays as the working OH2 config until cutover.

4. **Export JSONDB for Thing regeneration** (from the PC):
   ```bash
   mkdir -p _migration
   scp openhabian@<OLD_PI_HOST>:/var/lib/openhab2/jsondb/org.eclipse.smarthome.core.thing.Thing.json _migration/
   scp openhabian@<OLD_PI_HOST>:/var/lib/openhab2/jsondb/org.eclipse.smarthome.core.thing.link.ItemChannelLink.json _migration/
   echo "_migration/" >> .gitignore
   ```

5. **Inventory secrets to transfer later** (names only, never values):
   - `services/pushover.cfg` (app token + user key)
   - Mosquitto broker username/password (if set)
   - Brunt app account (email + password) for the new bridge
   - openHAB Cloud will self-generate new credentials on the new Pi

**Rollback:** none needed — nothing touched.

---

## Phase 1 — Stand up base OH5 on the new Pi

1. **Image the new Pi** with openHABian (Raspberry Pi Imager → choose openHABian, latest stable = OH 5.1 + Java 21, 64-bit). Boot, wait for first-run install to finish (can take 30–45 min).

2. **SSH in and confirm the base**:
   ```bash
   ssh openhabian@<NEW_PI_HOST>
   openhab-cli info | grep -i version       # expect 5.1.x
   java -version                            # expect 21
   getconf LONG_BIT                         # expect 64
   ```

3. **Get a clean OH5 running with nothing installed yet.** Confirm Main UI loads at `http://<NEW_PI_HOST>:8080` and the log is clean:
   ```bash
   tail -f /var/log/openhab/openhab.log
   ```

**Validation:** Main UI loads, no ERROR spam.
**Rollback:** re-flash the SD/SSD — old Pi unaffected.

---

## Phase 2 — Transform config on the branch (Claude Code)

Do this on the PC against the `oh5-migration` branch. Review every diff.

1. **Regenerate Things as textual `.things`.** Prompt Claude Code:
   ```
   Read _migration/org.eclipse.smarthome.core.thing.Thing.json and
   _migration/org.eclipse.smarthome.core.thing.link.ItemChannelLink.json. Generate
   textual .things files under things/, grouped by binding (hue, sonos, tplinksmarthome,
   astro, systeminfo, mqtt, ipcamera). For each Thing include its channels. Cross-check
   every ItemChannelLink against existing .items and report any Item linked to a channel
   whose Thing you couldn't generate, or any channel with no Item. Do NOT invent Things.
   Note the mqtt broker bridge must point at <OLD_PI_IP>. Output a summary table of
   Things generated per binding and any unresolved links.
   ```

2. **Apply OH5 config transforms.** Prompt:
   ```
   Transform this OH2.5 config for OH5 on the oh5-migration branch:
   - Remove any references to dropped bindings: exec, expire, mqtt1, smartthings.
   - Delete all .rulesx files (not migrating them).
   - Verify .rules DSL for OH5 compatibility; flag (don't auto-change) anything deprecated. Full rules conversion is handled in Phase 2a.
   - Confirm no .js transforms exist; leave map/jsonpath/regex as-is.
   - Create services/addons.cfg listing only: binding=mqtt,hue,sonos,tplinksmarthome,
     astro,systeminfo  / persistence=mapdb,rrd4j  / transformation=map,jsonpath,regex
     / misc=openhabcloud  / package=standard  (NO pushover yet — added to the binding line in Phase 3, since OH5 pushover is a binding, not an action).
   - Produce a short report of every change and every flagged item.
   Show diffs; change nothing I haven't approved.
   ```

3. **Decide ipcamera/BlueIris.** Look at `rules/blueiris.rules` (rules are commented, but `BlueIris/app` + `BlueIris/status` MQTT topics are live). Keep the ipcamera Thing only if you intend to use it; otherwise drop it from the generated `.things`.

4. **Naming check.** Have Claude Code flag the `FB1-SS6` vs `FB1_SS6` hyphen/underscore duplication seen on MQTT, plus any other drift, so you can reconcile device topics before they cause silent gaps.

5. Commit the branch:
   ```bash
   git add -A && git commit -m "OH5 migration: textual Things + config transforms"
   git push -u origin oh5-migration
   ```

**Validation:** clean diffs, no unresolved ItemChannelLinks you care about.
**Rollback:** `git checkout main` — branch is isolated.

---

## Phase 2a — Rules conversion (DSL carries over, two real changes)

DSL `.rules` are still supported in OH5, so rule *structure* is unchanged. Two OH2→OH3
changes affect many of your files and must be converted (not just flagged):

- **Pushover (major):** your `sendPushoverMessage(pushoverBuilder(...))` /
  `.withEmergencyPriority()` / `cancelPushoverEmergency(...)` calls are the OH2 **action**
  API (configured via `services/pushover.cfg`). OH5 uses a **binding + Thing**:
  `getActions("pushover","pushover:pushover-account:account")` then `actions.sendMessage(...)`.
  The PushoverBuilder was NOT carried over — all ~35 call sites across 9 files need rewriting,
  including the emergency-priority boiler/heating/gate alerts (priority becomes a parameter).
- **Joda-Time → java.time:** OH3 swapped the DSL date/time library. Anything using `now`,
  `DateTimeType`, `.plusMinutes()`/date math, `.getMillis()` (heating, boiler, gate,
  irrigation, blinds timers) needs checking — most method names survive; a few change.

Everything else (`sendCommand`, `postUpdate`, `createTimer`, `logInfo`, group/member
iteration, lambdas, global vars) carries over as-is.

**Step 1 — Audit (no changes).** Prompt Claude Code:
```
Audit all active .rules for OH2.5→OH5 compatibility. Produce a table: file | rule |
issue-type | line. Issue types: (a) pushover action call (sendPushoverMessage/
pushoverBuilder/cancelPushoverEmergency), (b) Joda/DateTime usage (now, DateTimeType,
.plusX, .getMillis, date math), (c) other deprecated DSL. Do NOT change anything yet.
Count pushover calls and flag which use emergency priority.
```

**Step 2 — Stand up the Pushover binding first** (during Phase 3): install the Pushover
binding, create a textual `pushover-account` Thing with the token + user key from the old
`pushover.cfg`, confirm ONLINE with a test message. Add `action` is NOT needed — it's a binding now.

**Step 3 — Convert pushover behind a reusable helper.** Prompt:
```
Convert all pushover calls to the OH5 binding. Create reusable lambdas `pushover` and
`pushoverEmergency` wrapping getActions("pushover","pushover:pushover-account:account")
.sendMessage(...), so call sites become e.g. pushover.apply("msg"). Map
.withEmergencyPriority() to the emergency-priority sendMessage parameters, and handle
cancelPushoverEmergency. Show every changed line as a diff.
```

**Step 4 — Convert Joda/time issues** from the audit, file by file, reviewing diffs.

**Step 5 — Test live, ONE file at a time** (during Phase 7): OH5 hot-loads `.rules` and
logs parse/runtime errors immediately. Deploy each converted rule file singly, watch
`/var/log/openhab/openhab.log`, confirm no error and the rule fires, then move on. Do NOT
convert-and-deploy all files at once — the emergency boiler/gate alerts must be verified individually.

**Validation:** every rule file loads without error; a test fire of each pushover path
(esp. emergency alerts) actually notifies.
**Rollback:** per-file on the branch — revert the one rule file that errored; others unaffected.

---

## Phase 3 — Deploy config + bindings to the new Pi

1. **Pull the branch onto the new Pi.** Initialise the repo at `/etc/openhab` (note new path):
   ```bash
   ssh openhabian@<NEW_PI_HOST>
   cd /etc/openhab
   sudo git init && sudo git config --global --add safe.directory /etc/openhab
   sudo git remote add origin <your-repo-ssh-url>
   sudo git fetch origin && sudo git checkout oh5-migration
   ```
   (Generate an SSH key for root on the new Pi and add it to GitHub first, same as before.)

2. **Install bindings.** With `services/addons.cfg` in place, OH5 installs them automatically. Confirm in Main UI → Settings → Add-ons, or:
   ```bash
   tail -f /var/log/openhab/openhab.log    # watch features install
   ```

3. **MQTT bridge → old Pi.** Your generated `mqtt:broker` Thing must have `host=<OLD_PI_IP>` and the broker credentials. Verify the bridge comes ONLINE and `mqtt:topic` Things start populating Items.

4. **Pushover binding + account Thing** (replaces the OH2 action — see Phase 2a). Don't copy `pushover.cfg`; in OH5 the token/user key live in a `pushover-account` Thing. Read the old keys for reference only (don't commit them):
   ```bash
   ssh openhabian@<OLD_PI_HOST> 'sudo cat /etc/openhab2/services/pushover.cfg'   # note token + user key
   ```
   Add `pushover` to the `binding=` line in `addons.cfg`, then create the account Thing textually (keys are secrets — keep this `.things` line out of git or use a secrets include):
   ```
   Thing pushover:pushover-account:account [ apikey="<TOKEN>", user="<USER_KEY>" ]
   ```
   Confirm the Thing is ONLINE and send a test message before converting the rule call sites.

5. **Other secrets** (out of git):
   - Mosquitto broker creds: stay on the old Pi (broker not moving).
   - Brunt app login: added in Phase 5 (`/etc/brunt-bridge/secrets.env`).

6. **Re-auth cloud/LAN bindings:**
   - **hue:** add bridge Thing → **press the physical button** on the Hue bridge to authorise → bulbs rediscover.
   - **sonos:** auto-discovers on the LAN; confirm players come ONLINE. **Multi-homed gotcha (hit during migration):** the new Pi runs Tailscale (`tailscale0`, 100.x) alongside `eth0`, and openHAB's jUPnP can bind UPnP discovery to the wrong interface → every player shows `OFFLINE / COMMUNICATION_ERROR / "not available in local network"` even though the textual Things/UDNs are correct. Fix: **Settings → Network Settings → Primary Address = `192.168.0.57/24`** (the eth0 address — *not* Tailscale `100.x` or a docker `172.x` bridge), then restart the Sonos binding (persists as `primaryAddress` in `/var/lib/openhab/config/org/openhab/network.config`). The same fix applies to any UPnP-discovered binding (e.g. hue bridge discovery).
   - **tplinksmarthome:** LAN-local; confirm the 3 HS110 plugs discovered (same subnet as new Pi).
   - **astro:** set system location (Main UI → Settings → Regional) or geolocation on the Thing.

**Validation:** MQTT Items updating from live Tasmota data; hue/sonos/tplink ONLINE; a test pushover sends.
**Rollback:** `sudo git checkout main` is N/A (new Pi only has the branch); to undo, stop `openhab` — old Pi still fully live.

---

## Phase 4 — Z-Wave (replaces SmartThings Z-Wave devices)

1. Plug the **ZST39** into the new Pi. Find its port:
   ```bash
   ls -l /dev/serial/by-id/    # use this stable path, not /dev/ttyACM0
   ```
2. Install the **Z-Wave binding** (Main UI → Add-ons). Add the **Z-Wave Serial Controller** Thing, set the serial port to the by-id path.
3. **Re-pair devices** (exclude from SmartThings first, then include on openHAB). Do the **smoke alarms first and verify alarm reporting**:
   - Multisensor (GH1-MS1) — active
   - Smoke Alarm Kitchen (GK1-SA1) — active
   - Smoke Alarm Landing (FL1-SA2) — revive or drop (offline since 2020 — check the unit physically)
   - Energy Monitor (GO1-EM1) — revive or drop (offline since 2024)
   - Scene Controller (FB1-SC1) — revive or drop (offline since 2023)
4. Each paired device appears as a Thing with channels; create textual `.things`/Items and link to your existing Item names. Commit to the branch.

**Validation:** each device reports state; smoke alarms confirmed working before relying on them.
**Rollback:** devices can be re-included back into SmartThings if needed (old hub still alive).

---

## Phase 5 — Brunt blinds (local MQTT→Brunt bridge)

Brunt is cloud-only (no local API), so this replaces SmartThings' cloud bridging with a local service that reuses your existing MQTT topics — **openHAB needs no change.**

1. Prompt Claude Code:
   ```
   Write a Python service for the new Pi that bridges MQTT to the Brunt cloud, replacing
   SmartThings' role for the 3 Brunt Blind Engines. It must:
   - Use the `brunt` PyPI library and a Brunt app account (creds from env/secret file, not code).
   - Subscribe to the SAME MQTT topics openHAB currently publishes blind commands to
     (derive them from rules/blinds.rules and the blind Items), so openHAB is unchanged.
   - Translate position/open/close commands to Brunt API calls and publish blind state back.
   - Reconnect on broker/cloud drop; log clearly.
   Provide the script, a requirements list, and a systemd unit (runs as a non-root user,
   reads creds from /etc/brunt-bridge/secrets.env which is chmod 600 and NOT in git).
   ```
2. Install on the new Pi, add Brunt creds to `/etc/brunt-bridge/secrets.env`, enable the service:
   ```bash
   pip install brunt paho-mqtt --break-system-packages
   sudo systemctl enable --now brunt-bridge
   journalctl -u brunt-bridge -f
   ```

**Validation:** moving a blind from the openHAB sitemap actuates the physical blind; state reflects back.
**Caveat:** cloud-dependent; if Brunt changes their API the bridge may need updating.
**Rollback:** stop `brunt-bridge`; SmartThings still bridges blinds on the old hub until you tear it down (Phase 8).

---

## Phase 6 — Persistence (records only)

1. Configure **rrd4j** as default persistence (for future charts) and **mapdb** for restore-on-startup.
2. Restore the temperature **records** via mapdb:
   ```bash
   # copy the mapdb store from old Pi to new (records: Temp_*_Min/Max etc.)
   scp openhabian@<OLD_PI_HOST>:/var/lib/openhab2/persistence/mapdb/storage.mapdb* /tmp/
   scp /tmp/storage.mapdb* openhabian@<NEW_PI_HOST>:/tmp/
   ssh openhabian@<NEW_PI_HOST> 'sudo systemctl stop openhab; sudo mkdir -p /var/lib/openhab/persistence/mapdb; sudo mv /tmp/storage.mapdb* /var/lib/openhab/persistence/mapdb/; sudo chown -R openhab:openhab /var/lib/openhab/persistence/mapdb; sudo systemctl start openhab'
   ```
   Configure mapdb `restoreOnStartup` for the `Temp_*` Items.
3. **Fallback if mapdb format doesn't restore cleanly:** manually re-seed the irreplaceable records (`Temp_All_*`, `Temp_Year_*`) with `postUpdate`. **Note the all-time max of 41.7 looked like a sensor spike — consider re-seeding a clean value** rather than carrying it over.

**Validation:** Records frame in the sitemap shows values after restart.
**Rollback:** records are non-critical; charts simply rebuild from fresh.

---

## Phase 7 — Parallel validation

Run both Pis side by side. Old Pi stays authoritative until this passes.

Checklist:
- [ ] All Tasmota sensor Items updating on new Pi (compare a few against old Pi values)
- [ ] hue / sonos / tplink controllable
- [ ] Heating, boiler, gate, irrigation rules behave (test cautiously — these have emergency-priority pushover alerts)
- [ ] pushover notifications arrive
- [ ] Z-Wave devices reporting; **smoke alarms verified**
- [ ] Brunt blinds move and report
- [ ] Records restored
- [ ] Basic UI sitemap renders; navigation works
- [ ] No persistent ERRORs in `/var/log/openhab/openhab.log`

Let it run a few days. Watch for intermittent issues (rule timers, MQTT reconnects).

---

## Phase 8 — Cutover

1. **openHAB Cloud:** install the openHAB Cloud connector on the new Pi, register the new UUID/secret under your **existing myopenhab account** (Main UI → Add-ons → openHAB Cloud Connector; then myopenhab.org → add the new instance). Remove the old instance once confirmed.
2. **Hostname/IP swap:** point your remote-access and any device/dashboard that addressed the *old* openHAB at the new Pi. (Broker stays at `<OLD_PI_IP>` — do **not** repoint Tasmota.) Tailscale: confirm the new Pi is on your tailnet.
3. **Merge the branch** once happy:
   ```bash
   git checkout main && git merge oh5-migration && git push
   ```
4. **SmartThings teardown — partial.** Remove all devices/integrations from SmartThings **except the gate virtual switch**. Keep the SmartThings hub + the gate virtual switch + the TAustin MQTT driver running on the **old Pi** so the Android Auto gate tile still works, state-synced from openHAB via MQTT.

**Validation:** new Pi is your daily driver; gate tile in Android Auto still functions; old Pi now only serves broker + gate.
**Rollback:** repoint remote access back to old Pi; it remains a complete OH2.5.12 system.

---

## Phase 9 — Steady state

Old Pi (Pi 4, OH 2.5.12) permanent role:
- Mosquitto broker (`<OLD_PI_IP>`, DHCP-reserved)
- SmartThings hub + gate virtual switch (Android Auto tile)

New Pi (OH5.1) role: everything else.

Then resume the normal git workflow from `main`: review in Claude Code → commit/push on PC → `sudo git pull` on the new Pi (path `/etc/openhab`, service `openhab`), with the log tailing. Keep `docs/FDS.md` updated per the `CLAUDE.md` rule — and add the new architecture (two-Pi split, Brunt bridge, Z-Wave) to it.

### Model reload latency after `git pull` (OH5)

`.items` reload promptly, but `.rules` and `.sitemap` can lag noticeably (sometimes a minute or more) before openHAB re-reads them from disk. Practical notes:

- **Don't judge a pull by the log.** `.sitemap` reloads are silent and `.rules` only log on a parse error or first fire — verify functionally (the UI shows the change / the rule fires), not by waiting for a log line.
- **`touch` does nothing** — OH5's watcher detects changes by file **content** (hash), not mtime. And don't append to a model file to force it: that dirties the git-tracked working tree and will block the next `sudo git pull`.
- **Force an immediate re-scan without a full restart** via the Karaf console (already running, connects instantly; rescans all model files in a few seconds):
  ```bash
  openhab-cli console            # default password: habopen
  bundle:restart org.openhab.core.model.core
  logout
  ```
- A full `sudo systemctl restart openhab` also works but takes ~1–2 min.
- **If the lag is consistently long**, the watcher is probably polling instead of using native filesystem events. Raise the inotify limit, then restart once; future pulls then reload near-instantly:
  ```bash
  echo "fs.inotify.max_user_watches=524288" | sudo tee /etc/sysctl.d/60-openhab-inotify.conf
  sudo sysctl --system
  ```

---

## Open items to carry forward
- ipcamera/BlueIris: decide keep vs drop (Phase 2).
- The 3 long-offline Z-Wave devices: revive or retire (Phase 4).
- Brunt bridge: monitor for API breakage; consider Z-Wave/Zigbee blind motors long-term for true local control.
- Eventually retire the SmartThings hub entirely if you replace the gate tile with another method (geofence, fob).
