<template>
  <main class="page">
    <h1>Import Library</h1>

    <!-- Tab switcher -->
    <div class="tabs">
      <button
        class="tab"
        :class="{ 'tab--active': activeTab === 'roon' }"
        @click="activeTab = 'roon'"
      >
        Roon
      </button>
      <button
        class="tab"
        :class="{ 'tab--active': activeTab === 'files' }"
        @click="activeTab = 'files'"
      >
        Files
      </button>
    </div>

    <!-- ================================================================ -->
    <!-- ROON TAB                                                          -->
    <!-- ================================================================ -->
    <template v-if="activeTab === 'roon'">
      <!-- Connection panel -->
      <section class="card">
        <h2>1. Connect to Roon Core</h2>
        <p class="hint">
          mDNS doesn't work inside Docker — enter the <strong>IP address</strong>
          of the machine running Roon Core (e.g. <code>192.168.1.42</code>).
        </p>
        <div class="connect-row">
          <input
            v-model="host"
            placeholder="192.168.x.x"
            class="host-input"
            :disabled="connecting"
          />
          <input
            v-model.number="port"
            type="number"
            placeholder="9330"
            class="port-input"
            :disabled="connecting"
          />
          <button @click="connect" :disabled="connecting || !host.trim()">
            {{ connecting ? 'Connecting…' : 'Connect' }}
          </button>
        </div>
        <p v-if="connectError" class="error">{{ connectError }}</p>
      </section>

      <!-- Status panel -->
      <section class="card">
        <h2>2. Authorize in Roon</h2>
        <div class="status-row">
          <span class="dot" :class="statusDotClass" />
          <span>{{ statusLabel }}</span>
          <button class="btn-sm" @click="refreshStatus" :disabled="polling">Refresh</button>
        </div>
        <div v-if="status.connected && !status.authorized" class="auth-steps">
          <p>To authorize:</p>
          <ol>
            <li>Open Roon on any device</li>
            <li>Go to <strong>Settings → Extensions</strong></li>
            <li>Find <strong>"Music DB Importer"</strong> and click <strong>Enable</strong></li>
            <li>Click Refresh above</li>
          </ol>
        </div>
        <p v-if="status.core_name" class="core-name">Core: {{ status.core_name }}</p>
      </section>

      <!-- Probe panel -->
      <section class="card">
        <h2>3. Probe library</h2>
        <p class="hint">Fetches raw data for the first few albums so you can see exactly what Roon provides.</p>
        <div class="probe-row">
          <label>Albums to fetch:
            <input v-model.number="probeCount" type="number" min="1" max="10" class="count-input" />
          </label>
          <button @click="runProbe" :disabled="!status.authorized || probing">
            {{ probing ? 'Fetching…' : 'Probe' }}
          </button>
        </div>
        <p v-if="probeError" class="error">{{ probeError }}</p>

        <div v-if="probeResult" class="probe-result">
          <div class="probe-summary">
            <strong>Albums found:</strong> {{ probeResult.albums?.length ?? 0 }} returned<br/>
            <strong>Total in library:</strong> {{ probeResult.browse_result?.list?.count ?? '?' }}
          </div>

          <div v-for="(album, i) in probeResult.albums" :key="i" class="album-snippet">
            <div class="album-title">{{ album.title }}</div>
            <div class="album-sub">{{ album.subtitle }}</div>
          </div>

          <details class="raw-json">
            <summary>Raw Roon JSON response</summary>
            <pre>{{ JSON.stringify(probeResult, null, 2) }}</pre>
          </details>
        </div>
      </section>

      <!-- Roon import panel -->
      <section class="card">
        <h2>4. Import Library</h2>
        <p class="hint">
          Imports all albums from your Roon library. Albums already in the database
          (matched by title + artist) are <strong>updated</strong> — tracks are refreshed
          and artwork is added if missing. Year and label are not available from the Roon
          Browse API and will be left blank.
        </p>

        <div class="collection-row">
          <label for="roon-collection-select">Add all albums to collection:</label>
          <select id="roon-collection-select" v-model="roonSelectedCollectionId" class="collection-select">
            <option :value="null">— none —</option>
            <option v-for="c in collections" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>

        <div v-if="roonJob.status !== 'running' && roonJob.status !== 'starting'" class="import-actions">
          <button
            class="btn-import"
            @click="startRoonImport"
            :disabled="!status.authorized || roonImportStarting"
          >
            {{
              roonJob.status === 'done' ? 'Import again' :
              roonJob.status === 'cancelled' ? 'Restart import' :
              roonImportStarting ? 'Starting…' : 'Start import'
            }}
          </button>
          <p v-if="!status.authorized" class="hint" style="margin-top: 0.5rem;">
            Authorize in Roon first (step 2).
          </p>
        </div>

        <div v-if="roonJob.status === 'running' || roonJob.status === 'starting'" class="progress-block">
          <div class="progress-header">
            <span>Importing… {{ roonJob.done }} / {{ roonJob.total || '?' }}</span>
            <button class="btn-sm btn-cancel" @click="cancelRoonImport" :disabled="roonCancelling">
              {{ roonCancelling ? 'Cancelling…' : 'Cancel' }}
            </button>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" :style="{ width: roonProgressPercent + '%' }" />
          </div>
          <div class="progress-stats">
            <span class="stat stat--green">New: {{ roonJob.imported }}</span>
            <span class="stat stat--amber">Updated: {{ roonJob.updated }}</span>
            <span class="stat stat--grey">Skipped: {{ roonJob.skipped }}</span>
            <span class="stat stat--red">Errors: {{ roonJob.errors }}</span>
          </div>
        </div>

        <div v-if="['done', 'cancelled', 'error'].includes(roonJob.status)" class="import-summary">
          <p :class="roonSummaryClass">{{ roonSummaryLabel }}</p>
          <div class="progress-stats">
            <span class="stat stat--green">New: {{ roonJob.imported }}</span>
            <span class="stat stat--amber">Updated: {{ roonJob.updated }}</span>
            <span class="stat stat--grey">Skipped: {{ roonJob.skipped }}</span>
            <span class="stat stat--red">Errors: {{ roonJob.errors }}</span>
          </div>
          <div v-if="roonJob.total > 0" class="progress-bar-track" style="margin-top: 0.5rem;">
            <div
              class="progress-bar-fill"
              :class="{ 'fill--done': roonJob.status === 'done' }"
              :style="{ width: roonProgressPercent + '%' }"
            />
          </div>
        </div>

        <details v-if="roonJob.error_list?.length" class="error-details">
          <summary>{{ roonJob.error_list.length }} error{{ roonJob.error_list.length === 1 ? '' : 's' }}</summary>
          <ul class="error-list">
            <li v-for="(e, i) in roonJob.error_list" :key="i">{{ e }}</li>
          </ul>
        </details>
      </section>
    </template>

    <!-- ================================================================ -->
    <!-- FILES TAB                                                         -->
    <!-- ================================================================ -->
    <template v-else-if="activeTab === 'files'">
      <section class="card">
        <h2>Scan directory for audio files</h2>
        <p class="hint">
          Enter the path to your music library <strong>as seen inside the Docker container</strong>.
          Mount the drive in <code>docker-compose.yml</code> first, e.g.
          <code>- /mnt/music:/music:ro</code>, then enter <code>/music</code> below.
        </p>
        <p class="hint">
          Supports FLAC, MP3, M4A, AIFF, OGG, and WAV. Each directory containing audio files
          is treated as one album. Tags are read via mutagen; embedded artwork and folder images
          are imported. Albums not found in the database are <strong>created</strong>; existing
          albums (matched by title + artist) are <strong>updated</strong>.
        </p>

        <div class="path-row">
          <input
            v-model="flacPath"
            placeholder="/music"
            class="path-input"
            :disabled="flacJob.status === 'running' || flacJob.status === 'starting'"
          />
        </div>

        <div class="collection-row" style="margin-top: 0.75rem;">
          <label for="flac-collection-select">Add all albums to collection:</label>
          <select id="flac-collection-select" v-model="flacSelectedCollectionId" class="collection-select">
            <option :value="null">— none —</option>
            <option v-for="c in collections" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
      </section>

      <section class="card">
        <h2>Import</h2>

        <div v-if="flacJob.status !== 'running' && flacJob.status !== 'starting'" class="import-actions">
          <button
            class="btn-import"
            @click="startFlacImport"
            :disabled="!flacPath.trim() || flacImportStarting"
          >
            {{
              flacJob.status === 'done' ? 'Scan again' :
              flacJob.status === 'cancelled' ? 'Restart scan' :
              flacImportStarting ? 'Starting…' : 'Start scan'
            }}
          </button>
        </div>

        <div v-if="flacJob.status === 'running' || flacJob.status === 'starting'" class="progress-block">
          <div class="progress-header">
            <span>Scanning… {{ flacJob.done }} / {{ flacJob.total || '?' }}</span>
            <button class="btn-sm btn-cancel" @click="cancelFlacImport" :disabled="flacCancelling">
              {{ flacCancelling ? 'Cancelling…' : 'Cancel' }}
            </button>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" :style="{ width: flacProgressPercent + '%' }" />
          </div>
          <div class="progress-stats">
            <span class="stat stat--green">New: {{ flacJob.imported }}</span>
            <span class="stat stat--amber">Updated: {{ flacJob.updated }}</span>
            <span class="stat stat--grey">Skipped: {{ flacJob.skipped }}</span>
            <span class="stat stat--red">Errors: {{ flacJob.errors }}</span>
          </div>
          <p v-if="flacJob.root_path" class="hint" style="margin-top: 0.5rem;">
            Scanning: <code>{{ flacJob.root_path }}</code>
          </p>
        </div>

        <div v-if="['done', 'cancelled', 'error'].includes(flacJob.status)" class="import-summary">
          <p :class="flacSummaryClass">{{ flacSummaryLabel }}</p>
          <div class="progress-stats">
            <span class="stat stat--green">New: {{ flacJob.imported }}</span>
            <span class="stat stat--amber">Updated: {{ flacJob.updated }}</span>
            <span class="stat stat--grey">Skipped: {{ flacJob.skipped }}</span>
            <span class="stat stat--red">Errors: {{ flacJob.errors }}</span>
          </div>
          <div v-if="flacJob.total > 0" class="progress-bar-track" style="margin-top: 0.5rem;">
            <div
              class="progress-bar-fill"
              :class="{ 'fill--done': flacJob.status === 'done' }"
              :style="{ width: flacProgressPercent + '%' }"
            />
          </div>
        </div>

        <details v-if="flacJob.error_list?.length" class="error-details">
          <summary>{{ flacJob.error_list.length }} error{{ flacJob.error_list.length === 1 ? '' : 's' }}</summary>
          <ul class="error-list">
            <li v-for="(e, i) in flacJob.error_list" :key="i">{{ e }}</li>
          </ul>
        </details>
      </section>
    </template>

    <!-- ================================================================ -->
    <!-- DANGER ZONE (always visible)                                      -->
    <!-- ================================================================ -->
    <section class="card card--danger">
      <h2>Danger zone</h2>
      <div class="danger-row">
        <div>
          <strong>Delete all albums</strong>
          <p class="hint" style="margin: 0.25rem 0 0;">
            Permanently removes every album from the database regardless of collection.
            This cannot be undone.
          </p>
        </div>
        <button class="btn-danger-solid" @click="deleteAllAlbums" :disabled="deletingAll">
          {{ deletingAll ? 'Deleting…' : 'Delete all albums' }}
        </button>
      </div>
      <p v-if="deleteAllResult !== null" class="delete-result">
        {{ deleteAllResult }}
      </p>
    </section>
  </main>
</template>

<script setup lang="ts">
const { apiFetch } = useApi()

// ── Tab ────────────────────────────────────────────────────────────────────
const activeTab = ref<'roon' | 'files'>('roon')

// ── Shared ─────────────────────────────────────────────────────────────────
interface Collection {
  id: number
  name: string
}

interface ImportJob {
  status: string
  total: number
  done: number
  imported: number
  updated: number
  skipped: number
  errors: number
  error_list: string[]
  cancel_requested: boolean
  root_path?: string | null
}

const collections = ref<Collection[]>([])

async function fetchCollections() {
  try {
    const data = await apiFetch('/collections')
    collections.value = (data as Collection[]).map((c: Collection) => ({ id: c.id, name: c.name }))
  } catch {
    // ignore — picker is optional
  }
}

// ── Persisted settings (localStorage) ─────────────────────────────────────
const LS_ROON_HOST = 'import.roon.host'
const LS_ROON_PORT = 'import.roon.port'
const LS_FLAC_PATH = 'import.flac.path'

// ── Roon ───────────────────────────────────────────────────────────────────
const host = ref('')
const port = ref(9330)
const connecting = ref(false)
const connectError = ref('')

const polling = ref(false)
const status = ref({ connected: false, authorized: false, core_name: null as string | null })

const probeCount = ref(3)
const probing = ref(false)
const probeError = ref('')
const probeResult = ref<Record<string, unknown> | null>(null)

const roonSelectedCollectionId = ref<number | null>(null)
const roonImportStarting = ref(false)
const roonCancelling = ref(false)
const roonJob = ref<ImportJob>({
  status: 'idle', total: 0, done: 0, imported: 0, updated: 0,
  skipped: 0, errors: 0, error_list: [], cancel_requested: false,
})
let roonPollTimer: ReturnType<typeof setInterval> | null = null

const statusDotClass = computed(() => {
  if (status.value.authorized) return 'dot--green'
  if (status.value.connected) return 'dot--yellow'
  return 'dot--grey'
})

const statusLabel = computed(() => {
  if (status.value.authorized) return `Authorized (${status.value.core_name ?? 'Roon Core'})`
  if (status.value.connected) return 'Connected — waiting for authorization in Roon UI'
  return 'Not connected'
})

const roonProgressPercent = computed(() => {
  if (!roonJob.value.total) return 0
  return Math.min(100, Math.round((roonJob.value.done / roonJob.value.total) * 100))
})

const roonSummaryLabel = computed(() => {
  if (roonJob.value.status === 'done') return 'Import complete!'
  if (roonJob.value.status === 'cancelled') return 'Import cancelled.'
  if (roonJob.value.status === 'error') return 'Import failed — see errors below.'
  return ''
})

const roonSummaryClass = computed(() => {
  if (roonJob.value.status === 'done') return 'summary-done'
  if (roonJob.value.status === 'cancelled') return 'summary-cancelled'
  return 'summary-error'
})

async function connect() {
  connectError.value = ''
  connecting.value = true
  try {
    await apiFetch('/import/roon/connect', {
      method: 'POST',
      body: { host: host.value.trim(), port: port.value },
    })
    await refreshStatus()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    connectError.value = err?.data?.detail ?? 'Failed to connect'
  } finally {
    connecting.value = false
  }
}

async function refreshStatus() {
  polling.value = true
  try {
    status.value = await apiFetch('/import/roon/status')
  } catch {
    // ignore
  } finally {
    polling.value = false
  }
}

async function runProbe() {
  probeError.value = ''
  probeResult.value = null
  probing.value = true
  try {
    probeResult.value = await apiFetch(`/import/roon/probe?count=${probeCount.value}`)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    probeError.value = err?.data?.detail ?? 'Probe failed'
  } finally {
    probing.value = false
  }
}

async function fetchRoonProgress() {
  try {
    roonJob.value = await apiFetch('/import/roon/progress')
  } catch {
    // ignore transient errors
  }
  if (!['running', 'starting'].includes(roonJob.value.status)) {
    stopRoonPolling()
  }
}

function startRoonPolling() {
  if (roonPollTimer) return
  roonPollTimer = setInterval(fetchRoonProgress, 2000)
}

function stopRoonPolling() {
  if (roonPollTimer) {
    clearInterval(roonPollTimer)
    roonPollTimer = null
  }
}

async function startRoonImport() {
  roonImportStarting.value = true
  roonCancelling.value = false
  try {
    await apiFetch('/import/roon/start', {
      method: 'POST',
      body: { collection_id: roonSelectedCollectionId.value },
    })
    await fetchRoonProgress()
    startRoonPolling()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    roonJob.value = {
      ...roonJob.value,
      status: 'error',
      error_list: [err?.data?.detail ?? 'Failed to start import'],
    }
  } finally {
    roonImportStarting.value = false
  }
}

async function cancelRoonImport() {
  roonCancelling.value = true
  try {
    await apiFetch('/import/roon/cancel', { method: 'POST' })
  } catch {
    // ignore
  }
}

// ── Files ──────────────────────────────────────────────────────────────────
const flacPath = ref('')
const flacSelectedCollectionId = ref<number | null>(null)
const flacImportStarting = ref(false)
const flacCancelling = ref(false)
const flacJob = ref<ImportJob>({
  status: 'idle', total: 0, done: 0, imported: 0, updated: 0,
  skipped: 0, errors: 0, error_list: [], cancel_requested: false,
})
let flacPollTimer: ReturnType<typeof setInterval> | null = null

const flacProgressPercent = computed(() => {
  if (!flacJob.value.total) return 0
  return Math.min(100, Math.round((flacJob.value.done / flacJob.value.total) * 100))
})

const flacSummaryLabel = computed(() => {
  if (flacJob.value.status === 'done') return 'Scan complete!'
  if (flacJob.value.status === 'cancelled') return 'Scan cancelled.'
  if (flacJob.value.status === 'error') return 'Scan failed — see errors below.'
  return ''
})

const flacSummaryClass = computed(() => {
  if (flacJob.value.status === 'done') return 'summary-done'
  if (flacJob.value.status === 'cancelled') return 'summary-cancelled'
  return 'summary-error'
})

async function fetchFlacProgress() {
  try {
    flacJob.value = await apiFetch('/import/flac/progress')
  } catch {
    // ignore transient errors
  }
  if (!['running', 'starting'].includes(flacJob.value.status)) {
    stopFlacPolling()
  }
}

function startFlacPolling() {
  if (flacPollTimer) return
  flacPollTimer = setInterval(fetchFlacProgress, 2000)
}

function stopFlacPolling() {
  if (flacPollTimer) {
    clearInterval(flacPollTimer)
    flacPollTimer = null
  }
}

async function startFlacImport() {
  flacImportStarting.value = true
  flacCancelling.value = false
  try {
    await apiFetch('/import/flac/start', {
      method: 'POST',
      body: {
        root_path: flacPath.value.trim(),
        collection_id: flacSelectedCollectionId.value,
      },
    })
    await fetchFlacProgress()
    startFlacPolling()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    flacJob.value = {
      ...flacJob.value,
      status: 'error',
      error_list: [err?.data?.detail ?? 'Failed to start scan'],
    }
  } finally {
    flacImportStarting.value = false
  }
}

async function cancelFlacImport() {
  flacCancelling.value = true
  try {
    await apiFetch('/import/flac/cancel', { method: 'POST' })
  } catch {
    // ignore
  }
}

// ── Danger zone ────────────────────────────────────────────────────────────
const deletingAll = ref(false)
const deleteAllResult = ref<string | null>(null)

async function deleteAllAlbums() {
  if (!confirm('Permanently delete ALL albums from the database? This cannot be undone.')) return
  deletingAll.value = true
  deleteAllResult.value = null
  try {
    const res = await apiFetch<{ deleted: number }>('/albums', { method: 'DELETE' })
    deleteAllResult.value = `Done — ${res.deleted} album${res.deleted === 1 ? '' : 's'} deleted.`
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    deleteAllResult.value = `Error: ${err?.data?.detail ?? 'Failed to delete albums'}`
  } finally {
    deletingAll.value = false
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  // Restore persisted settings
  host.value = localStorage.getItem(LS_ROON_HOST) ?? ''
  port.value = Number(localStorage.getItem(LS_ROON_PORT) ?? 9330)
  flacPath.value = localStorage.getItem(LS_FLAC_PATH) ?? ''

  // Save on change
  watch(host, (v) => localStorage.setItem(LS_ROON_HOST, v))
  watch(port, (v) => localStorage.setItem(LS_ROON_PORT, String(v)))
  watch(flacPath, (v) => localStorage.setItem(LS_FLAC_PATH, v))

  await Promise.all([refreshStatus(), fetchCollections()])
  // Restore in-progress jobs if the page is refreshed mid-import
  await Promise.all([fetchRoonProgress(), fetchFlacProgress()])
  if (['running', 'starting'].includes(roonJob.value.status)) startRoonPolling()
  if (['running', 'starting'].includes(flacJob.value.status)) {
    activeTab.value = 'files'
    startFlacPolling()
  }
})

onUnmounted(() => {
  stopRoonPolling()
  stopFlacPolling()
})
</script>

<style scoped>
.page { padding: 1.5rem; max-width: 760px; display: flex; flex-direction: column; gap: 1.5rem; }
h1 { margin: 0 0 0.25rem; font-size: 1.5rem; }
h2 { margin: 0 0 0.75rem; font-size: 1rem; font-weight: 600; }

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: -0.5rem;
}
.tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  padding: 0.5rem 1.25rem;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  color: #666;
  transition: color 0.15s, border-color 0.15s;
}
.tab:hover { color: #333; }
.tab--active { color: #4a6cf7; border-bottom-color: #4a6cf7; }

.card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
}
.card--danger {
  border-color: #e74c3c;
  background: #fff8f8;
}
.danger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  flex-wrap: wrap;
}
.btn-danger-solid {
  background: #c0392b; color: #fff; border: none; border-radius: 4px;
  padding: 0.5rem 1.1rem; cursor: pointer; font-size: 0.9rem; white-space: nowrap;
  flex-shrink: 0;
}
.btn-danger-solid:disabled { opacity: 0.5; cursor: not-allowed; }
.delete-result { margin: 0.75rem 0 0; font-size: 0.875rem; color: #555; }

.hint { font-size: 0.875rem; color: #666; margin: 0 0 0.75rem; }
code { background: #f3f3f3; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.85em; }

/* Roon connect */
.connect-row { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.host-input { flex: 1; min-width: 160px; border: 1px solid #ccc; border-radius: 4px; padding: 0.4rem 0.6rem; font-size: 0.9rem; }
.port-input { width: 80px; border: 1px solid #ccc; border-radius: 4px; padding: 0.4rem 0.6rem; font-size: 0.9rem; }
.connect-row button, .probe-row button {
  background: #4a6cf7; color: #fff; border: none; border-radius: 4px;
  padding: 0.4rem 1rem; cursor: pointer; font-size: 0.9rem; white-space: nowrap;
}
.connect-row button:disabled, .probe-row button:disabled { opacity: 0.5; cursor: not-allowed; }

.status-row { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem; font-size: 0.9rem; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot--green { background: #27ae60; }
.dot--yellow { background: #f39c12; }
.dot--grey { background: #bbb; }
.btn-sm { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 0.2rem 0.5rem; cursor: pointer; font-size: 0.8rem; margin-left: auto; }
.btn-cancel { border-color: #e74c3c; color: #e74c3c; }
.btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }

.auth-steps { font-size: 0.875rem; color: #555; margin: 0.5rem 0; }
.auth-steps ol { margin: 0.25rem 0 0 1.25rem; padding: 0; line-height: 1.7; }
.core-name { font-size: 0.8rem; color: #888; margin: 0.5rem 0 0; }

.probe-row { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.probe-row label { font-size: 0.875rem; display: flex; align-items: center; gap: 0.4rem; }
.count-input { width: 60px; border: 1px solid #ccc; border-radius: 4px; padding: 0.3rem 0.5rem; font-size: 0.875rem; }

.probe-summary { font-size: 0.875rem; color: #555; margin-bottom: 0.75rem; line-height: 1.6; }
.album-snippet { border: 1px solid #eee; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; }
.album-title { font-weight: 600; font-size: 0.9rem; }
.album-sub { font-size: 0.8rem; color: #666; }

.raw-json { margin-top: 1rem; }
.raw-json summary { cursor: pointer; font-size: 0.875rem; color: #4a6cf7; user-select: none; }
.raw-json pre {
  margin-top: 0.5rem;
  background: #1a1a2e;
  color: #e0e0e0;
  padding: 1rem;
  border-radius: 6px;
  font-size: 0.78rem;
  overflow-x: auto;
  max-height: 500px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Files path input */
.path-row { display: flex; gap: 0.5rem; align-items: center; }
.path-input {
  flex: 1;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  font-size: 0.9rem;
  font-family: monospace;
}
.path-input:disabled { background: #f5f5f5; color: #aaa; }

/* Collection picker */
.collection-row {
  display: flex; align-items: center; gap: 0.75rem;
  font-size: 0.875rem; margin-bottom: 1rem; flex-wrap: wrap;
}
.collection-select {
  border: 1px solid #ccc; border-radius: 4px;
  padding: 0.3rem 0.5rem; font-size: 0.875rem; min-width: 200px;
}

/* Import/scan section */
.import-actions { display: flex; flex-direction: column; gap: 0.5rem; }
.btn-import {
  background: #27ae60; color: #fff; border: none; border-radius: 4px;
  padding: 0.55rem 1.5rem; cursor: pointer; font-size: 1rem; font-weight: 600;
  align-self: flex-start;
}
.btn-import:disabled { opacity: 0.5; cursor: not-allowed; }

.progress-block { display: flex; flex-direction: column; gap: 0.6rem; }
.progress-header { display: flex; align-items: center; justify-content: space-between; font-size: 0.9rem; }

.progress-bar-track {
  height: 10px;
  background: #e8e8e8;
  border-radius: 5px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: #4a6cf7;
  border-radius: 5px;
  transition: width 0.4s ease;
}
.progress-bar-fill.fill--done { background: #27ae60; }

.progress-stats { display: flex; gap: 1.25rem; font-size: 0.875rem; flex-wrap: wrap; }
.stat { font-weight: 600; }
.stat--green { color: #27ae60; }
.stat--amber { color: #d68910; }
.stat--grey { color: #888; }
.stat--red { color: #e74c3c; }

.import-summary { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0.75rem; }
.summary-done { color: #27ae60; font-weight: 600; margin: 0; }
.summary-cancelled { color: #888; font-weight: 600; margin: 0; }
.summary-error { color: #e74c3c; font-weight: 600; margin: 0; }

.error-details { margin-top: 0.75rem; }
.error-details summary { cursor: pointer; font-size: 0.875rem; color: #e74c3c; user-select: none; }
.error-list {
  margin: 0.5rem 0 0 1rem;
  padding: 0;
  font-size: 0.8rem;
  color: #555;
  line-height: 1.7;
}

.error { color: #c0392b; font-size: 0.875rem; margin-top: 0.5rem; }
</style>
