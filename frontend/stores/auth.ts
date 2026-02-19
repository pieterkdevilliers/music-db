import { defineStore } from 'pinia'

interface User {
  id: number
  email: string
  created_at: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null as string | null,
    user: null as User | null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    init() {
      if (import.meta.client) {
        this.token = localStorage.getItem('auth_token')
      }
    },

    async fetchMe() {
      if (!this.token) return
      const { apiFetch } = useApi()
      try {
        this.user = await apiFetch<User>('/auth/me')
      } catch {
        this.logout()
      }
    },

    async login(email: string, password: string) {
      const { baseURL } = useApi()
      const form = new URLSearchParams()
      form.set('username', email)
      form.set('password', password)

      const data = await $fetch<{ access_token: string }>(`${baseURL}/auth/login`, {
        method: 'POST',
        body: form.toString(),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      this.token = data.access_token
      if (import.meta.client) {
        localStorage.setItem('auth_token', this.token)
      }
      await this.fetchMe()
    },

    async register(email: string, password: string) {
      const { apiFetch } = useApi()
      await apiFetch('/auth/register', {
        method: 'POST',
        body: { email, password },
      })
      await this.login(email, password)
    },

    logout() {
      this.token = null
      this.user = null
      if (import.meta.client) {
        localStorage.removeItem('auth_token')
      }
      navigateTo('/login')
    },
  },
})
