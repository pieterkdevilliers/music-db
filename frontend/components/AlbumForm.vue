<template>
  <form @submit.prevent="submit" class="album-form">

    <!-- MusicBrainz lookup -->
    <div class="mb-lookup">
      <div class="mb-search-row">
        <div class="field flex-1">
          <label>Title *</label>
          <input v-model="form.title" required />
        </div>
        <div class="field flex-1">
          <label>Artist *</label>
          <input v-model="form.artist" required />
        </div>
        <button
          type="button"
          class="btn-mb"
          :disabled="!canSearch || mbSearching"
          @click="runMbSearch"
        >
          {{ mbSearching ? 'Searching…' : '🔍 MusicBrainz' }}
        </button>
      </div>

      <!-- Candidate list -->
      <div v-if="mbCandidates.length" class="mb-candidates">
        <div class="mb-candidates-header">
          <span>Select the correct release:</span>
          <button type="button" class="link-btn" @click="dismissSearch">Fill in manually</button>
        </div>
        <div
          v-for="c in mbCandidates"
          :key="c.mbid"
          class="mb-candidate"
          @click="selectCandidate(c)"
        >
          <span class="mb-title">{{ c.title }}</span>
          <span class="mb-meta">{{ c.artist }}</span>
          <span v-if="c.year" class="mb-meta">{{ c.year }}</span>
          <span v-if="c.label" class="mb-meta">{{ c.label }}</span>
          <span v-if="c.country" class="mb-meta mb-country">{{ c.country }}</span>
          <span class="mb-tracks">{{ c.track_count }} tracks</span>
          <button type="button" class="btn-use">Use this</button>
        </div>
      </div>

      <!-- Selected release badge -->
      <div v-if="form.mbid && !mbCandidates.length" class="mb-badge">
        <span>MusicBrainz data loaded</span>
        <button type="button" class="link-btn" @click="clearMb">× Clear</button>
      </div>

      <!-- No results message -->
      <p v-if="mbNoResults" class="mb-no-results">
        No results found on MusicBrainz. Fill in the details manually below.
      </p>
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
    <div class="field">
      <label>Personnel</label>
      <PersonnelTagInput v-model="form.personnel" />
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
import type { MBCandidate } from '~/composables/useMusicBrainz'

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
const { searchReleases, getRelease } = useMusicBrainz()

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
  personnel: props.initial?.personnel ?? [],
  collection_id: props.initial?.collection_id ?? null,
  mbid: null,
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

// --- MusicBrainz search state ---
const mbSearching = ref(false)
const mbCandidates = ref<MBCandidate[]>([])
const mbNoResults = ref(false)

const canSearch = computed(() =>
  form.value.title.trim().length > 0 && form.value.artist.trim().length > 0
)

async function runMbSearch() {
  mbCandidates.value = []
  mbNoResults.value = false
  mbSearching.value = true
  try {
    const results = await searchReleases(form.value.title.trim(), form.value.artist.trim())
    if (results.length === 0) {
      mbNoResults.value = true
    } else {
      mbCandidates.value = results
    }
  } catch {
    mbNoResults.value = true
  } finally {
    mbSearching.value = false
  }
}

async function selectCandidate(candidate: MBCandidate) {
  mbSearching.value = true
  try {
    const release = await getRelease(candidate.mbid)
    form.value.title = release.title
    form.value.artist = release.artist
    form.value.release_year = release.year ?? null
    form.value.record_label = release.label ?? null
    form.value.tracks = release.tracks
    form.value.mbid = release.mbid
    mbCandidates.value = []
  } catch {
    // Fall through — user can fill in manually
  } finally {
    mbSearching.value = false
  }
}

function dismissSearch() {
  mbCandidates.value = []
  mbNoResults.value = false
}

function clearMb() {
  form.value.mbid = null
}

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
.flex-1 { flex: 1; }
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

/* MusicBrainz lookup */
.mb-lookup { display: flex; flex-direction: column; gap: 0.5rem; }
.mb-search-row { display: flex; gap: 0.75rem; align-items: flex-end; flex-wrap: wrap; }
.btn-mb {
  background: #1d2a4a; color: #fff; border: none; border-radius: 4px;
  padding: 0.4rem 0.85rem; font-size: 0.85rem; cursor: pointer; white-space: nowrap;
  align-self: flex-end;
}
.btn-mb:disabled { opacity: 0.5; cursor: not-allowed; }

.mb-candidates { border: 1px solid #d0d7f7; border-radius: 6px; overflow: hidden; }
.mb-candidates-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.4rem 0.75rem; background: #eef1fd; font-size: 0.8rem; color: #444;
}
.mb-candidate {
  display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
  padding: 0.5rem 0.75rem; border-top: 1px solid #eee; cursor: pointer;
  font-size: 0.875rem;
}
.mb-candidate:hover { background: #f5f7ff; }
.mb-title { font-weight: 600; flex: 1; min-width: 120px; }
.mb-meta { color: #666; font-size: 0.8rem; }
.mb-country {
  background: #f0f0f0; border-radius: 3px;
  padding: 0 0.35rem; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
}
.mb-tracks { color: #999; font-size: 0.78rem; margin-left: auto; }
.btn-use {
  background: #4a6cf7; color: #fff; border: none; border-radius: 4px;
  padding: 0.25rem 0.6rem; font-size: 0.8rem; cursor: pointer;
}

.mb-badge {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: #eef1fd; border: 1px solid #c5cffb; border-radius: 4px;
  padding: 0.25rem 0.6rem; font-size: 0.8rem; color: #3a56c7; align-self: flex-start;
}
.mb-no-results { font-size: 0.85rem; color: #888; margin: 0; }
.link-btn {
  background: none; border: none; color: #4a6cf7; cursor: pointer;
  font-size: 0.8rem; padding: 0; text-decoration: underline;
}

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
