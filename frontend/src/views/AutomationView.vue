<script setup lang="ts">
import { ArrowDown, ArrowRight, Building2, Flame, RadioTower, Route, ShieldAlert, Volume2 } from '@lucide/vue'
import PageTitle from '../components/common/PageTitle.vue'

const inputs = [
  { node: 'Node 1', label: 'Fire detection', detail: 'fire_detected', icon: Flame, tone: 'coral' },
  { node: 'Node 2', label: 'Exit monitoring', detail: 'exit_blocked', icon: Route, tone: 'gold' },
  { node: 'Node 3', label: 'Equipment room', detail: 'sound + vibration', icon: Volume2, tone: 'blue' },
]

const responses = [
  { node: 'Node 2', label: 'Evacuation guidance', detail: 'Evacuate or close route', icon: Route, tone: 'gold' },
  { node: 'Node 4', label: 'Emergency alert', detail: 'LCD status + master warning', icon: Building2, tone: 'sage' },
  { node: 'Node 3', label: 'Equipment isolation', detail: 'Relay OFF · manual reset', icon: ShieldAlert, tone: 'blue' },
]

const rules = [
  { tag: 'FIRE', condition: 'Node 1 fire active', action: 'Node 2 evacuation + Node 4 emergency alert' },
  { tag: 'BLOCKED EXIT', condition: 'Fire active + Node 2 exit blocked', action: 'Close unsafe route + critical emergency alert' },
  { tag: 'EQUIPMENT', condition: 'Fire active + sound > 100 + vibration', action: 'Node 3 equipment power isolated' },
]
</script>

<template>
  <div class="view-stack">
    <PageTitle eyebrow="Cloud rule processing" title="Automation" description="Deployed ThingsBoard flow from MQTT telemetry to coordinated device response." />

    <section class="raised-card automation-map">
      <div class="map-column">
        <p class="map-label">Telemetry inputs</p>
        <article v-for="item in inputs" :key="item.node" class="flow-node" :class="`flow-node--${item.tone}`">
          <span><component :is="item.icon" :size="20" /></span>
          <div><b>{{ item.node }} · {{ item.label }}</b><small>{{ item.detail }}</small></div>
        </article>
      </div>

      <div class="map-connector"><ArrowRight /><ArrowDown /></div>

      <div class="flow-hub">
        <span><RadioTower :size="28" /></span>
        <small>THINGSBOARD</small>
        <h2>Shared Building State</h2>
        <p>Latest cross-node telemetry</p>
        <strong>Evaluate safety rules</strong>
      </div>

      <div class="map-connector"><ArrowRight /><ArrowDown /></div>

      <div class="map-column">
        <p class="map-label">Coordinated responses</p>
        <article v-for="item in responses" :key="item.label" class="flow-node" :class="`flow-node--${item.tone}`">
          <span><component :is="item.icon" :size="20" /></span>
          <div><b>{{ item.node }} · {{ item.label }}</b><small>{{ item.detail }}</small></div>
        </article>
      </div>
    </section>

    <section class="rule-strip">
      <article v-for="rule in rules" :key="rule.tag" class="raised-card compact-rule">
        <span>{{ rule.tag }}</span>
        <div><small>WHEN</small><b>{{ rule.condition }}</b></div>
        <ArrowRight />
        <div><small>THEN</small><b>{{ rule.action }}</b></div>
      </article>
    </section>

    <p class="safety-latch"><ShieldAlert :size="17" /><b>Safety latch:</b> equipment restoration requires a manual operator reset.</p>
  </div>
</template>
