<script setup lang="ts">
import { Activity, Bell, Cloud, Map, RadioTower, ShieldCheck, Zap } from '@lucide/vue'
import { useSystemData } from '../composables/useSystemData'
import FloorPlanNodeCard from '../components/overview/FloorPlanNodeCard.vue'
import conceptualDiagram from '../assets/conceptual-diagram.png'

const { devices, activeAlarms, status, buildingState, error } = useSystemData()
</script>
<template>
  <div class="view-stack overview-page">
    <section class="status-hero raised-card">
      <div><p class="eyebrow">Building safety overview</p><h1>Building Status: <span :class="buildingState.toLowerCase()">{{ buildingState }}</span></h1><p>{{ buildingState === 'SAFE' ? 'No active cloud alarms are currently reported.' : 'Review current alarms and affected zones.' }}</p></div>
      <div class="hero-stats"><div><Bell /><span><small>Active alarms</small><strong>{{ activeAlarms.length }}</strong></span></div><div><RadioTower /><span><small>Node sources</small><strong>{{ status.live_nodes }} LIVE / {{ status.simulated_nodes }} SIMULATED</strong></span></div></div>
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
        <div class="zone-card-footer"><p class="caption">Static demonstration route; dynamic route optimisation is not yet implemented.</p><RouterLink class="automation-summary" to="/automation"><Zap :size="17" /><span><b>Automation Status</b><small>Rule design available</small></span><strong>View Rules →</strong></RouterLink></div>
      </article>
      <div class="overview-side">
        <article class="raised-card compact-card"><div class="card-heading"><div><Bell /><h2>Active Alarms</h2></div><RouterLink to="/monitor?tab=alarms">View all →</RouterLink></div><div v-if="!activeAlarms.length" class="empty-state"><ShieldCheck /><b>No active alarms</b><span>ThingsBoard currently reports no active alarm.</span></div><ul v-else class="alarm-list"><li v-for="alarm in activeAlarms.slice(0, 3)" :key="alarm.id?.id"><b>{{ alarm.type }}</b><span>{{ alarm.severity }}</span></li></ul></article>
        <article class="raised-card compact-card"><div class="card-heading"><div><Activity /><h2>Recent Events</h2></div></div><div class="empty-inline">Event persistence is not configured. No production events are fabricated.</div></article>
      </div>
    </section>
    <section class="health-strip raised-card"><h2><Activity /> System Health</h2><div><Cloud /><span><small>ThingsBoard</small><b>{{ status.thingsboard_connected ? 'Connected' : 'Unavailable' }}</b></span></div><div><ShieldCheck /><span><small>FastAPI</small><b>Healthy</b></span></div><div><RadioTower /><span><small>Nodes</small><b>{{ status.live_nodes }} LIVE / {{ status.simulated_nodes }} SIMULATED</b></span></div></section>
  </div>
</template>
