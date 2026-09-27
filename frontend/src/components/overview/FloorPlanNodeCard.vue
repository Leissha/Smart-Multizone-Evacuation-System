<script setup lang="ts">
import { computed } from 'vue'
import type { DeviceViewModel } from '../../types/device'

const props = defineProps<{ device: DeviceViewModel }>()
const labels: Record<string, string> = {
  temperature: 'Temperature', smoke_level: 'Smoke level', fire_detected: 'Fire detected',
  distance_cm: 'Distance', exit_blocked: 'Exit blocked', sound_level: 'Sound',
  vibration_detected: 'Vibration', relay_state: 'Relay', buzzer_state: 'Buzzer',
  manual_emergency: 'Emergency', display_state: 'Display', master_buzzer: 'Master buzzer',
}
const metrics = computed(() => Object.entries(props.device.telemetry)
  .filter(([key]) => !key.includes('fault'))
  .slice(0, 4))

function displayValue(key: string, value: string | number | boolean) {
  if (typeof value === 'boolean') {
    if (key === 'relay_state' || key === 'buzzer_state' || key === 'master_buzzer') return value ? 'On' : 'Off'
    return value ? 'Yes' : 'No'
  }
  if (key === 'temperature') return `${value} °C`
  if (key === 'distance_cm') return `${value} cm`
  return value
}
</script>

<template>
  <article class="plan-node-card" :class="`accent-${device.accent}`">
    <header><b>{{ device.shortName }}</b><span class="plan-source" :class="device.source">{{ device.source.toUpperCase() }}</span></header>
    <dl><div v-for="([key, value]) in metrics" :key="key"><dt>{{ labels[key] ?? key }}</dt><dd>{{ displayValue(key, value) }}</dd></div></dl>
  </article>
</template>
