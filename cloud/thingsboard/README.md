# ThingsBoard setup for Node 3

1. Create a ThingsBoard device named `node-3-equipment-room`.
2. Copy its access token into the edge `.env` as `THINGSBOARD_ACCESS_TOKEN`.
3. Generate a programmatic API key from **Account > Security > API keys**, then set `THINGSBOARD_API_KEY` in the root `.env`. Do not commit that file.
4. Run the edge and confirm **Latest telemetry** receives the four raw Node 3 keys.
5. Add timeseries widgets for sound and vibration and state cards for relay/buzzer.
6. Add RPC controls for `setRelay`, `setBuzzer`, and `setEquipmentAlarm`, each with boolean parameters. `setEquipmentAlarm` controls the relay and buzzer together.
7. Verify a successful response occurs only after the corresponding physical change and ACK.
8. Create the future equipment alarm described in `rule-notes.md` only after choosing and validating a real threshold.

MQTT device topics:

- Telemetry: `v1/devices/me/telemetry`
- RPC request: `v1/devices/me/rpc/request/+`
- RPC response: `v1/devices/me/rpc/response/{request_id}`

FastAPI resolves the device UUID from its stable name. The Vue application polls FastAPI every five seconds. A ThingsBoard WebSocket adapter is optional and is not required for the Node 3 milestone.
