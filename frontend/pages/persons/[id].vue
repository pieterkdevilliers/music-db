<template>
  <main class="page">
    <div v-if="person">
      <h1>{{ person.name }}</h1>

      <div class="section">
        <h2>Credits</h2>
        <table v-if="albums.length" class="disc-table">
          <thead>
            <tr><th>Album</th><th>Artist</th><th>Year</th><th>Role(s)</th></tr>
          </thead>
          <tbody>
            <tr v-for="entry in albums" :key="entry.album.id">
              <td>
                <NuxtLink :to="`/albums/${entry.album.id}`">{{ entry.album.title }}</NuxtLink>
              </td>
              <td>{{ entry.album.artist }}</td>
              <td>{{ entry.album.release_year ?? '—' }}</td>
              <td>{{ entry.roles.join(', ') }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty">No albums found for this person.</p>
      </div>
    </div>
    <div v-else class="empty">Loading…</div>
  </main>
</template>

<script setup lang="ts">
const route = useRoute()
const { apiFetch } = useApi()
const id = Number(route.params.id)

interface AlbumSummary {
  id: number
  title: string
  artist: string
  release_year: number | null
}

interface PersonDetail {
  id: number
  name: string
}

const person = ref<PersonDetail | null>(null)
const albums = ref<{ album: AlbumSummary; roles: string[] }[]>([])

onMounted(async () => {
  const data = await apiFetch<{ person: PersonDetail; albums: { album: AlbumSummary; roles: string[] }[] }>(
    `/persons/${id}`
  )
  person.value = data.person
  albums.value = data.albums
})
</script>

<style scoped>
.page { padding: 1.5rem; max-width: 720px; }
h1 { margin: 0 0 1.5rem; font-size: 1.5rem; }
.section { margin-bottom: 1.5rem; }
h2 { font-size: 1rem; font-weight: 600; margin: 0 0 0.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.25rem; }
.disc-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
.disc-table th { text-align: left; padding: 0.35rem 0.5rem; border-bottom: 2px solid #eee; font-size: 0.8rem; color: #777; }
.disc-table td { padding: 0.35rem 0.5rem; border-bottom: 1px solid #f0f0f0; }
.disc-table a { color: #4a6cf7; text-decoration: none; }
.empty { color: #888; }
</style>
