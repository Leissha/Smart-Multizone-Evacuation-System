import type { DeviceViewModel } from '../types/device'

export const simulatedDevices: DeviceViewModel[] = [
  { id: 'node-1-fire-detection', displayName: 'Node 1 – Fire Detection', shortName: 'Node 1', purpose: 'Kitchen / lab fire zone', zone: 'Zone 1', source: 'simulated', online: false, lastUpdate: null, accent: 'coral', telemetryContract: [], rpcMethods: [], telemetry: { temperature: 24.2, smoke_level: 'Low', fire_detected: false } },
  { id: 'node-2-exit-monitoring', displayName: 'Node 2 – Exit Monitoring', shortName: 'Node 2', purpose: 'Hallway / exit zone', zone: 'Zone 2', source: 'simulated', online: false, lastUpdate: null, accent: 'sage', telemetryContract: [], rpcMethods: [], telemetry: { distance_cm: 120, exit_blocked: false } },
  { id: 'node-3-equipment-room', displayName: 'Node 3 – Equipment Room', shortName: 'Node 3', purpose: 'Server / equipment monitoring', zone: 'Zone 3', source: 'simulated', online: false, lastUpdate: null, accent: 'gold', telemetryContract: [], rpcMethods: ['setRelay', 'setBuzzer', 'setEquipmentAlarm'], telemetry: { sound_level: 116, vibration_detected: false, relay_state: true, buzzer_state: false, equipment_fault: false } },
  { id: 'node-4-command-center', displayName: 'Node 4 – Command Center', shortName: 'Node 4', purpose: 'Central command terminal', zone: 'Zone 4', source: 'simulated', online: false, lastUpdate: null, accent: 'blue', telemetryContract: [], rpcMethods: [], telemetry: { manual_emergency: false, display_state: 'Standby', master_buzzer: false } },
]

export function cloneSimulatedDevices(): DeviceViewModel[] {
  return simulatedDevices.map((device) => ({ ...device, telemetry: { ...device.telemetry } }))
}
