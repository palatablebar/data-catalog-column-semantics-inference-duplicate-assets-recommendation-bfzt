import { http } from './http'
import type { User } from '../types/models'

export async function login(email: string, password: string) {
  const { data } = await http.post('/auth/login', { email, password })
  return data as { token: string; user: User }
}

export async function fetchMe() {
  const { data } = await http.get('/auth/me')
  return data as { user: User }
}
