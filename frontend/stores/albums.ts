import { defineStore } from 'pinia'

export interface AlbumMusicianInput {
  musician_name: string
  instrument: string
}

export interface AlbumCreate {
  title: string
  artist: string
  release_year?: number | null
  producer?: string | null
  record_label?: string | null
  tracks: string[]
  musicians: AlbumMusicianInput[]
  collection_id?: number | null
}

export interface Album {
  id: number
  title: string
  artist: string
  release_year: number | null
  producer: string | null
  record_label: string | null
  tracks: string[]
  musicians: { musician: { id: number; name: string }; instrument: string }[]
  created_at: string
}

interface AlbumFilters {
  musician_id?: number
  instrument?: string
  artist?: string
  label?: string
  search?: string
}

export const useAlbumsStore = defineStore('albums', {
  state: () => ({
    albums: [] as Album[],
    current: null as Album | null,
    filters: {} as AlbumFilters,
  }),

  actions: {
    async fetchAlbums(filters?: AlbumFilters) {
      const { apiFetch } = useApi()
      const params = new URLSearchParams()
      const f = filters ?? this.filters
      if (f.musician_id) params.set('musician_id', String(f.musician_id))
      if (f.instrument) params.set('instrument', f.instrument)
      if (f.artist) params.set('artist', f.artist)
      if (f.label) params.set('label', f.label)
      if (f.search) params.set('search', f.search)
      const qs = params.toString()
      this.albums = await apiFetch<Album[]>(`/albums${qs ? '?' + qs : ''}`)
    },

    async fetchAlbum(id: number) {
      const { apiFetch } = useApi()
      this.current = await apiFetch<Album>(`/albums/${id}`)
    },

    async createAlbum(payload: AlbumCreate) {
      const { apiFetch } = useApi()
      const { collection_id, ...albumData } = payload
      const album = await apiFetch<Album>('/albums', {
        method: 'POST',
        body: albumData,
      })
      if (collection_id) {
        const collectionsStore = useCollectionsStore()
        await collectionsStore.addAlbum(collection_id, album.id)
      }
      this.albums.unshift(album)
      return album
    },

    async updateAlbum(id: number, payload: Partial<AlbumCreate>) {
      const { apiFetch } = useApi()
      const { collection_id: _ignored, ...albumData } = payload
      const updated = await apiFetch<Album>(`/albums/${id}`, {
        method: 'PATCH',
        body: albumData,
      })
      const idx = this.albums.findIndex((a) => a.id === id)
      if (idx !== -1) this.albums[idx] = updated
      if (this.current?.id === id) this.current = updated
      return updated
    },

    async deleteAlbum(id: number) {
      const { apiFetch } = useApi()
      await apiFetch(`/albums/${id}`, { method: 'DELETE' })
      this.albums = this.albums.filter((a) => a.id !== id)
      if (this.current?.id === id) this.current = null
    },
  },
})
