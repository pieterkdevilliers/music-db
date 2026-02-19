<template>
  <div />
</template>

<script setup lang="ts">
definePageMeta({ middleware: [] })

const token = import.meta.client ? localStorage.getItem('auth_token') : null
await navigateTo(token ? '/collections' : '/login')
</script>
