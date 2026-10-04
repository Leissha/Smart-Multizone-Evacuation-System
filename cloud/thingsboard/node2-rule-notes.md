# Node 2 ThingsBoard setup and rules

## Device

1. Create a device named `node-2-exit-monitoring` (device profile: default, or an `Exit Monitor` profile).
2. Copy its access token into `devices/node2/.env` as `THINGSBOARD_ACCESS_TOKEN`.
3. Add a **shared attribute** `threshold_cm` (integer, for example `50`). Changing it reconfigures the Arduino.

## Dashboard widgets

| Widget | Data |
| --- | --- |
| Time-series line chart | `distance_cm` with `threshold_cm` as a second series |
| LED indicator / state card | `exit_blocked`, `exit_closed`, `evacuation_mode`, `sensor_ok` |
| Switch control (RPC) | `setEvacuation`, `setExitClosed`, `setBuzzer` (boolean params) |
| Knob / slider control (RPC) | `setThreshold` (5–300) |
| Update shared attribute | `threshold_cm` |

## Rule 1 — Exit Blocked alarm (single device)

In the device profile **Alarm rules** (or a rule chain):

```text
Create alarm "Exit Blocked" (severity MAJOR)
  condition: exit_blocked == true
Clear alarm
  condition: exit_blocked == false
```

## Rule 2 — Node 2 sensor fault alarm

```text
Create alarm "Exit Sensor Fault" (severity WARNING)
  condition: sensor_ok == false
Clear when sensor_ok == true
```

## Rule 3 — Fire on Node 1 → evacuation guidance on Node 2 (cross-node)

1. Add a relation from `node-1-fire-detection` to `node-2-exit-monitoring` (type `Evacuates`).
2. In the root rule chain, after **Message type switch → Post telemetry**:

```text
[script filter] msg.fire_detected === true
   → [change originator] source: Related entity, relation type "Evacuates", direction From
   → [transformation script] return {msg: {method: "setEvacuation", params: true}, metadata: metadata, msgType: "RPC_CALL_FROM_SERVER_TO_DEVICE"};
   → [rpc call request]
```

Repeat with `fire_detected === false` → `params: false` to stop guidance after the fire clears.

## Rule 4 — Fire AND exit blocked → escalate (cross-node, multi-source)

```text
IF Node 1 fire_detected == true AND Node 2 exit_blocked == true
THEN create "Evacuation Route Blocked" alarm (CRITICAL)
     and send setLockdown(true) to node-4-command-center
```

Implement with an **originator attributes / latest telemetry** enrichment node on the Node 2 message that fetches `fire_detected` from the related Node 1 device, followed by a script filter `msg.exit_blocked && metadata.fire_detected === 'true'`.

## Rule 5 — Command centre closes the route

When Node 4 `display_state == "LOCKDOWN"` and the operator decides this exit is unsafe, the web app or a dashboard switch sends `setExitClosed(true)` to Node 2. The red LED stays on until `setExitClosed(false)`.

Record the final threshold you chose (after measuring the hallway) and screenshots of each alarm firing as evidence.
