# Node 4 — Command Centre

Device name: `node-4-command-centre`

Node 4 is the central command terminal: a manual emergency button, a status display, and a master alarm buzzer that can be triggered locally or remotely.

## Hardware

| Component | Connection | Purpose |
| --------- | ---------- | ------- |
| Push button | `D2 -> switch -> GND`, using `INPUT_PULLUP` | Manual emergency trigger |
| Passive buzzer | `D3` (tone-driven) | Master alarm |
| 16x2 I2C LCD | `SDA -> A4`, `SCL -> A5`, `5V`, `GND` | Status display |

## Telemetry

The Arduino sends one telemetry line approximately once per second, as comma-separated `key=value` pairs (the same wire format as Node 3 — not JSON).

| Key | Type | Description |
| --- | ---- | ----------- |
| `manual_emergency` | Boolean | Button state (true while held) |
| `display_state` | String | `SAFE` or `LOCKDOWN` — what the LCD is currently showing |
| `master_buzzer` | Boolean | Current buzzer state |

Example (raw serial line from the Arduino):

```
manual_emergency=false, display_state=SAFE, master_buzzer=false
```

The edge service parses this line and republishes it to ThingsBoard as JSON telemetry with the same keys.

## RPC

ThingsBoard sends RPC commands to the edge. The edge converts them to Arduino serial commands and waits for the matching ACK.

| RPC | `true` | `false` |
| --- | ------ | ------- |
| `setLockdown` | `LOCKDOWN_ON` | `LOCKDOWN_OFF` |
| `setBuzzer` | `BUZZER_ON` | `BUZZER_OFF` |

`setLockdown` is the primary command-centre action: it sets `display_state` and `master_buzzer` together. `setBuzzer` controls the buzzer independently, for testing or a buzzer-only alert.

Example response:

```
{"success": true, "method": "setLockdown", "lockdown_active": true}
```

(`lockdown_active` is used here rather than `display_state`, since the RPC's own params are boolean and `display_state` is a string field in the telemetry registry.)

A command is successful only after the edge receives the matching acknowledgement, for example:

```
LOCKDOWN_ON
ACK=LOCKDOWN_ON
```

## ThingsBoard flow

```
Arduino
   ↓ serial telemetry (key=value)
Python edge
   ↓ MQTT (JSON)
ThingsBoard
   ↓ RPC
Python edge
   ↓ serial command
Arduino
   ↓ ACK
Python edge
   ↓ RPC response
ThingsBoard
```

## Source status

The web application displays each node as:

- `LIVE` — fresh ThingsBoard telemetry is available.
- `SIMULATED` — live telemetry is unavailable or stale.

## Edge configuration

Node 4 uses (see `devices/node4/.env.example`):

```
SERIAL_PORT
SERIAL_BAUD_RATE
SERIAL_TIMEOUT
POLL_INTERVAL
ACK_TIMEOUT

THINGSBOARD_ENABLED
THINGSBOARD_HOST
THINGSBOARD_PORT
THINGSBOARD_ACCESS_TOKEN
THINGSBOARD_TLS
DEVICE_ID
```

`THINGSBOARD_ACCESS_TOKEN` identifies the MQTT device and must not be committed. Leave `SERIAL_PORT` blank to have the edge auto-detect the Arduino's port.

## Verification

1. Upload `devices/node4/firmware/node4.ino`.
2. Close Arduino Serial Monitor.
3. Start the Node 4 edge service: `python -m devices.node4.edge.main`.
4. Confirm telemetry updates in ThingsBoard.
5. Press the manual emergency button and confirm `manual_emergency` and `display_state` update.
6. Test `setLockdown` and `setBuzzer` from ThingsBoard (or the web app's Control panel, once Node 4 is registered with RPC methods in `backend/app/nodes/registry.py`).
7. Confirm the physical output (LCD + buzzer) and matching ACK.
8. Verify the updated state is returned to ThingsBoard.
