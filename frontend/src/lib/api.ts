import axios from 'axios'

/** Base URL is relative so the Vite dev proxy (and any reverse proxy) handles routing. */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
})
