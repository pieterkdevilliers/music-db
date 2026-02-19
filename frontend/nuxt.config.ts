// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: true },
  devServer: { host: "0.0.0.0", port: 3003 },
  routeRules: {
    "/login": { appMiddleware: false },
    "/register": { appMiddleware: false },
  },
  modules: ["@pinia/nuxt"],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8003",
    },
  },
});
