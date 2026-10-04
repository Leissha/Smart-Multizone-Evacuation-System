<script setup lang="ts">
import { computed, onMounted, ref, watch, watchEffect } from 'vue'
import PageTitle from '../components/common/PageTitle.vue'
import SourceBadge from '../components/common/SourceBadge.vue'
import { useSystemData } from '../composables/useSystemData'
import { api } from '../services/api'

const { devices, alarms, error, refresh } = useSystemData()
const selected = ref('')
const windowHours = ref(1)
const history = ref<Record<string, Array<{ ts: number; value: string | number | boolean }>>>({})

const device = computed(() => devices.value.find((item) => item.id === selected.value) ?? devices.value[0])
const chartSeries = computed(() => Object.entries(history.value).find(([, samples]) => samples.length > 0))
const chartKey = computed(() => chartSeries.value?.[0] ?? '')
const chartValues = computed(() => chartSeries.value?.[1] ?? [])

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

async function act(id: string | undefined, type: 'ack' | 'clear') {
  if (!id) return
  if (type === 'ack') await api.acknowledgeAlarm(id)
  else await api.clearAlarm(id)
  await refresh()
}

watch([selected, windowHours], loadHistory)
onMounted(loadHistory)
</script>

<template>
  <div class="view-stack">
    <PageTitle
      eyebrow="Telemetry & cloud evidence"
      title="Monitor"
      description="Selected-device telemetry beside alarms from the complete building system."
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
        <strong>{{ typeof value === 'boolean' ? (value ? 'YES' : 'NO') : value }}</strong>
      </article>
    </section>

    <p v-if="error" class="notice warning">{{ error }}</p>

    <section class="monitor-split">
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
          <small class="chart-label">{{ chartKey.replaceAll('_', ' ') }}</small>
          <svg viewBox="0 0 600 150" preserveAspectRatio="none">
            <polyline :points="chartValues.map((point, index) => `${index * 600 / (chartValues.length - 1)},${140 - (Number(point.value) || 0)}`).join(' ')" />
          </svg>
        </div>
        <div v-else class="empty-inline">
          {{ device.source === 'live' ? 'No samples returned for this window.' : 'Historical simulation is intentionally not fabricated.' }}
        </div>
      </article>

      <article class="raised-card system-events-card">
        <div class="card-heading">
          <div>
            <p class="eyebrow">Complete building</p>
            <h2>System alarms — all nodes</h2>
          </div>
          <span>{{ alarms.length }} record{{ alarms.length === 1 ? '' : 's' }}</span>
        </div>

        <div v-if="!alarms.length" class="empty-state compact-empty">
          <b>No alarm records returned</b>
          <span>No simulated alarms or events are fabricated.</span>
        </div>
        <div v-else class="system-event-list">
          <div v-for="alarm in alarms" :key="alarm.id?.id" class="system-event-row">
            <div>
              <small>{{ alarm.originatorName ?? 'Unknown node' }}</small>
              <b>{{ alarm.type }}</b>
              <time>{{ new Date(alarm.createdTime ?? alarm.startTs ?? 0).toLocaleString() }}</time>
            </div>
            <div class="event-state">
              <span>{{ alarm.severity }}</span>
              <span>{{ alarm.status }}</span>
            </div>
            <div class="event-actions">
              <button v-if="!alarm.acknowledged" class="text-button" @click="act(alarm.id?.id, 'ack')">Acknowledge</button>
              <button v-if="!alarm.cleared" class="text-button coral" @click="act(alarm.id?.id, 'clear')">Clear</button>
            </div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>
