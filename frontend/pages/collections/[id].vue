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
            class="btn-danger btn-outlined"
            @click="deleteAllAlbums"
          >Delete all albums</button>
          <button class="btn-danger" @click="deleteCollection">Delete collection</button>
        </div>
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
const id = Number(route.params.id)

onMounted(() => collectionsStore.fetchCollection(id))

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
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; gap: 1rem; }
h1 { margin: 0 0 0.25rem; font-size: 1.4rem; }
.desc { color: #666; margin: 0; font-size: 0.9rem; }
.actions { display: flex; gap: 0.5rem; flex-shrink: 0; }
.btn-secondary {
  background: #4a6cf7; color: #fff; text-decoration: none;
  border-radius: 4px; padding: 0.45rem 1rem; font-size: 0.875rem;
}
.btn-danger { background: #c0392b; color: #fff; border: none; border-radius: 4px; padding: 0.45rem 0.75rem; cursor: pointer; }
.btn-danger.btn-outlined { background: transparent; border: 1px solid #c0392b; color: #c0392b; }
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
