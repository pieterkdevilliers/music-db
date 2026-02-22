import { defineStore } from 'pinia'

// Matches AlbumSummary from the backend
interface AlbumSummary {
  id: number
  title: string
  artist: string
  release_year: number | null
  record_label: string | null
}

interface Collection {
  id: number
  user_id: number
  name: string
  description: string | null
  created_at: string
  albums: AlbumSummary[]
}

export const useCollectionsStore = defineStore('collections', {
  state: () => ({
    collections: [] as Collection[],
    current: null as Collection | null,
  }),

  actions: {
    async fetchCollections() {
      const { apiFetch } = useApi()
      this.collections = await apiFetch<Collection[]>('/collections')
    },

    async fetchCollection(id: number) {
      const { apiFetch } = useApi()
      this.current = await apiFetch<Collection>(`/collections/${id}`)
      // Keep the matching entry in collections list in sync
      const idx = this.collections.findIndex((c) => c.id === id)
      if (idx !== -1 && this.current) {
        this.collections[idx] = this.current
      }
    },

    async createCollection(name: string, description?: string) {
      const { apiFetch } = useApi()
      const collection = await apiFetch<Collection>('/collections', {
        method: 'POST',
        body: { name, description },
      })
      this.collections.push(collection)
      return collection
    },

    async updateCollection(id: number, payload: { name?: string; description?: string }) {
      const { apiFetch } = useApi()
      const updated = await apiFetch<Collection>(`/collections/${id}`, {
        method: 'PATCH',
        body: payload,
      })
      const idx = this.collections.findIndex((c) => c.id === id)
      if (idx !== -1) this.collections[idx] = updated
      if (this.current?.id === id) this.current = updated
      return updated
    },

    async deleteCollection(id: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/collections/${id}`, { method: 'DELETE' })
      this.collections = this.collections.filter((c) => c.id !== id)
      if (this.current?.id === id) this.current = null
    },

    async addAlbum(collectionId: number, albumId: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/collections/${collectionId}/albums/${albumId}`, {
        method: 'POST',
      })
      await this.fetchCollection(collectionId)
    },

    async deleteAllAlbums(collectionId: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/collections/${collectionId}/albums`, { method: 'DELETE' })
      if (this.current?.id === collectionId) {
        this.current.albums = []
      }
      const idx = this.collections.findIndex((c) => c.id === collectionId)
      if (idx !== -1) {
        this.collections[idx] = { ...this.collections[idx], albums: [] }
      }
    },

    async removeAlbum(collectionId: number, albumId: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/collections/${collectionId}/albums/${albumId}`, {
        method: 'DELETE',
      })
      // Update both current and the collections list
      const filter = (albums: AlbumSummary[]) => albums.filter((a) => a.id !== albumId)
      if (this.current?.id === collectionId) {
        this.current.albums = filter(this.current.albums)
      }
      const idx = this.collections.findIndex((c) => c.id === collectionId)
      if (idx !== -1) {
        this.collections[idx] = { ...this.collections[idx], albums: filter(this.collections[idx].albums) }
      }
    },
  },
})
