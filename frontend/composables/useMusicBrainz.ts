export interface MBCandidate {
  mbid: string
  title: string
  artist: string
  year: number | null
  label: string | null
  country: string | null
  track_count: number
}

export interface MBRelease {
  mbid: string
  title: string
  artist: string
  year: number | null
  label: string | null
  tracks: string[]
}

export function useMusicBrainz() {
  const { apiFetch } = useApi()

  async function searchReleases(title: string, artist: string): Promise<MBCandidate[]> {
    return apiFetch<MBCandidate[]>('/musicbrainz/search', {
      params: { title, artist },
    })
  }

  async function getRelease(mbid: string): Promise<MBRelease> {
    return apiFetch<MBRelease>(`/musicbrainz/release/${mbid}`)
  }

  return { searchReleases, getRelease }
}
