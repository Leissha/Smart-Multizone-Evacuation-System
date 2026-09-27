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

async function refreshNode(device: DeviceViewModel, contract: NodeContractSummary): Promise<boolean> {
  const [nodeStatus, telemetry] = await Promise.all([
    api.nodeStatus(contract.device_id),
    api.nodeLatest(contract.device_id),
  ])
  const newestTs = Math.max(0, ...Object.values(telemetry).map((sample) => sample?.ts ?? 0))
  const freshnessSeconds = freshnessOverrideSeconds > 0 ? freshnessOverrideSeconds : contract.freshness_seconds
  const live = nodeStatus.active && newestTs > 0 && Date.now() - newestTs <= freshnessSeconds * 1000
  if (live) applyLiveTelemetry(device, telemetry, newestTs)
  return live
}

async function refresh() {
  loading.value = true
  const baseline = cloneSimulatedDevices()
  const [registryResult, systemResult, alarmResult] = await Promise.allSettled([
    api.nodes(), api.systemStatus(), api.alarms(),
  ])

  const contracts = registryResult.status === 'fulfilled' ? registryResult.value : []
  for (const contract of contracts) {
    const device = baseline.find((item) => item.id === contract.device_id)
    if (device) applyContract(device, contract)
  }

  const nodeResults = await Promise.allSettled(contracts.map(async (contract) => {
    const device = baseline.find((item) => item.id === contract.device_id)
    return device ? refreshNode(device, contract) : false
  }))
  const liveNodes = nodeResults.filter((result) => result.status === 'fulfilled' && result.value).length

  devices.value = baseline
  alarms.value = alarmResult.status === 'fulfilled' ? alarmResult.value.data ?? [] : []
  const cloudStatus = systemResult.status === 'fulfilled' ? systemResult.value : null
  status.value = {
    api_healthy: true,
    thingsboard_connected: cloudStatus?.thingsboard_connected ?? liveNodes > 0,
    active_alarm_count: alarms.value.filter((alarm) => !alarm.cleared).length,
    live_nodes: liveNodes,
    simulated_nodes: baseline.length - liveNodes,
  }

  const topLevelFailures = [registryResult, systemResult, alarmResult].filter((result) => result.status === 'rejected')
  error.value = topLevelFailures.length === 3 ? 'Unable to load cloud data' : ''
  loading.value = false
}

export function useSystemData() {
  const activeAlarms = computed(() => alarms.value.filter((alarm) => !alarm.cleared))
  const buildingState = computed(() => activeAlarms.value.length ? 'WARNING' : 'SAFE')
  return { devices, alarms, activeAlarms, status, buildingState, loading, error, refresh }
}

export function startSystemPolling() {
  onMounted(() => { refresh(); intervalId = window.setInterval(refresh, 5000) })
  onBeforeUnmount(() => window.clearInterval(intervalId))
}
