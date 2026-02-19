<template>
  <form @submit.prevent="submit" class="album-form">
    <div class="field">
      <label>Title *</label>
      <input v-model="form.title" required />
    </div>
    <div class="field">
      <label>Artist *</label>
      <input v-model="form.artist" required />
    </div>
    <div class="row">
      <div class="field">
        <label>Release Year</label>
        <input v-model.number="form.release_year" type="number" min="1900" max="2100" />
      </div>
      <div class="field">
        <label>Producer</label>
        <input v-model="form.producer" />
      </div>
      <div class="field">
        <label>Record Label</label>
        <input v-model="form.record_label" />
      </div>
    </div>
    <div class="field">
      <label>Tracks (one per line)</label>
      <textarea v-model="tracksText" rows="5" placeholder="Track 1&#10;Track 2&#10;Track 3" />
    </div>
    <div class="field">
      <label>Musicians</label>
      <MusicianTagInput v-model="form.musicians" />
    </div>
    <div v-if="!hideCollectionPicker" class="field">
      <label>Add to Collection</label>
      <select v-model="form.collection_id">
        <option :value="null">— None —</option>
        <option v-for="c in collectionsStore.collections" :key="c.id" :value="c.id">
          {{ c.name }}
        </option>
      </select>
    </div>
    <div class="actions">
      <button type="submit" :disabled="loading">
        {{ loading ? 'Saving…' : submitLabel }}
      </button>
      <slot name="secondary-action" />
    </div>
    <p v-if="error" class="error">{{ error }}</p>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { AlbumCreate } from '~/stores/albums'

const props = withDefaults(defineProps<{
  initial?: Partial<AlbumCreate & { tracks: string[] }>
  submitLabel?: string
  hideCollectionPicker?: boolean
}>(), {
  submitLabel: 'Save Album',
  hideCollectionPicker: false,
})

const emit = defineEmits<{
  (e: 'submit', payload: AlbumCreate): void
}>()

const collectionsStore = useCollectionsStore()

onMounted(() => collectionsStore.fetchCollections())

const loading = ref(false)
const error = ref('')

const form = ref<AlbumCreate>({
  title: props.initial?.title ?? '',
  artist: props.initial?.artist ?? '',
  release_year: props.initial?.release_year ?? null,
  producer: props.initial?.producer ?? null,
  record_label: props.initial?.record_label ?? null,
  tracks: props.initial?.tracks ?? [],
  musicians: props.initial?.musicians ?? [],
  collection_id: props.initial?.collection_id ?? null,
})

const tracksText = computed({
  get: () => form.value.tracks.join('\n'),
  set: (val: string) => {
    form.value.tracks = val
      .split('\n')
      .map((t) => t.trim())
      .filter(Boolean)
  },
})

async function submit() {
  error.value = ''
  loading.value = true
  try {
    emit('submit', { ...form.value })
  } catch (e: unknown) {
    error.value = (e as Error).message ?? 'An error occurred'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.album-form { display: flex; flex-direction: column; gap: 1rem; max-width: 640px; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.row { display: flex; gap: 1rem; flex-wrap: wrap; }
.row .field { flex: 1; min-width: 140px; }
label { font-size: 0.85rem; font-weight: 500; color: #555; }
input, textarea, select {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  font-size: 0.9rem;
  font-family: inherit;
}
textarea { resize: vertical; }
.actions { display: flex; gap: 0.75rem; align-items: center; }
button[type="submit"] {
  background: #4a6cf7;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1.25rem;
  cursor: pointer;
  font-size: 0.9rem;
}
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #c0392b; font-size: 0.875rem; }
</style>
