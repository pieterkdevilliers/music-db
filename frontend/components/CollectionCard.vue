<template>
  <NuxtLink :to="`/collections/${collection.id}`" class="card">
    <h3>{{ collection.name }}</h3>
    <p v-if="collection.description" class="desc">{{ collection.description }}</p>
    <span class="meta">{{ albumCount }} album{{ albumCount !== 1 ? 's' : '' }}</span>
  </NuxtLink>
</template>

<script setup lang="ts">
const props = defineProps<{
  collection: {
    id: number
    name: string
    description?: string | null
    albums?: unknown[]
  }
}>()

const albumCount = computed(() => props.collection.albums?.length ?? 0)
</script>

<style scoped>
.card {
  display: block;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s;
}
.card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
h3 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
}
.desc {
  color: #666;
  font-size: 0.875rem;
  margin: 0 0 0.5rem;
}
.meta {
  font-size: 0.75rem;
  color: #999;
}
</style>
