export type DataSource = 'live' | 'simulated'

export interface TelemetrySample<T> {
  value: T
  ts: number
}

export type TelemetryValue = string | number | boolean
export type TelemetryRecord = Record<string, TelemetrySample<TelemetryValue>>

export interface TelemetryFieldContract {
  key: string
  type: 'number' | 'boolean' | 'string'
  unit: string | null
}

export interface NodeContractSummary {
  device_id: string
  name: string
  role: string
  zone: string
  telemetry_contract: TelemetryFieldContract[]
  rpc_methods: string[]
  freshness_seconds: number
  accent: DeviceViewModel['accent']
}

export interface DeviceStatus {
  device_id: string
  cloud_configured: boolean
  active: boolean
  last_update_ms: number | null
}

export interface DeviceViewModel {
  id: string
  displayName: string
  shortName: string
  purpose: string
  zone: string
  source: DataSource
  online: boolean
  lastUpdate: number | null
  telemetry: Record<string, string | number | boolean>
  telemetryContract: TelemetryFieldContract[]
  rpcMethods: string[]
  accent: 'coral' | 'sage' | 'gold' | 'blue'
}

export interface SystemStatus {
  api_healthy: boolean
  thingsboard_connected: boolean
  active_alarm_count: number
  live_nodes: number
  simulated_nodes: number
}

export interface AlarmRecord {
  id?: { id?: string }
  type?: string
  severity?: string
  status?: string
  createdTime?: number
  startTs?: number
  cleared?: boolean
  acknowledged?: boolean
  details?: Record<string, unknown>
}

export interface DeviceCreatePayload {
  display_name: string
  device_name: string
  zone: string
  purpose: string
  telemetry_contract: string[]
  rpc_methods: string[]
  notes: string
}

export interface DeviceProvisionResponse {
  device_name: string
  device_uuid: string
  edge_config_template: string
  credential_message: string
}
