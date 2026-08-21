import { z } from 'zod'
import { api } from './api'

const TOKEN_KEY = 'uploadsaathi.token'

export const userSchema = z.object({
  id: z.number(),
  full_name: z.string(),
  email: z.string(),
  mobile: z.string(),
  created_at: z.string(),
})

export const tokenSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  expires_in: z.number(),
  user: userSchema,
})

export type User = z.infer<typeof userSchema>
export type TokenResponse = z.infer<typeof tokenSchema>

export const signupSchema = z.object({
  full_name: z.string().trim().min(2, 'Enter your full name'),
  email: z.string().trim().email('Enter a valid email address'),
  mobile: z
    .string()
    .trim()
    .regex(/^[6-9]\d{9}$/, 'Enter a valid 10-digit mobile number'),
  password: z.string().min(8, 'Use at least 8 characters').max(64),
})

export const loginSchema = z.object({
  identifier: z.string().trim().min(3, 'Enter your email or mobile number'),
  password: z.string().min(1, 'Enter your password'),
})

export type SignupInput = z.infer<typeof signupSchema>
export type LoginInput = z.infer<typeof loginSchema>

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export async function signup(input: SignupInput): Promise<TokenResponse> {
  const { data } = await api.post('/auth/signup', input)
  return tokenSchema.parse(data)
}

export async function login(input: LoginInput): Promise<TokenResponse> {
  const { data } = await api.post('/auth/login', input)
  return tokenSchema.parse(data)
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get('/auth/me')
  return userSchema.parse(data)
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } finally {
    tokenStore.clear()
  }
}

/** Turns an axios/zod failure into a message safe to show a citizen. */
export function toErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.') {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    if (first?.msg) return first.msg.replace(/^Value error, /, '')
  }
  return fallback
}
