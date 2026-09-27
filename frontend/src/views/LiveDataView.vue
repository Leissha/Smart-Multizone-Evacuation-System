<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import PageTitle from '../components/common/PageTitle.vue'
import SourceBadge from '../components/common/SourceBadge.vue'
import { useSystemData } from '../composables/useSystemData'
const { devices } = useSystemData(); const selected = ref(''); const device = computed(() => devices.value.find((item) => item.id === selected.value) ?? devices.value[0])
watchEffect(() => { if (!selected.value && devices.value.length) selected.value = devices.value[0].id })
</script>
<template><div class="view-stack"><PageTitle eyebrow="Telemetry" title="Live Data" description="Current values use real ThingsBoard telemetry when fresh, otherwise clearly marked simulation."/><section class="raised-card filter-row"><label>Device<select v-model="selected"><option v-for="item in devices" :key="item.id" :value="item.id">{{ item.displayName }}</option></select></label><SourceBadge :source="device.source" /><span>Updated: {{ device.lastUpdate ? new Date(device.lastUpdate).toLocaleString() : 'Simulation baseline' }}</span></section><section class="metric-grid"><article v-for="(value, key) in device.telemetry" :key="key" class="raised-card metric-card"><small>{{ String(key).replaceAll('_', ' ') }}</small><strong>{{ typeof value === 'boolean' ? (value ? 'TRUE' : 'FALSE') : value }}</strong></article></section><section class="raised-card chart-placeholder"><h2>Historical telemetry</h2><p v-if="device.source === 'live'">History is available through the ThingsBoard-backed API. Use Monitor to select a time window.</p><p v-else>Historical simulation is intentionally not fabricated.</p></section></div></template>
