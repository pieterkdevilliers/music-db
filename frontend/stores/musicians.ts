import { defineStore } from 'pinia'
import type { Album } from './albums'

interface Musician {
  id: number
  name: string
}

interface MusicianDetail {
  musician: Musician
  albums: { album: Album; instruments: string[] }[]
}

export const useMusiciansStore = defineStore('musicians', {
  state: () => ({
    musicians: [] as Musician[],
    current: null as MusicianDetail | null,
  }),

  actions: {
    async search(query: string) {
      const { apiFetch } = useApi()
      this.musicians = await apiFetch<Musician[]>(
        `/musicians?search=${encodeURIComponent(query)}`
      )
    },

    async fetchOne(id: number) {
      const { apiFetch } = useApi()
      this.current = await apiFetch<MusicianDetail>(`/musicians/${id}`)
    },
  },
})
