# Adding a physical node

Each teammate owns one node folder:

| Node | Folder |
| --- | --- |
| Node 1 | `devices/node1` |
| Node 2 | `devices/node2` |
| Node 3 | `devices/node3` |
| Node 4 | `devices/node4` |

1. Create your node folder. You may copy an existing node as a starting point, but keep firmware, parsing and RPC mapping specific to your hardware.
2. Add the Arduino/MCU firmware and verify serial telemetry locally first.
3. Define the node's telemetry fields, types and units in `backend/app/nodes/registry.py`.
4. Register only RPC methods that are supported by the firmware and return a matching ACK.
5. Create the ThingsBoard device using **Add Node** in the web app or the ThingsBoard UI. Use the stable device name from the registry.
6. Copy the node's `.env.example` to `.env` and add its ThingsBoard device token. Do not commit the token.
7. Start the edge service and confirm telemetry appears in **ThingsBoard → Latest Telemetry**.
8. Confirm the web app changes the node from **SIMULATED** to **LIVE** once fresh telemetry is available.
9. Test each registered RPC method and verify the physical actuator response and ACK.
10. Commit your node folder. Update shared files only when the shared contract or infrastructure genuinely needs to change.

Reuse the common serial, MQTT and ACK patterns where they fit. Keep pins, firmware, telemetry parsing and actuator commands node-specific.

## Run an edge on a VM (Virtual Box)

Check the current address from the VM console:

```bash
hostname -I
sudo systemctl enable --now ssh
```

Connect from Windows using the address from the VM hostname:

```powershell
ssh admin@<vm-ip>
```

Prepare the project once:

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip
git clone https://github.com/Leissha/Smart-Multizone-Evacuation-System.git
cd smart-multizone-evacuation
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-edge.txt
```

Copy the node's example settings, add its ThingsBoard token and run its edge module. For Node 3:

```bash
cp devices/node3/.env.example devices/node3/.env
nano devices/node3/.env
.venv/bin/python -m devices.node3.edge.main
```
