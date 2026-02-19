<template>
  <main class="page" v-if="albumsStore.current">
    <div class="page-header">
      <div>
        <h1>{{ albumsStore.current.title }}</h1>
        <p class="artist">{{ albumsStore.current.artist }}</p>
      </div>
      <div class="actions">
        <NuxtLink :to="`/albums/${id}/edit`" class="btn-secondary">Edit</NuxtLink>
        <button class="btn-danger" @click="deleteAlbum">Delete</button>
      </div>
    </div>

    <div class="meta-row">
      <span v-if="albumsStore.current.release_year">{{ albumsStore.current.release_year }}</span>
      <span v-if="albumsStore.current.record_label">{{ albumsStore.current.record_label }}</span>
      <span v-if="albumsStore.current.producer">Produced by {{ albumsStore.current.producer }}</span>
    </div>

    <div class="section">
      <h2>Tracks</h2>
      <ol v-if="albumsStore.current.tracks.length">
        <li v-for="(track, i) in albumsStore.current.tracks" :key="i">{{ track }}</li>
      </ol>
      <p v-else class="empty">No tracks listed.</p>
    </div>

    <div class="section">
      <h2>Musicians</h2>
      <table v-if="albumsStore.current.musicians.length" class="musicians-table">
        <thead>
          <tr><th>Name</th><th>Instrument</th></tr>
        </thead>
        <tbody>
          <tr v-for="m in albumsStore.current.musicians" :key="`${m.musician.id}-${m.instrument}`">
            <td>
              <NuxtLink :to="`/musicians/${m.musician.id}`">{{ m.musician.name }}</NuxtLink>
            </td>
            <td>{{ m.instrument }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">No musicians listed.</p>
    </div>

    <div class="section">
      <h2>Collections</h2>

      <div v-if="albumCollections.length" class="assigned-list">
        <div v-for="c in albumCollections" :key="c.id" class="assigned-tag">
          <NuxtLink :to="`/collections/${c.id}`">{{ c.name }}</NuxtLink>
          <button class="remove-tag" @click="removeFromCollection(c.id)" title="Remove from collection">×</button>
        </div>
      </div>
      <p v-else class="empty">Not in any collection yet.</p>

      <div v-if="availableCollections.length" class="collection-row">
        <select v-model="selectedCollection">
          <option :value="null">Add to collection…</option>
          <option v-for="c in availableCollections" :key="c.id" :value="c.id">
            {{ c.name }}
          </option>
        </select>
        <button :disabled="!selectedCollection" @click="addToCollection">Add</button>
      </div>
    </div>
  </main>
  <main v-else class="page empty-page">Loading…</main>
</template>

<script setup lang="ts">
const route = useRoute()
const albumsStore = useAlbumsStore()
const collectionsStore = useCollectionsStore()
const id = Number(route.params.id)
const selectedCollection = ref<number | null>(null)

onMounted(async () => {
  await albumsStore.fetchAlbum(id)
  await collectionsStore.fetchCollections()
})

const albumCollections = computed(() =>
  collectionsStore.collections.filter((c) => c.albums.some((a) => a.id === id))
)

const availableCollections = computed(() =>
  collectionsStore.collections.filter((c) => !c.albums.some((a) => a.id === id))
)

async function deleteAlbum() {
  if (!confirm('Delete this album?')) return
  await albumsStore.deleteAlbum(id)
  await navigateTo('/albums')
}

async function addToCollection() {
  if (!selectedCollection.value) return
  await collectionsStore.addAlbum(selectedCollection.value, id)
  selectedCollection.value = null
}

async function removeFromCollection(collectionId: number) {
  await collectionsStore.removeAlbum(collectionId, id)
}
</script>

<style scoped>
.page { padding: 1.5rem; max-width: 720px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 0.5rem; }
h1 { margin: 0; font-size: 1.5rem; }
.artist { color: #555; margin: 0.25rem 0 0; font-size: 1rem; }
.actions { display: flex; gap: 0.5rem; flex-shrink: 0; }
.btn-secondary {
  background: #4a6cf7; color: #fff; text-decoration: none;
  border-radius: 4px; padding: 0.4rem 0.75rem; font-size: 0.875rem;
}
.btn-danger { background: #c0392b; color: #fff; border: none; border-radius: 4px; padding: 0.4rem 0.75rem; cursor: pointer; }
.meta-row { display: flex; gap: 1rem; flex-wrap: wrap; color: #666; font-size: 0.875rem; margin-bottom: 1.5rem; }
.meta-row span::before { content: '· '; }
.meta-row span:first-child::before { content: ''; }
.section { margin-bottom: 1.5rem; }
h2 { font-size: 1rem; font-weight: 600; margin: 0 0 0.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.25rem; }
ol { padding-left: 1.25rem; margin: 0; }
ol li { padding: 0.15rem 0; font-size: 0.9rem; }
.musicians-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
.musicians-table th { text-align: left; padding: 0.35rem 0.5rem; border-bottom: 2px solid #eee; font-size: 0.8rem; color: #777; }
.musicians-table td { padding: 0.35rem 0.5rem; border-bottom: 1px solid #f0f0f0; }
.musicians-table a { color: #4a6cf7; text-decoration: none; }
.assigned-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.75rem; }
.assigned-tag {
  display: inline-flex; align-items: center; gap: 0.3rem;
  background: #eef1fd; border: 1px solid #c5cffb; border-radius: 4px;
  padding: 0.2rem 0.5rem; font-size: 0.85rem;
}
.assigned-tag a { color: #4a6cf7; text-decoration: none; }
.assigned-tag a:hover { text-decoration: underline; }
.remove-tag {
  background: none; border: none; color: #888; cursor: pointer;
  font-size: 1rem; line-height: 1; padding: 0 0.1rem;
}
.remove-tag:hover { color: #c0392b; }
.collection-row { display: flex; gap: 0.5rem; }
select { border: 1px solid #ccc; border-radius: 4px; padding: 0.35rem 0.5rem; font-size: 0.875rem; }
.collection-row button { background: #4a6cf7; color: #fff; border: none; border-radius: 4px; padding: 0.35rem 0.75rem; cursor: pointer; }
.collection-row button:disabled { opacity: 0.5; }
.empty { color: #888; font-size: 0.9rem; margin-bottom: 0.75rem; }
.empty-page { color: #888; }
</style>
