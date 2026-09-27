<script setup lang="ts">
import { Check, Copy, Plus, X } from '@lucide/vue'
import { reactive, ref } from 'vue'
import PageTitle from '../components/common/PageTitle.vue'
import SourceBadge from '../components/common/SourceBadge.vue'
import { useSystemData } from '../composables/useSystemData'
import { api } from '../services/api'
import type { DeviceCreatePayload, DeviceProvisionResponse } from '../types/device'

const { devices } = useSystemData()
const showForm = ref(false), saving = ref(false), message = ref(''), copied = ref(false)
const provisioned = ref<DeviceProvisionResponse | null>(null)
const form = reactive<DeviceCreatePayload>({ display_name: '', device_name: '', zone: '', purpose: '', telemetry_contract: [], rpc_methods: [], notes: '' })
const telemetryText = ref(''), rpcText = ref('')
async function submit() {
  saving.value = true; message.value = ''; provisioned.value = null
  try {
    form.telemetry_contract = telemetryText.value.split(',').map((v) => v.trim()).filter(Boolean)
    form.rpc_methods = rpcText.value.split(',').map((v) => v.trim()).filter(Boolean)
    provisioned.value = await api.createDevice(form)
  } catch (reason) { message.value = reason instanceof Error ? reason.message : 'Device creation failed' }
  finally { saving.value = false }
}
async function copyConfig() { if (provisioned.value) { await navigator.clipboard.writeText(provisioned.value.edge_config_template); copied.value = true } }
</script>
<template><div class="view-stack"><PageTitle eyebrow="Device management" title="Project Nodes" description="Four planned safety nodes, with source and connectivity kept separate."><button class="action-button" @click="showForm = true"><Plus /> Add Device</button></PageTitle>
<section class="raised-card table-card"><div class="device-table header"><span>Device</span><span>Purpose / Zone</span><span>Source</span><span>Connectivity</span><span>Last telemetry</span></div><div v-for="device in devices" :key="device.id" class="device-table"><span><b>{{ device.displayName }}</b><small>{{ device.id }}</small></span><span>{{ device.purpose }}<small>{{ device.zone }}</small></span><SourceBadge :source="device.source" /><span class="connectivity"><i :class="device.online ? 'ok' : 'muted'" />{{ device.online ? 'Online' : 'Not connected' }}</span><span>{{ device.lastUpdate ? new Date(device.lastUpdate).toLocaleString() : 'No live sample' }}</span></div></section>
<div v-if="showForm" class="modal-backdrop"><section class="modal raised-card"><button class="modal-close" @click="showForm = false"><X /></button><p class="eyebrow">ThingsBoard provisioning</p><h2>Add Device</h2><form @submit.prevent="submit" class="form-grid"><label>Display name<input v-model="form.display_name" required /></label><label>Stable device name<input v-model="form.device_name" placeholder="node-2-exit-monitoring" required /></label><label>Zone<input v-model="form.zone" required /></label><label>Purpose<input v-model="form.purpose" required /></label><label class="wide">Telemetry fields<input v-model="telemetryText" placeholder="distance_cm, exit_blocked" /></label><label class="wide">RPC methods<input v-model="rpcText" placeholder="setIndicator" /></label><label class="wide">Notes<textarea v-model="form.notes" /></label><p v-if="message" class="notice warning wide">{{ message }}</p><button class="action-button wide" :disabled="saving">{{ saving ? 'Creating…' : 'Create in ThingsBoard' }}</button></form><div v-if="provisioned" class="provision-result"><p><Check /> Device created: <b>{{ provisioned.device_name }}</b></p><pre>{{ provisioned.edge_config_template }}</pre><button class="soft-button" @click="copyConfig"><Copy /> {{ copied ? 'Copied' : 'Copy configuration template' }}</button><small>{{ provisioned.credential_message }}</small></div></section></div></div></template>
