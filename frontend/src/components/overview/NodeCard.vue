<script setup lang="ts">
import { Activity, Flame, RadioTower, Settings2 } from '@lucide/vue'
import type { DeviceViewModel } from '../../types/device'
import SourceBadge from '../common/SourceBadge.vue'

defineProps<{ device: DeviceViewModel }>()
const icons = { coral: Flame, sage: RadioTower, gold: Settings2, blue: Activity }
const labels: Record<string, string> = {
  temperature: 'Temperature', smoke_level: 'Smoke level', fire_detected: 'Fire detected',
  distance_cm: 'Distance', exit_blocked: 'Exit blocked', threshold_cm: 'Block threshold',
  evacuation_mode: 'Evacuation', exit_closed: 'Exit closed', sensor_ok: 'Sensor OK', sound_level: 'Sound level',
  vibration_detected: 'Vibration', relay_state: 'Relay', buzzer_state: 'Buzzer',
  manual_emergency: 'Manual emergency', display_state: 'Display state', master_buzzer: 'Master buzzer',
}
function displayValue(key: string, value: string | number | boolean) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (key === 'temperature') return `${value} °C`
  if (key === 'distance_cm' || key === 'threshold_cm') return `${value} cm`
  return value
}
</script>
<template>
  <article class="node-card" :class="`accent-${device.accent}`">
    <div class="node-head"><span class="node-icon"><component :is="icons[device.accent]" :size="27" /></span><div><h3>{{ device.displayName }}</h3><p>{{ device.purpose }}</p></div></div>
    <SourceBadge :source="device.source" />
    <dl><template v-for="(value, key) in device.telemetry" :key="key"><div v-if="!String(key).includes('fault')"><dt>{{ labels[String(key)] ?? key }}</dt><dd>{{ displayValue(String(key), value) }}</dd></div></template></dl>
  </article>
</template>
