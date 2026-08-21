import axios from 'axios'

/** Base URL is relative so the Vite dev proxy (and any reverse proxy) handles routing. */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
})

let getToken: () => string | null = () => null
let onUnauthorized: () => void = () => {}

/** Wired up once by AuthProvider so this module stays free of React imports. */
export function configureAuthHandlers(opts: {
  getToken: () => string | null
  onUnauthorized: () => void
}) {
  getToken = opts.getToken
  onUnauthorized = opts.onUnauthorized
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status
    const url: string = error?.config?.url ?? ''
    // An expired/invalid token means sign out — but a failed login attempt is not that.
    if (status === 401 && !url.includes('/auth/login') && !url.includes('/auth/signup')) {
      onUnauthorized()
    }
    return Promise.reject(error)
  },
)
