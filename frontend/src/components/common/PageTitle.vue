<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; description: string }>()
</script>
<template><div class="page-title"><div><p class="eyebrow">{{ eyebrow }}</p><h1>{{ title }}</h1><p>{{ description }}</p></div><slot /></div></template>
