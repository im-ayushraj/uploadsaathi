import { z } from 'zod'
import { api } from './api'

export const healthSchema = z.object({
  status: z.string(),
  app: z.string(),
  version: z.string(),
  env: z.string(),
  database: z.string(),
  prototype_notice: z.string(),
})

export type Health = z.infer<typeof healthSchema>

export async function fetchHealth(): Promise<Health> {
  const { data } = await api.get('/health')
  return healthSchema.parse(data)
}
