#!/usr/bin/env python3
"""
Brunt <-> MQTT bridge for openHAB.

Subscribes to the existing Tasmota-style command topics that openHAB's blind
'Position' things publish to, and relays each commanded position to the Brunt
cloud via the `brunt` library. Replaces the old SmartThings->Brunt relay.

openHAB things are command-only (commandTopic, no stateTopic), so this bridge
is primarily a COMMAND relay. Optional position feedback can be enabled by
setting PUBLISH_STATE=true (publishes to stat/<blind>/POSITION) if you later
add stateTopics in openHAB.

Secrets are read from environment (see /etc/brunt-bridge/secrets.env).
"""

import asyncio
import logging
import os
import signal
import sys

import paho.mqtt.client as mqtt
from brunt import BruntClientAsync

# ---- Config from environment -------------------------------------------------
BRUNT_USER = os.environ.get("BRUNT_USER", "")
BRUNT_PASS = os.environ.get("BRUNT_PASS", "")

MQTT_HOST = os.environ.get("MQTT_HOST", "192.168.0.40")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASS = os.environ.get("MQTT_PASS", "")

PUBLISH_STATE = os.environ.get("PUBLISH_STATE", "false").lower() == "true"
STATE_POLL_SEC = int(os.environ.get("STATE_POLL_SEC", "60"))

# Position polarity. Brunt: 100 = fully open, 0 = fully closed.
# openHAB gBlinds mapping: 100 = Open, 1 = Close  -> same direction.
# If blinds end up inverted after a live test, set INVERT=true in secrets.env.
INVERT = os.environ.get("INVERT", "false").lower() == "true"

# ---- Topic <-> Brunt blind-name mapping -------------------------------------
# command topic (subscribed) -> Brunt app device name
TOPIC_TO_BRUNT = {
    "cmnd/GO1-BE1/POSITION": "Office",
    "cmnd/GL1-BE2/POSITION": "Living Room",
    "cmnd/FB1-BE3/POSITION": "Bedroom",
}
# reverse, for optional state publishing
BRUNT_TO_BASE = {
    "Office": "GO1-BE1",
    "Living Room": "GL1-BE2",
    "Bedroom": "FB1-BE3",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("brunt-bridge")


def clamp_pos(raw: str) -> int:
    """Parse an incoming MQTT payload to a 0-100 int, applying optional invert."""
    try:
        val = int(round(float(raw)))
    except (ValueError, TypeError):
        raise ValueError(f"non-numeric position payload: {raw!r}")
    val = max(0, min(100, val))
    if INVERT:
        val = 100 - val
    return val


class Bridge:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.brunt = None  # created in run(), inside the running loop
        self._brunt_lock = asyncio.Lock()
        self.mqttc = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="brunt-bridge"
        )
        if MQTT_USER:
            self.mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
        self.mqttc.on_connect = self._on_connect
        self.mqttc.on_message = self._on_message

    # ---- MQTT callbacks (run in paho's network thread) ----
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            log.info("Connected to MQTT %s:%s", MQTT_HOST, MQTT_PORT)
            for topic in TOPIC_TO_BRUNT:
                client.subscribe(topic)
                log.info("Subscribed: %s", topic)
        else:
            log.error("MQTT connect failed: %s", reason_code)

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", "ignore").strip()
        brunt_name = TOPIC_TO_BRUNT.get(msg.topic)
        if not brunt_name:
            return
        try:
            pos = clamp_pos(payload)
        except ValueError as e:
            log.warning("Ignoring %s: %s", msg.topic, e)
            return
        log.info("CMD %s -> Brunt '%s' = %d", msg.topic, brunt_name, pos)
        # hand off to the asyncio loop (we're on paho's thread here)
        asyncio.run_coroutine_threadsafe(
            self._set_position(brunt_name, pos), self.loop
        )

    # ---- Brunt operations (asyncio) ----
    async def _set_position(self, brunt_name: str, pos: int):
        async with self._brunt_lock:
            try:
                await self.brunt.async_login()
                await self.brunt.async_change_request_position(
                    position=pos, name=brunt_name
                )
                log.info("Brunt '%s' set to %d OK", brunt_name, pos)
            except Exception as e:  # noqa: BLE001 - cloud API, catch all
                log.error("Brunt set '%s'=%d failed: %s", brunt_name, pos, e)

    async def _poll_states(self):
        """Optional: publish current position back to stat/<blind>/POSITION."""
        while True:
            await asyncio.sleep(STATE_POLL_SEC)
            if not PUBLISH_STATE:
                continue
            async with self._brunt_lock:
                try:
                    await self.brunt.async_login()
                    things = await self.brunt.async_get_state()
                except Exception as e:  # noqa: BLE001
                    log.error("Brunt poll failed: %s", e)
                    continue
            # things structure varies by lib version; guard defensively
            try:
                for thing in things.get("things", []):
                    name = thing.get("NAME") or thing.get("name")
                    base = BRUNT_TO_BASE.get(name)
                    if not base:
                        continue
                    pos = thing.get("currentPosition") or thing.get("position")
                    if pos is None:
                        continue
                    if INVERT:
                        pos = 100 - int(pos)
                    self.mqttc.publish(f"stat/{base}/POSITION", str(int(pos)))
            except Exception as e:  # noqa: BLE001
                log.error("State publish error: %s", e)

    async def run(self):
        # aiohttp ClientSession (inside Brunt client) needs a running loop
        self.brunt = BruntClientAsync(username=BRUNT_USER, password=BRUNT_PASS)
        self.mqttc.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.mqttc.loop_start()
        try:
            await self._poll_states()
        finally:
            self.mqttc.loop_stop()
            await self.brunt.async_close()


def main():
    if not BRUNT_USER or not BRUNT_PASS:
        log.error("BRUNT_USER / BRUNT_PASS not set (check secrets.env)")
        sys.exit(1)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bridge = Bridge(loop)

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async def runner():
        task = loop.create_task(bridge.run())
        await stop.wait()
        task.cancel()

    try:
        loop.run_until_complete(runner())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
