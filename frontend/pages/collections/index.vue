<template>
  <main class="page">
    <div class="page-header">
      <h1>My Collections</h1>
      <button @click="showCreate = true">+ New Collection</button>
    </div>

    <div v-if="collectionsStore.collections.length === 0" class="empty">
      No collections yet. Create one to get started.
    </div>

    <div class="grid">
      <CollectionCard
        v-for="c in collectionsStore.collections"
        :key="c.id"
        :collection="c"
      />
    </div>

    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h2>New Collection</h2>
        <form @submit.prevent="createCollection">
          <div class="field">
            <label>Name</label>
            <input v-model="newName" required />
          </div>
          <div class="field">
            <label>Description</label>
            <input v-model="newDesc" />
          </div>
          <div class="actions">
            <button type="submit">Create</button>
            <button type="button" @click="showCreate = false">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
const collectionsStore = useCollectionsStore()

const showCreate = ref(false)
const newName = ref('')
const newDesc = ref('')

onMounted(() => collectionsStore.fetchCollections())

async function createCollection() {
  await collectionsStore.createCollection(newName.value, newDesc.value || undefined)
  newName.value = ''
  newDesc.value = ''
  showCreate.value = false
}
</script>

<style scoped>
.page { padding: 1.5rem; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
h1 { margin: 0; font-size: 1.4rem; }
button {
  background: #4a6cf7;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.45rem 1rem;
  cursor: pointer;
}
.empty { color: #888; margin-top: 2rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: #fff; border-radius: 8px; padding: 1.5rem; width: 360px;
}
.modal h2 { margin: 0 0 1rem; font-size: 1.1rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.75rem; }
label { font-size: 0.85rem; font-weight: 500; }
.modal input { border: 1px solid #ccc; border-radius: 4px; padding: 0.4rem 0.6rem; }
.actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
.actions button:last-child { background: #888; }
</style>
