export const useApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  const apiFetch = $fetch.create({
    baseURL,
    onRequest({ options }) {
      const token = import.meta.client ? localStorage.getItem('auth_token') : null
      if (token) {
        options.headers = {
          ...options.headers,
          Authorization: `Bearer ${token}`,
        }
      }
    },
    async onResponseError({ response }) {
      if (response.status === 401) {
        if (import.meta.client) {
          localStorage.removeItem('auth_token')
        }
        await navigateTo('/login')
      }
    },
  })

  return { apiFetch, baseURL }
}
