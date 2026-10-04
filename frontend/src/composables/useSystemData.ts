import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../services/api'
import { cloneSimulatedDevices } from '../simulation/simulatedDevices'
import type { AlarmRecord, DeviceViewModel, NodeContractSummary, SystemStatus, TelemetryRecord } from '../types/device'

const freshnessOverrideSeconds = Number(import.meta.env.VITE_LIVE_FRESHNESS_SECONDS ?? 0)
const devices = ref<DeviceViewModel[]>(cloneSimulatedDevices())
const alarms = ref<AlarmRecord[]>([])
const status = ref<SystemStatus>({ api_healthy: true, thingsboard_connected: false, active_alarm_count: 0, live_nodes: 0, simulated_nodes: 4 })
const loading = ref(false)
const error = ref('')
let intervalId: number | undefined
let contracts: NodeContractSummary[] | null = null

function applyContract(device: DeviceViewModel, contract: NodeContractSummary) {
  device.displayName = contract.name
  device.purpose = contract.role
  device.zone = contract.zone
  device.accent = contract.accent
  device.telemetryContract = contract.telemetry_contract
  device.rpcMethods = contract.rpc_methods
}

function applyLiveTelemetry(device: DeviceViewModel, telemetry: TelemetryRecord, newestTs: number) {
  device.source = 'live'
  device.online = true
  device.lastUpdate = newestTs
  device.telemetry = {
    ...device.telemetry,
    ...Object.fromEntries(Object.entries(telemetry).map(([key, sample]) => [key, sample.value])),
  }
}

function refreshNode(device: DeviceViewModel, contract: NodeContractSummary, telemetry: TelemetryRecord): boolean {
  const newestTs = Math.max(0, ...Object.values(telemetry).map((sample) => sample?.ts ?? 0))
  const freshnessSeconds = freshnessOverrideSeconds > 0 ? freshnessOverrideSeconds : contract.freshness_seconds
  const live = newestTs > 0 && Date.now() - newestTs <= freshnessSeconds * 1000
  if (live) applyLiveTelemetry(device, telemetry, newestTs)
  return live
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  const baseline = cloneSimulatedDevices()
  const registryResult = contracts
    ? { status: 'fulfilled' as const, value: contracts }
    : await api.nodes().then(
      (value) => ({ status: 'fulfilled' as const, value }),
      (reason) => ({ status: 'rejected' as const, reason }),
    )
  if (registryResult.status === 'fulfilled') contracts = registryResult.value
  const currentContracts = contracts ?? []
  for (const contract of currentContracts) {
    const device = baseline.find((item) => item.id === contract.device_id)
    if (device) applyContract(device, contract)
  }

  const snapshotResult = await api.nodesLatest().then(
    (value) => ({ status: 'fulfilled' as const, value }),
    (reason) => ({ status: 'rejected' as const, reason }),
  )
  const snapshot = snapshotResult.status === 'fulfilled' ? snapshotResult.value : {}
  const cloudHasTelemetry = Object.values(snapshot).some((telemetry) => Object.keys(telemetry).length > 0)
  const nodeResults = currentContracts.map((contract) => {
    const device = baseline.find((item) => item.id === contract.device_id)
    return device ? refreshNode(device, contract, snapshot[contract.device_id] ?? {}) : false
  })
  const liveNodes = nodeResults.filter(Boolean).length

  devices.value = baseline
  alarms.value = []
  status.value = {
    api_healthy: true,
    thingsboard_connected: snapshotResult.status === 'fulfilled' && cloudHasTelemetry,
    active_alarm_count: alarms.value.filter((alarm) => !alarm.cleared).length,
    live_nodes: liveNodes,
    simulated_nodes: baseline.length - liveNodes,
  }

  error.value = registryResult.status === 'rejected' || snapshotResult.status === 'rejected'
    ? 'Unable to load cloud data'
    : ''
  loading.value = false
}

export function useSystemData() {
  const activeAlarms = computed(() => alarms.value.filter((alarm) => !alarm.cleared))
  const buildingState = computed(() => activeAlarms.value.length ? 'WARNING' : 'SAFE')
  return { devices, alarms, activeAlarms, status, buildingState, loading, error, refresh }
}

export function startSystemPolling() {
  onMounted(() => { refresh(); intervalId = window.setInterval(refresh, 15000) })
  onBeforeUnmount(() => window.clearInterval(intervalId))
}
