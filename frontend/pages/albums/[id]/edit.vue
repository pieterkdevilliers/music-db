<template>
  <main class="page">
    <div class="page-header">
      <h1>Edit Album</h1>
      <NuxtLink :to="`/albums/${id}`" class="back">← Cancel</NuxtLink>
    </div>
    <AlbumForm
      v-if="initial"
      :initial="initial"
      submit-label="Save Changes"
      :hide-collection-picker="true"
      @submit="saveAlbum"
    />
    <div v-else class="loading">Loading…</div>
    <p v-if="error" class="error">{{ error }}</p>
  </main>
</template>

<script setup lang="ts">
import type { AlbumCreate } from '~/stores/albums'

const route = useRoute()
const albumsStore = useAlbumsStore()
const id = Number(route.params.id)
const error = ref('')

onMounted(() => albumsStore.fetchAlbum(id))

const initial = computed(() => {
  const album = albumsStore.current
  if (!album || album.id !== id) return undefined
  return {
    title: album.title,
    artist: album.artist,
    release_year: album.release_year,
    producer: album.producer,
    record_label: album.record_label,
    tracks: album.tracks,
    musicians: album.musicians.map((m) => ({
      musician_name: m.musician.name,
      instrument: m.instrument,
    })),
    personnel: album.personnel.map((p) => ({
      person_name: p.person.name,
      role: p.role,
    })),
    other_details: album.other_details.map((d) => ({
      detail_name: d.detail.name,
      detail_type: d.detail_type,
    })),
  }
})

async function saveAlbum(payload: AlbumCreate) {
  error.value = ''
  try {
    await albumsStore.updateAlbum(id, payload)
    await navigateTo(`/albums/${id}`)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    error.value = err?.data?.detail ?? 'Failed to save album'
  }
}
</script>

<style scoped>
.page { padding: 1.5rem; max-width: 720px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
h1 { margin: 0; font-size: 1.4rem; }
.back { color: #4a6cf7; text-decoration: none; font-size: 0.9rem; }
.loading { color: #888; }
.error { color: #c0392b; margin-top: 0.5rem; }
</style>
