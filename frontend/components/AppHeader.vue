<template>
  <header class="app-header">
    <nav>
      <NuxtLink to="/collections" class="brand">Music DB</NuxtLink>
      <div class="nav-links">
        <NuxtLink to="/collections">Collections</NuxtLink>
        <NuxtLink to="/albums">Albums</NuxtLink>
        <NuxtLink to="/import">Import</NuxtLink>
      </div>
      <div class="user-menu" v-if="authStore.isAuthenticated">
        <span class="user-email">{{ authStore.user?.email }}</span>
        <button @click="authStore.logout()">Logout</button>
      </div>
    </nav>
  </header>
</template>

<script setup lang="ts">
const authStore = useAuthStore()
</script>

<style scoped>
.app-header {
  background: #1a1a2e;
  color: #fff;
  padding: 0 1.5rem;
}
nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  height: 3.5rem;
}
.brand {
  font-weight: 700;
  font-size: 1.1rem;
  color: #e94560;
  text-decoration: none;
}
.nav-links {
  display: flex;
  gap: 1rem;
}
.nav-links a {
  color: #ccc;
  text-decoration: none;
}
.nav-links a:hover {
  color: #fff;
}
.user-menu {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.user-email {
  font-size: 0.875rem;
  color: #aaa;
}
button {
  background: #e94560;
  color: #fff;
  border: none;
  padding: 0.3rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
}
</style>
