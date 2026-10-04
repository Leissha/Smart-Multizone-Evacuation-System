<script setup lang="ts">
import { computed, ref, watch, watchEffect } from 'vue'
import PageTitle from '../components/common/PageTitle.vue'
import SourceBadge from '../components/common/SourceBadge.vue'
import { useSystemData } from '../composables/useSystemData'
import { api } from '../services/api'

const { devices, error } = useSystemData()
const selected = ref('')
const windowHours = ref(1)
const history = ref<Record<string, Array<{ ts: number; value: string | number | boolean }>>>({})

const device = computed(() => devices.value.find((item) => item.id === selected.value) ?? devices.value[0])
const chartSeries = computed(() => Object.entries(history.value)
  .map(([key, samples]) => [key, samples
    .filter((point) => Number.isFinite(Number(point.value)))
    .sort((left, right) => left.ts - right.ts)] as const)
  .find(([, samples]) => samples.length > 1))
const chartKey = computed(() => chartSeries.value?.[0] ?? '')
const chartValues = computed(() => chartSeries.value?.[1] ?? [])
const fallbackUnits: Record<string, string> = { sound_level: 'ADC', temperature: '°C', distance_cm: 'cm', threshold_cm: 'cm' }
const chartUnit = computed(() => device.value.telemetryContract.find((field) => field.key === chartKey.value)?.unit
  ?? fallbackUnits[chartKey.value]
  ?? '')
const numericValues = computed(() => chartValues.value.map((point) => Number(point.value)))
const analysisThreshold = computed(() => {
  if (chartKey.value === 'sound_level') return 100
  if (chartKey.value === 'distance_cm') {
    const threshold = Number(device.value.telemetry.threshold_cm)
    return Number.isFinite(threshold) ? threshold : null
  }
  return null
})
const analysisStats = computed(() => {
  const values = numericValues.value
  if (!values.length) return null
  const latestValue = Number(device.value.telemetry[chartKey.value])
  return {
    current: Number.isFinite(latestValue) ? latestValue : values.at(-1) ?? 0,
    average: values.reduce((total, value) => total + value, 0) / values.length,
    maximum: Math.max(...values),
  }
})
const chartScale = computed(() => {
  const values = [...numericValues.value]
  if (analysisThreshold.value !== null) values.push(analysisThreshold.value)
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  return { minimum, maximum, range: maximum - minimum || 1 }
})
const chartPoints = computed(() => {
  const values = numericValues.value
  if (values.length < 2) return ''
  const { minimum, range } = chartScale.value
  return values.map((value, index) => `${48 + index * 547 / (values.length - 1)},${140 - ((value - minimum) / range) * 130}`).join(' ')
})
const thresholdY = computed(() => {
  if (analysisThreshold.value === null || !numericValues.value.length) return null
  const { minimum, range } = chartScale.value
  return 140 - ((analysisThreshold.value - minimum) / range) * 130
})
const axisTicks = computed(() => {
  if (!numericValues.value.length) return []
  const { minimum, maximum, range } = chartScale.value
  return [maximum, minimum + range / 2, minimum].map((value) => ({
    value,
    y: 140 - ((value - minimum) / range) * 130,
  }))
})
const thresholdLabel = computed(() => chartKey.value === 'distance_cm'
  ? `< ${analysisThreshold.value}`
  : `> ${analysisThreshold.value}`)

function formatAnalysisValue(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function telemetryUnit(key: string) {
  return device.value.telemetryContract.find((field) => field.key === key)?.unit ?? fallbackUnits[key] ?? ''
}

function displayTelemetryValue(key: string, value: string | number | boolean) {
  if (typeof value === 'boolean') return value ? 'YES' : 'NO'
  const unit = telemetryUnit(key)
  return unit ? `${value} ${unit}` : value
}

watchEffect(() => {
  if (!selected.value && devices.value.length) selected.value = devices.value[0].id
})

async function loadHistory() {
  history.value = {}
  if (device.value.source !== 'live') return
  const end = Date.now()
  history.value = await api
    .nodeHistory(device.value.id, end - windowHours.value * 3_600_000, end)
    .catch(() => ({}))
}

watch([selected, windowHours, () => device.value.source], loadHistory, { immediate: true })
</script>

<template>
  <div class="view-stack monitor-page">
    <PageTitle
      eyebrow="Telemetry & cloud evidence"
      title="Monitor"
      description="Live values and responsive historical telemetry for the selected device."
    />

    <section class="raised-card monitor-toolbar">
      <label>
        Device
        <select v-model="selected">
          <option v-for="item in devices" :key="item.id" :value="item.id">{{ item.displayName }}</option>
        </select>
      </label>
      <SourceBadge :source="device.source" />
      <span>Updated: {{ device.lastUpdate ? new Date(device.lastUpdate).toLocaleString() : 'Simulation baseline' }}</span>
      <div class="time-window">
        <button v-for="hours in [1, 6, 24, 168]" :key="hours" :class="{ active: windowHours === hours }" @click="windowHours = hours">
          {{ hours === 168 ? '7d' : `${hours}h` }}
        </button>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="(value, key) in device.telemetry" :key="key" class="raised-card metric-card">
        <small>{{ String(key).replaceAll('_', ' ') }}</small>
        <strong>{{ displayTelemetryValue(String(key), value) }}</strong>
      </article>
    </section>

    <p v-if="error" class="notice warning">{{ error }}</p>

    <section>
      <article class="raised-card telemetry-chart">
        <div class="card-heading">
          <div>
            <p class="eyebrow">Selected device</p>
            <h2>Historical telemetry</h2>
            <small>{{ device.displayName }}</small>
          </div>
          <span>ThingsBoard · {{ windowHours === 168 ? '7d' : `${windowHours}h` }}</span>
        </div>
        <div v-if="chartValues.length > 1" class="chart-body">
          <small class="chart-label">{{ chartKey.replaceAll('_', ' ') }}<b v-if="chartUnit"> ({{ chartUnit }})</b></small>
          <div v-if="analysisStats" class="analysis-summary">
            <span><small>Current</small><strong>{{ formatAnalysisValue(analysisStats.current) }}<em v-if="chartUnit"> {{ chartUnit }}</em></strong></span>
            <span><small>Average</small><strong>{{ formatAnalysisValue(analysisStats.average) }}<em v-if="chartUnit"> {{ chartUnit }}</em></strong></span>
            <span><small>Maximum</small><strong>{{ formatAnalysisValue(analysisStats.maximum) }}<em v-if="chartUnit"> {{ chartUnit }}</em></strong></span>
            <span><small>Threshold</small><strong>{{ analysisThreshold === null ? 'Not configured' : thresholdLabel }}<em v-if="analysisThreshold !== null && chartUnit"> {{ chartUnit }}</em></strong></span>
          </div>
          <svg viewBox="0 0 600 150" preserveAspectRatio="none">
            <g class="chart-axis">
              <template v-for="tick in axisTicks" :key="tick.y">
                <line x1="48" :y1="tick.y" x2="600" :y2="tick.y" />
                <text x="42" :y="tick.y + 3">{{ formatAnalysisValue(tick.value) }}</text>
              </template>
              <text class="axis-unit" x="8" y="76" transform="rotate(-90 8 76)">{{ chartUnit }}</text>
            </g>
            <line v-if="thresholdY !== null" class="threshold-line" x1="48" :y1="thresholdY" x2="600" :y2="thresholdY" />
            <polyline :points="chartPoints" />
          </svg>
        </div>
        <div v-else class="empty-inline">
          {{ device.source === 'live' ? 'No samples returned for this window.' : 'Historical simulation is intentionally not fabricated.' }}
        </div>
      </article>

    </section>
  </div>
</template>
