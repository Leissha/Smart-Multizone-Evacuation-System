<script setup lang="ts">
import AppHeader from './components/layout/AppHeader.vue'
import { startSystemPolling } from './composables/useSystemData'

startSystemPolling()
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main class="page-wrap"><RouterView /></main>
  </div>
</template>
