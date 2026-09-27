# Node 3 rule notes

ThingsBoard Rule Engine logic:

```text
IF sound_level > configured sound_threshold
AND vibration_detected = true
THEN equipment_fault = true
```

Possible actions are creating an Equipment Fault alarm, calling `setBuzzer(true)`, and optionally calling `setRelay(false)`. The threshold must be calibrated from real room readings. `equipment_fault` must be labelled as derived state, not raw telemetry.

