# Brunt bridge install (run on the new Pi)

## 1. Place files
sudo mkdir -p /opt/brunt-bridge
sudo cp brunt_bridge.py /opt/brunt-bridge/
sudo mkdir -p /etc/brunt-bridge

## 2. Python venv + deps (brunt + paho-mqtt 2.x)
sudo python3 -m venv /opt/brunt-bridge/venv
sudo /opt/brunt-bridge/venv/bin/pip install --upgrade pip
sudo /opt/brunt-bridge/venv/bin/pip install "paho-mqtt>=2.0" brunt

## 3. Secrets (NOT in git)
sudo cp secrets.env.example /etc/brunt-bridge/secrets.env
sudo nano /etc/brunt-bridge/secrets.env      # fill BRUNT_PASS + MQTT_PASS
sudo chmod 600 /etc/brunt-bridge/secrets.env
sudo chown openhab:openhab /etc/brunt-bridge/secrets.env

## 4. Ownership of code
sudo chown -R openhab:openhab /opt/brunt-bridge

## 5. systemd
sudo cp brunt-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now brunt-bridge

## 6. Watch it
journalctl -u brunt-bridge -f

## Test
# In openHAB, command one blind (e.g. set GO1BE1_position to 50, or use the
# overview "All blinds" / blinds page). Watch the journal: you should see
#   CMD cmnd/GO1-BE1/POSITION -> Brunt 'Office' = 50
#   Brunt 'Office' set to 50 OK
# and the physical blind should move. If it moves the WRONG way, set INVERT=true
# in secrets.env and: sudo systemctl restart brunt-bridge
