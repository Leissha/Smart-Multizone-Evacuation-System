## Rule chains

The project uses two ThingsBoard rule-chain configurations:

[Independent Rule Chain](rule-chains/independent_rule_chain.json)
  - Used during Phase 1 to verify each node independently.
  - Validates telemetry conditions and tests the full telemetry → rule → RPC → actuator → ACK flow.

[Integration Rule Chain](rule-chains/integration_rule_chain.json)
  - Used during Phase 2 for final multi-node coordination.
  - Stores selected node states on the Smart Evacuation Building asset and combines them for cross-node decisions such as evacuation, route closure, equipment isolation and command-centre lockdown.

# Node 3 rule notes

ThingsBoard Rule Engine logic:

```text
IF sound_level > configured sound_threshold
AND vibration_detected = true
THEN equipment_fault = true
```

Possible actions are creating an Equipment Fault alarm, calling `setBuzzer(true)`, and optionally calling `setRelay(false)`. The threshold must be calibrated from real room readings. `equipment_fault` must be labelled as derived state, not raw telemetry.

