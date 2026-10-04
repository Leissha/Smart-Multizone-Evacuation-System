<script setup lang="ts">
import { Activity, Building2, ChartNoAxesCombined, Cloud, LayoutDashboard, ShieldCheck, SlidersHorizontal } from '@lucide/vue'
import { useSystemData } from '../../composables/useSystemData'

const { status } = useSystemData()
const links = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/nodes', label: 'Nodes', icon: Building2 },
  { to: '/monitor', label: 'Monitor', icon: ChartNoAxesCombined },
  { to: '/control', label: 'Control', icon: SlidersHorizontal },
  { to: '/automation', label: 'Automation', icon: Activity },
]
</script>

<template>
  <header class="topbar page-wrap">
    <RouterLink to="/" class="brand">
      <span class="brand-mark"><ShieldCheck :size="26" /></span>
      <span><strong>Smart Multi-Zone</strong><small>Evacuation & Safety System</small></span>
    </RouterLink>
    <nav class="nav-pill" aria-label="Primary navigation">
      <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link">
        <component :is="link.icon" :size="16" /><span>{{ link.label }}</span>
      </RouterLink>
    </nav>
    <div class="top-actions">
      <div class="cloud-state"><Cloud :size="19" /><span><small>ThingsBoard</small><strong>{{ status.thingsboard_connected ? 'Connected' : 'Unavailable' }}</strong></span><i :class="status.thingsboard_connected ? 'ok' : 'muted'" /></div>
      <span class="avatar">A</span>
    </div>
  </header>
</template>
