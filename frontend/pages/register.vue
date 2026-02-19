<template>
  <main class="auth-page">
    <div class="auth-card">
      <h1>Create Account</h1>
      <form @submit.prevent="submit">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" required autocomplete="email" />
        </div>
        <div class="field">
          <label>Password <small>(min 8 characters)</small></label>
          <input v-model="password" type="password" required autocomplete="new-password" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Creating account…' : 'Register' }}
        </button>
      </form>
      <p class="switch">Already have an account? <NuxtLink to="/login">Sign in</NuxtLink></p>
    </div>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ middleware: [] })  // public route

const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.register(email.value, password.value)
    await navigateTo('/collections')
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    error.value = err?.data?.detail ?? 'Registration failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}
.auth-card {
  background: #fff;
  border-radius: 8px;
  padding: 2rem;
  width: 360px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.08);
}
h1 { margin: 0 0 1.5rem; font-size: 1.4rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 1rem; }
label { font-size: 0.85rem; font-weight: 500; color: #555; }
small { font-weight: 400; color: #888; }
input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.45rem 0.6rem;
  font-size: 0.9rem;
}
button {
  width: 100%;
  background: #4a6cf7;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.6rem;
  font-size: 0.95rem;
  cursor: pointer;
  margin-top: 0.5rem;
}
button:disabled { opacity: 0.6; }
.error { color: #c0392b; font-size: 0.85rem; margin-bottom: 0.5rem; }
.switch { text-align: center; font-size: 0.875rem; margin-top: 1rem; }
</style>
