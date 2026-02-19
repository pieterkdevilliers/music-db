<template>
  <NuxtLink :to="`/albums/${album.id}`" class="card">
    <div class="art-wrapper">
      <img v-if="album.art_path" :src="artUrl" :alt="album.title" class="art" />
      <div v-else class="art-placeholder" />
    </div>
    <div class="card-body">
      <h3>{{ album.title }}</h3>
      <p class="artist">{{ album.artist }}</p>
      <div class="meta">
        <span v-if="album.record_label">{{ album.record_label }}</span>
        <span v-if="album.release_year"> · {{ album.release_year }}</span>
      </div>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()

const props = defineProps<{
  album: {
    id: number
    title: string
    artist: string
    record_label?: string | null
    release_year?: number | null
    art_path?: string | null
  }
}>()

const artUrl = computed(() =>
  props.album.art_path
    ? `${config.public.apiBase}/static/${props.album.art_path}`
    : null
)
</script>

<style scoped>
.card {
  display: block;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s;
}
.card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
.art-wrapper {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: #f0f0f0;
}
.art {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.art-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #e8eaf0 0%, #d0d4e8 100%);
}
.card-body {
  padding: 0.75rem 1rem 1rem;
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
