import type {
  AlarmRecord, DeviceCreatePayload, DeviceProvisionResponse,
  NodeContractSummary, TelemetryRecord,
} from '../types/device'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { Accept: 'application/json', ...(options?.body ? { 'Content-Type': 'application/json' } : {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  nodes: () => request<NodeContractSummary[]>('/api/nodes'),
  nodesLatest: () => request<Record<string, TelemetryRecord>>('/api/nodes/telemetry/latest'),
  createDevice: (payload: DeviceCreatePayload) => request<DeviceProvisionResponse>('/api/nodes', { method: 'POST', body: JSON.stringify(payload) }),
  devices: () => request<NodeContractSummary[]>('/api/nodes'),
  nodeHistory: (nodeId: string, startTs: number, endTs: number) => request<Record<string, Array<{ ts: number; value: string | number | boolean }>>>(`/api/nodes/${encodeURIComponent(nodeId)}/telemetry/history?start_ts=${startTs}&end_ts=${endTs}`),
  nodeRpc: (nodeId: string, method: string, params: boolean) => request(`/api/nodes/${encodeURIComponent(nodeId)}/rpc`, { method: 'POST', body: JSON.stringify({ method, params }) }),
  alarms: (nodeId?: string) => request<{ data?: AlarmRecord[] }>(`/api/monitor/alarms${nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : ''}`),
  acknowledgeAlarm: (id: string) => request<void>(`/api/monitor/alarms/${id}/ack`, { method: 'POST' }),
  clearAlarm: (id: string) => request<void>(`/api/monitor/alarms/${id}/clear`, { method: 'POST' }),
  rules: () => request<{ data: unknown[]; management_supported: boolean; message: string }>('/api/automation/rules'),
  events: () => request<{ data: unknown[]; message: string }>('/api/monitor/events'),
}
