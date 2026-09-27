<script setup lang="ts">
defineProps<{ source: 'live' | 'simulated' }>()
</script>
<template><span class="source-badge" :class="source">{{ source.toUpperCase() }}</span></template>
