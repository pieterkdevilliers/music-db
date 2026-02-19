<template>
  <NuxtLink :to="`/albums/${album.id}`" class="card">
    <h3>{{ album.title }}</h3>
    <p class="artist">{{ album.artist }}</p>
    <div class="meta">
      <span v-if="album.record_label">{{ album.record_label }}</span>
      <span v-if="album.release_year"> · {{ album.release_year }}</span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
defineProps<{
  album: {
    id: number
    title: string
    artist: string
    record_label?: string | null
    release_year?: number | null
  }
}>()
</script>

<style scoped>
.card {
  display: block;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s;
}
.card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
h3 {
  margin: 0 0 0.25rem;
  font-size: 0.95rem;
  font-weight: 600;
}
.artist {
  color: #444;
  font-size: 0.875rem;
  margin: 0 0 0.4rem;
}
.meta {
  font-size: 0.75rem;
  color: #999;
}
</style>
