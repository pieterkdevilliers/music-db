<template>
  <main class="page">
    <div v-if="collectionsStore.current">
      <div class="page-header">
        <div>
          <h1>{{ collectionsStore.current.name }}</h1>
          <p v-if="collectionsStore.current.description" class="desc">
            {{ collectionsStore.current.description }}
          </p>
        </div>
        <div class="actions">
          <NuxtLink :to="`/albums/new?collection_id=${id}`" class="btn-secondary">+ Add Album</NuxtLink>
          <button
            v-if="collectionsStore.current.albums?.length"
            class="btn-enrich"
            @click="enrichCollection"
            :disabled="enriching"
          >
            {{ enriching ? `Enriching… ${enrichmentStore.job.done}/${enrichmentStore.job.total || '?'}` : 'Enrich Collection' }}
          </button>
          <button
            v-if="enriching"
            class="btn-sm btn-cancel"
            @click="cancelEnrich"
          >Cancel</button>
          <button
            v-if="collectionsStore.current.albums?.length"
            class="btn-danger btn-outlined"
            @click="deleteAllAlbums"
          >Delete all albums</button>
          <button class="btn-danger" @click="deleteCollection">Delete collection</button>
        </div>
      </div>

      <div v-if="enrichNotice" :class="['enrich-notice', `enrich-notice--${enrichNotice.type}`]">
        {{ enrichNotice.message }}
        <button class="enrich-notice-close" @click="enrichNotice = null">×</button>
      </div>

      <div v-if="enriching" class="progress-block">
        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: enrichProgressPercent + '%' }" />
        </div>
        <div class="progress-stats">
          <span class="stat stat--purple">Enriched: {{ enrichmentStore.job.enriched }}</span>
          <span class="stat stat--grey">Skipped: {{ enrichmentStore.job.skipped }}</span>
          <span class="stat stat--red">Errors: {{ enrichmentStore.job.errors }}</span>
        </div>
        <p v-if="enrichmentStore.job.current_album" class="current-album">
          Current: {{ enrichmentStore.job.current_album }}
        </p>
      </div>

      <div v-if="!collectionsStore.current.albums?.length" class="empty">
        No albums in this collection yet. Browse <NuxtLink to="/albums">all albums</NuxtLink> to add some.
      </div>

      <div class="grid">
        <div
          v-for="album in collectionsStore.current.albums"
          :key="album.id"
          class="album-wrapper"
        >
          <AlbumCard :album="album" />
          <button class="remove-btn" @click="removeAlbum(album.id)">Remove</button>
        </div>
      </div>
    </div>
    <div v-else class="empty">Loading…</div>
  </main>
</template>

<script setup lang="ts">
const route = useRoute()
const collectionsStore = useCollectionsStore()
const enrichmentStore = useEnrichmentStore()
const id = Number(route.params.id)
const enrichNotice = ref<{ type: 'success' | 'error'; message: string } | null>(null)

const enriching = computed(
  () => ['running', 'starting'].includes(enrichmentStore.job.status)
)

const enrichProgressPercent = computed(() => {
  if (!enrichmentStore.job.total) return 0
  return Math.min(100, Math.round((enrichmentStore.job.done / enrichmentStore.job.total) * 100))
})

onMounted(async () => {
  await collectionsStore.fetchCollection(id)
  await enrichmentStore.pollProgress()
  if (enriching.value) enrichmentStore.startPolling()
})

onUnmounted(() => enrichmentStore.stopPolling())

async function enrichCollection() {
  enrichNotice.value = null
  try {
    await enrichmentStore.enrichCollection(id)
    const stop = watch(
      () => enrichmentStore.job.status,
      (status) => {
        if (status === 'done') {
          stop()
          enrichNotice.value = { type: 'success', message: 'Enrichment complete.' }
        } else if (status === 'error') {
          stop()
          enrichNotice.value = { type: 'error', message: enrichmentStore.job.error_list.at(-1) ?? 'Enrichment failed.' }
        }
      }
    )
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    enrichNotice.value = { type: 'error', message: err?.data?.detail ?? 'Failed to start enrichment.' }
  }
}

async function cancelEnrich() {
  await enrichmentStore.cancel()
}

async function removeAlbum(albumId: number) {
  await collectionsStore.removeAlbum(id, albumId)
}

async function deleteAllAlbums() {
  const count = collectionsStore.current?.albums?.length ?? 0
  if (!confirm(`Permanently delete all ${count} album${count === 1 ? '' : 's'} in this collection? This cannot be undone.`)) return
  await collectionsStore.deleteAllAlbums(id)
}

async function deleteCollection() {
  if (!confirm('Delete this collection?')) return
  await collectionsStore.deleteCollection(id)
  await navigateTo('/collections')
}
</script>

<style scoped>
.page { padding: 1.5rem; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1rem; gap: 1rem; }
h1 { margin: 0 0 0.25rem; font-size: 1.4rem; }
.desc { color: #666; margin: 0; font-size: 0.9rem; }
.actions { display: flex; gap: 0.5rem; flex-shrink: 0; flex-wrap: wrap; align-items: center; }
.btn-secondary {
  background: #4a6cf7; color: #fff; text-decoration: none;
  border-radius: 4px; padding: 0.45rem 1rem; font-size: 0.875rem;
}
.btn-danger { background: #c0392b; color: #fff; border: none; border-radius: 4px; padding: 0.45rem 0.75rem; cursor: pointer; }
.btn-danger.btn-outlined { background: transparent; border: 1px solid #c0392b; color: #c0392b; }
.btn-enrich {
  background: #8e44ad; color: #fff; border: none; border-radius: 4px;
  padding: 0.45rem 0.75rem; cursor: pointer; font-size: 0.875rem;
}
.btn-enrich:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-sm { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 0.2rem 0.5rem; cursor: pointer; font-size: 0.8rem; }
.btn-cancel { border-color: #e74c3c; color: #e74c3c; }
.enrich-notice {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.5rem 0.75rem; border-radius: 4px; font-size: 0.875rem;
  margin-bottom: 1rem;
}
.enrich-notice--success { background: #eafaf1; border: 1px solid #a9dfbf; color: #1e8449; }
.enrich-notice--error { background: #fdedec; border: 1px solid #f5b7b1; color: #c0392b; }
.enrich-notice-close { background: none; border: none; cursor: pointer; font-size: 1rem; color: inherit; padding: 0 0.1rem; margin-left: 0.5rem; }
.progress-block { margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.4rem; }
.progress-bar-track { height: 8px; background: #e8e8e8; border-radius: 4px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: #8e44ad; border-radius: 4px; transition: width 0.4s ease; }
.progress-stats { display: flex; gap: 1rem; font-size: 0.8rem; }
.stat { font-weight: 600; }
.stat--purple { color: #8e44ad; }
.stat--grey { color: #888; }
.stat--red { color: #e74c3c; }
.current-album { font-size: 0.8rem; color: #666; margin: 0; }
.empty { color: #888; margin-top: 2rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
.album-wrapper { position: relative; }
.remove-btn {
  position: absolute; top: 0.5rem; right: 0.5rem;
  background: rgba(192,57,43,0.85); color: #fff;
  border: none; border-radius: 4px; padding: 0.2rem 0.5rem;
  font-size: 0.75rem; cursor: pointer;
}
</style>
