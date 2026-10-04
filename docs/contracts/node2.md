# Node 2 — Hallway / Exit Monitoring

Device name: `node-2-exit-monitoring`

Node 2 watches the hallway exit with an ultrasonic distance sensor. It shows people whether the exit route is clear (green LED) or blocked (red LED), and it can be put into evacuation guidance mode or closed remotely from ThingsBoard or the web app.

## Hardware

| Component | Connection | Purpose |
| --- | --- | --- |
| HC-SR04 ultrasonic sensor | `VCC -> 5V`, `Trig -> D4`, `Echo -> D3`, `GND -> GND` | Distance to the nearest object in front of the exit |
| Green LED + 220 Ω resistor | `D5 -> LED (+)`, `LED (-) -> 220 Ω -> GND` | Exit clear; flashes during evacuation ("exit this way") |
| Red LED + 220 Ω resistor | `D6 -> LED (+)`, `LED (-) -> 220 Ω -> GND` | Exit blocked or closed by the command centre |
| Passive buzzer | `+ -> 5V`, `- -> NPN collector` | Local warning when the exit is blocked during an evacuation |
| NPN transistor (PN2222 / S8050 / BC337) + 1 kΩ | `D2 -> 1 kΩ -> base`, `emitter -> GND` | Switches the buzzer so it is louder than driving it straight from a pin |
| Arduino Uno | USB to the edge PC/VM | Sensing, local rule, serial protocol |

Wiring diagram: [`docs/node2-wiring.png`](../node2-wiring.png)

## Local (edge) rule

The Arduino runs this rule by itself, so the exit sign still works if the PC or cloud is offline:

```text
distance = median of the last 5 readings (taken every 100 ms)

IF distance < threshold_cm for 3 seconds          THEN exit_blocked = true
IF distance >= threshold_cm for 2 seconds         THEN exit_blocked = false

LED / buzzer output:
  exit_closed = true            -> red on (flashing during evacuation), green off
  exit_blocked = true           -> red on, buzzer pulses if evacuation_mode = true
  otherwise                     -> green on (flashing if evacuation_mode = true)
```

No-echo handling: a single missed echo is ignored. If the last good reading was below `threshold_cm`, a missing echo is treated as "object right against the sensor" (the HC-SR04 cannot measure under ~3 cm), so the exit stays blocked. If the last reading was far, 1 s without echo means nothing within 4 m (`distance_cm = 400`).

The 3-second hold means a person walking past the exit does not count as a blockage. The median filter removes single bad readings. `threshold_cm` is saved in EEPROM so it survives a power cycle.

## Telemetry

One line per second over serial, comma-separated `key=value` pairs (same wire format as Node 3 and Node 4):

```text
distance_cm=123.4, exit_blocked=false, threshold_cm=50, evacuation_mode=false, exit_closed=false, buzzer_state=false, sensor_ok=true
```

| Key | Type | Description |
| --- | --- | --- |
| `distance_cm` | Number `0–400` | Filtered distance in centimetres (400 = nothing in range) |
| `exit_blocked` | Boolean | Derived state from the local rule above |
| `threshold_cm` | Integer `5–300` | Current blocking threshold |
| `evacuation_mode` | Boolean | Evacuation guidance is active |
| `exit_closed` | Boolean | Route closed by the command centre / cloud rule |
| `buzzer_state` | Boolean | Manual buzzer state |
| `sensor_ok` | Boolean | `false` if the sensor gives no echo for 5 s, or the edge receives no frames for 5 s |

The edge validates every frame (all keys present, correct types, distance within `0–400`) and publishes it to ThingsBoard as JSON with QoS 1.

## RPC

ThingsBoard sends RPC commands to the edge. The edge converts them to serial commands and replies only after the matching ACK from the Arduino.

| RPC | Params | Serial command | ACK |
| --- | --- | --- | --- |
| `setEvacuation` | `true` / `false` | `EVAC_ON` / `EVAC_OFF` | `ACK=EVAC_ON` / `ACK=EVAC_OFF` |
| `setExitClosed` | `true` / `false` | `EXIT_CLOSE` / `EXIT_OPEN` | `ACK=EXIT_CLOSE` / `ACK=EXIT_OPEN` |
| `setBuzzer` | `true` / `false` | `BUZZER_ON` / `BUZZER_OFF` | `ACK=BUZZER_ON` / `ACK=BUZZER_OFF` |
| `setThreshold` | number `5–300` | `THRESHOLD=<n>` | `ACK=THRESHOLD=<n>` |
| `getState` | none | — (answered by the edge) | — |

`setEvacuation`, `setExitClosed` and `setBuzzer` are registered in `backend/app/nodes/registry.py`, so they appear on the web app's **Control** page. `setThreshold` takes a number, so it is used from a ThingsBoard dashboard widget or rule chain instead (the web API only sends booleans).

Example response:

```json
{"success": true, "method": "setThreshold", "threshold_cm": 40}
```

If the Arduino rejects a command (`ERROR=...`) or does not answer within `ACK_TIMEOUT`, the response is `{"success": false, "error": "..."}`.

## Remote configuration with a shared attribute

The edge also subscribes to ThingsBoard shared attributes. Setting the shared attribute `threshold_cm` on the device (for example to `40`) sends `THRESHOLD=40` to the Arduino. On every (re)connect the edge asks ThingsBoard for the current value, so a change made while the node was offline is applied when it comes back.

## MQTT topics

| Direction | Topic |
| --- | --- |
| Telemetry (edge → cloud) | `v1/devices/me/telemetry` |
| RPC request (cloud → edge) | `v1/devices/me/rpc/request/+` |
| RPC response (edge → cloud) | `v1/devices/me/rpc/response/{request_id}` |
| Shared attribute updates (cloud → edge) | `v1/devices/me/attributes` |
| Attribute request / response | `v1/devices/me/attributes/request/1` / `v1/devices/me/attributes/response/+` |

All messages use QoS 1 over TLS (port 8883). The Paho client reconnects automatically (1–30 s back-off).

## Edge configuration

See `devices/node2/.env.example`:

```text
SERIAL_PORT              blank = auto-detect
SERIAL_BAUD_RATE
SERIAL_TIMEOUT
POLL_INTERVAL
ACK_TIMEOUT
STALE_AFTER              seconds without frames before sensor_ok=false is published

THINGSBOARD_ENABLED
THINGSBOARD_HOST
THINGSBOARD_PORT
THINGSBOARD_ACCESS_TOKEN
THINGSBOARD_TLS
DEVICE_ID
```

`THINGSBOARD_ACCESS_TOKEN` must not be committed.

## Verification

1. Upload `devices/node2/firmware/node2/node2.ino` and check the telemetry line in Serial Monitor.
2. Close Serial Monitor.
3. Run `python -m devices.node2.edge.main`.
4. Confirm the seven keys update in ThingsBoard **Latest telemetry**.
5. Hold an object closer than `threshold_cm` for 3 s — red LED on, `exit_blocked = true`.
6. Send `setEvacuation(true)` — green LED flashes; block the exit — buzzer pulses.
7. Send `setExitClosed(true)` — red LED on even with nothing in front.
8. Send `setThreshold(30)` or set the shared attribute `threshold_cm = 30` — `threshold_cm` telemetry changes to 30.
9. Unplug the Arduino — `sensor_ok = false` appears within 5 s.
