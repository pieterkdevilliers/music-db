<template>
  <div>
    <NuxtRouteAnnouncer />
    <AppHeader v-if="showHeader" />
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const PUBLIC_ROUTES = ['/login', '/register']
const showHeader = computed(() => !PUBLIC_ROUTES.includes(route.path))
</script>

<style>
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; color: #222; }
a { color: inherit; }
</style>
