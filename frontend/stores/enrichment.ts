import { defineStore } from 'pinia'

interface EnrichmentJob {
  status: string
  total: number
  done: number
  enriched: number
  skipped: number
  errors: number
  error_list: string[]
  cancel_requested: boolean
  current_album: string | null
}

const IDLE_JOB: EnrichmentJob = {
  status: 'idle',
  total: 0,
  done: 0,
  enriched: 0,
  skipped: 0,
  errors: 0,
  error_list: [],
  cancel_requested: false,
  current_album: null,
}

export const useEnrichmentStore = defineStore('enrichment', {
  state: () => ({
    job: { ...IDLE_JOB } as EnrichmentJob,
    _pollTimer: null as ReturnType<typeof setInterval> | null,
  }),

  actions: {
    async enrichAlbum(albumId: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/enrichment/album/${albumId}`, { method: 'POST' })
      await this.pollProgress()
      this.startPolling()
    },

    async enrichCollection(collectionId: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/enrichment/collection/${collectionId}`, { method: 'POST' })
      await this.pollProgress()
      this.startPolling()
    },

    async pollProgress() {
      const { apiFetch } = useApi()
      try {
        this.job = await apiFetch<EnrichmentJob>('/enrichment/progress')
      } catch {
        // ignore transient errors
      }
      if (!['running', 'starting'].includes(this.job.status)) {
        this.stopPolling()
      }
    },

    startPolling() {
      if (this._pollTimer) return
      this._pollTimer = setInterval(() => this.pollProgress(), 2000)
    },

    stopPolling() {
      if (this._pollTimer) {
        clearInterval(this._pollTimer)
        this._pollTimer = null
      }
    },

    async cancel() {
      const { apiFetch } = useApi()
      try {
        await apiFetch('/enrichment/cancel', { method: 'POST' })
      } catch {
        // ignore
      }
    },

    reset() {
      this.stopPolling()
      this.job = { ...IDLE_JOB }
    },
  },
})
