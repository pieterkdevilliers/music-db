<template>
  <div class="details-tag-input">
    <div class="tags">
      <div v-for="(entry, i) in modelValue" :key="i" class="tag">
        <span>{{ entry.detail_name }} — {{ entry.detail_type }}</span>
        <button type="button" @click="remove(i)">×</button>
      </div>
    </div>
    <div class="add-row">
      <div class="autocomplete">
        <input
          v-model="nameQuery"
          placeholder="Value (e.g. Abbey Road Studios)"
          @input="onNameInput"
          @blur="closeSuggestions"
          autocomplete="off"
        />
        <ul v-if="suggestions.length" class="suggestions">
          <li
            v-for="s in suggestions"
            :key="s.id"
            @mousedown.prevent="selectSuggestion(s.name)"
          >
            {{ s.name }}
          </li>
        </ul>
      </div>
      <input v-model="typeInput" placeholder="Type (e.g. Recording Studio)" />
      <button type="button" @click="add">Add</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: { detail_name: string; detail_type: string }[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: { detail_name: string; detail_type: string }[]): void
}>()

const { apiFetch } = useApi()

const nameQuery = ref('')
const typeInput = ref('')
const suggestions = ref<{ id: number; name: string }[]>([])

async function onNameInput() {
  if (nameQuery.value.length < 1) {
    suggestions.value = []
    return
  }
  try {
    suggestions.value = await apiFetch<{ id: number; name: string }[]>(
      `/details?q=${encodeURIComponent(nameQuery.value)}`
    )
  } catch {
    suggestions.value = []
  }
}

function selectSuggestion(name: string) {
  nameQuery.value = name
  suggestions.value = []
}

function closeSuggestions() {
  setTimeout(() => { suggestions.value = [] }, 150)
}

function add() {
  const name = nameQuery.value.trim()
  const type = typeInput.value.trim()
  if (!name || !type) return
  emit('update:modelValue', [
    ...props.modelValue,
    { detail_name: name, detail_type: type },
  ])
  nameQuery.value = ''
  typeInput.value = ''
}

function remove(index: number) {
  const updated = [...props.modelValue]
  updated.splice(index, 1)
  emit('update:modelValue', updated)
}
</script>

<style scoped>
.details-tag-input { display: flex; flex-direction: column; gap: 0.5rem; }
.tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tag {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  background: #e8f5e9;
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  font-size: 0.85rem;
}
.tag button {
  background: none;
  border: none;
  cursor: pointer;
  color: #666;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
}
.add-row { display: flex; gap: 0.5rem; align-items: flex-start; flex-wrap: wrap; }
.add-row input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.35rem 0.6rem;
  font-size: 0.875rem;
}
.add-row button {
  background: #4a6cf7;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.35rem 0.75rem;
  cursor: pointer;
  font-size: 0.875rem;
}
.autocomplete { position: relative; }
.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
  z-index: 10;
  max-height: 180px;
  overflow-y: auto;
}
.suggestions li {
  padding: 0.4rem 0.6rem;
  cursor: pointer;
  font-size: 0.875rem;
}
.suggestions li:hover { background: #f0f0f0; }
</style>
