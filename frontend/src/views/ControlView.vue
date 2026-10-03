<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import PageTitle from '../components/common/PageTitle.vue'
import SourceBadge from '../components/common/SourceBadge.vue'
import { useSystemData } from '../composables/useSystemData'
import { api } from '../services/api'

const { devices, refresh } = useSystemData()
const selectedId = ref('')
const busy = ref('')
const message = ref('')
const device = computed(() => devices.value.find((item) => item.id === selectedId.value) ?? devices.value[0])
watchEffect(() => {
  if (!selectedId.value && devices.value.length) {
    selectedId.value = devices.value.find((item) => item.rpcMethods.length)?.id ?? devices.value[0].id
  }
})

const methodLabels: Record<string, string> = {
  setRelay: 'Relay',
  setBuzzer: 'Buzzer',
  setEquipmentAlarm: 'Equipment alarm',
}
const methodStateKeys: Record<string, string> = {
  setRelay: 'relay_state',
  setBuzzer: 'buzzer_state',
}

function currentState(method: string) {
  if (method === 'setEquipmentAlarm') {
    return device.value.telemetry.relay_state && device.value.telemetry.buzzer_state ? 'ON' : 'OFF'
  }
  const key = methodStateKeys[method]
  if (!key) return '—'
  return device.value.telemetry[key] ? 'ON' : 'OFF'
}

async function control(method: string, enabled: boolean) {
  busy.value = method
  message.value = ''
  try {
    await api.nodeRpc(device.value.id, method, enabled)
    message.value = `${methodLabels[method] ?? method} command acknowledged by ${device.value.shortName}`
    await refresh()
  } catch (reason) {
    message.value = reason instanceof Error ? reason.message : 'RPC failed'
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <div class="view-stack">
    <PageTitle eyebrow="Manual action" title="Control" description="Available controls come from each node contract and use ThingsBoard RPC." />
    <section class="raised-card monitor-toolbar">
      <label>Node
        <select v-model="selectedId">
          <option v-for="item in devices" :key="item.id" :value="item.id">{{ item.displayName }}</option>
        </select>
      </label>
      <SourceBadge :source="device.source" />
    </section>
    <section class="control-grid">
      <article class="raised-card control-panel">
        <div class="control-title">
          <div><p class="eyebrow">{{ device.zone }}</p><h2>{{ device.displayName }}</h2></div>
          <SourceBadge :source="device.source" />
        </div>
        <div v-if="!device.rpcMethods.length" class="empty-inline">No RPC methods are registered for this node.</div>
        <div v-for="method in device.rpcMethods" :key="method" class="control-item">
          <div><b>{{ methodLabels[method] ?? method }}</b><p>Current state: <strong>{{ currentState(method) }}</strong></p></div>
          <div>
            <button class="action-button" :disabled="busy !== ''" @click="control(method, true)">Turn ON</button>
            <button class="soft-button" :disabled="busy !== ''" @click="control(method, false)">Turn OFF</button>
          </div>
        </div>
        <p v-if="message" class="notice">{{ message }}</p>
      </article>
      <article class="raised-card">
        <p class="eyebrow">Contract-driven controls</p>
        <h2>Registered nodes</h2>
        <div class="disabled-control" v-for="item in devices" :key="item.id">
          <span><b>{{ item.displayName }}</b><small>{{ item.rpcMethods.length ? item.rpcMethods.join(', ') : 'No confirmed RPC contract' }}</small></span>
          <button disabled>{{ item.source.toUpperCase() }}</button>
        </div>
      </article>
    </section>
  </div>
</template>
