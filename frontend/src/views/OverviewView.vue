<script setup lang="ts">
import { Cloud, Map, RadioTower, Zap } from '@lucide/vue'
import { useSystemData } from '../composables/useSystemData'
import FloorPlanNodeCard from '../components/overview/FloorPlanNodeCard.vue'
import conceptualDiagram from '../assets/conceptual-diagram.png'

const { devices, status, error } = useSystemData()
</script>
<template>
  <div class="view-stack overview-page">
    <section class="status-hero raised-card">
      <div><p class="eyebrow">Building telemetry overview</p><h1>System Status: <span :class="status.thingsboard_connected ? 'safe' : 'warning'">{{ status.thingsboard_connected ? 'CONNECTED' : 'OFFLINE' }}</span></h1><p>Live and simulated node telemetry in one operational view.</p></div>
      <div class="hero-stats"><div><Cloud /><span><small>ThingsBoard</small><strong>{{ status.thingsboard_connected ? 'CONNECTED' : 'UNAVAILABLE' }}</strong></span></div><div><RadioTower /><span><small>Node sources</small><strong>{{ status.live_nodes }} LIVE / {{ status.simulated_nodes }} SIMULATED</strong></span></div></div>
    </section>
    <p v-if="error" class="notice warning">Cloud data unavailable: {{ error }}. Simulation fallback is active.</p>
    <section class="overview-grid">
      <article class="raised-card zone-card">
        <div class="card-heading"><div><Map /><h2>Building / Zone Overview</h2></div><span>Conceptual floor plan</span></div>
        <figure class="floor-map floor-plan-stage">
          <img class="floor-plan-image" :src="conceptualDiagram" alt="Conceptual four-zone building plan with static evacuation routes and exits" />
          <FloorPlanNodeCard v-for="(device, index) in devices" :key="device.id" :device="device" class="node-overlay" :class="[`node-overlay--node${index + 1}`, { 'node-overlay--node3': index === 2 }]" />
        </figure>
        <div class="floor-plan-node-grid"><FloorPlanNodeCard v-for="device in devices" :key="`mobile-${device.id}`" :device="device" /></div>
        <div class="zone-card-footer"><RouterLink class="automation-summary" to="/automation"><Zap :size="17" /><span><b>Automation Status</b><small>3 deployed safety flows</small></span><strong>View Rules →</strong></RouterLink></div>
      </article>
    </section>
  </div>
</template>
