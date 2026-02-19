<template>
  <main class="page">
    <div class="page-header">
      <h1>Albums</h1>
      <NuxtLink to="/albums/new" class="btn-primary">+ Add Album</NuxtLink>
    </div>

    <div class="layout">
      <aside class="filters">
        <h3>Filter</h3>
        <div class="field">
          <label>Search</label>
          <input v-model="filters.search" @input="debouncedFetch" placeholder="Title or artist…" />
        </div>
        <div class="field">
          <label>Artist</label>
          <input v-model="filters.artist" @input="debouncedFetch" />
        </div>
        <div class="field">
          <label>Record Label</label>
          <input v-model="filters.label" @input="debouncedFetch" />
        </div>
        <div class="field">
          <label>Instrument</label>
          <input v-model="filters.instrument" @input="debouncedFetch" placeholder="e.g. drums" />
        </div>
        <button @click="clearFilters">Clear</button>
      </aside>

      <section class="results">
        <div v-if="albumsStore.albums.length === 0" class="empty">No albums found.</div>
        <div class="grid">
          <AlbumCard v-for="a in albumsStore.albums" :key="a.id" :album="a" />
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
const albumsStore = useAlbumsStore()

const filters = reactive({
  search: '',
  artist: '',
  label: '',
  instrument: '',
})

let debounceTimer: ReturnType<typeof setTimeout>

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    albumsStore.fetchAlbums({
      search: filters.search || undefined,
      artist: filters.artist || undefined,
      label: filters.label || undefined,
      instrument: filters.instrument || undefined,
    })
  }, 300)
}

function clearFilters() {
  filters.search = ''
  filters.artist = ''
  filters.label = ''
  filters.instrument = ''
  albumsStore.fetchAlbums()
}

onMounted(() => albumsStore.fetchAlbums())
</script>

<style scoped>
.page { padding: 1.5rem; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
h1 { margin: 0; font-size: 1.4rem; }
.btn-primary {
  background: #4a6cf7; color: #fff; text-decoration: none;
  border-radius: 4px; padding: 0.45rem 1rem; font-size: 0.875rem;
}
.layout { display: flex; gap: 1.5rem; align-items: flex-start; }
.filters { width: 200px; flex-shrink: 0; }
.filters h3 { margin: 0 0 0.75rem; font-size: 0.95rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.75rem; }
label { font-size: 0.8rem; font-weight: 500; color: #555; }
.filters input { border: 1px solid #ccc; border-radius: 4px; padding: 0.35rem 0.5rem; font-size: 0.85rem; width: 100%; box-sizing: border-box; }
.filters button { background: #888; color: #fff; border: none; border-radius: 4px; padding: 0.35rem 0.75rem; cursor: pointer; font-size: 0.8rem; width: 100%; }
.results { flex: 1; }
.empty { color: #888; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
</style>
