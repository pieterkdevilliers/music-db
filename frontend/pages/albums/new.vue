<template>
  <main class="page">
    <div class="page-header">
      <h1>Add Album</h1>
      <NuxtLink to="/albums" class="back">← Back</NuxtLink>
    </div>
    <AlbumForm submit-label="Add Album" @submit="createAlbum" />
    <p v-if="error" class="error">{{ error }}</p>
  </main>
</template>

<script setup lang="ts">
import type { AlbumCreate } from '~/stores/albums'

const albumsStore = useAlbumsStore()
const error = ref('')

async function createAlbum(payload: AlbumCreate) {
  error.value = ''
  try {
    const album = await albumsStore.createAlbum(payload)
    await navigateTo(`/albums/${album.id}`)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    error.value = err?.data?.detail ?? 'Failed to create album'
  }
}
</script>

<style scoped>
.page { padding: 1.5rem; max-width: 720px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
h1 { margin: 0; font-size: 1.4rem; }
.back { color: #4a6cf7; text-decoration: none; font-size: 0.9rem; }
.error { color: #c0392b; margin-top: 0.5rem; }
</style>
