const PUBLIC_ROUTES = ['/login', '/register']

export default defineNuxtRouteMiddleware((to) => {
  const token = import.meta.client ? localStorage.getItem('auth_token') : null
  if (!token && !PUBLIC_ROUTES.includes(to.path)) {
    return navigateTo('/login')
  }
})
