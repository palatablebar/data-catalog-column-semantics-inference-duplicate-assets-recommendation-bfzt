import { defineStore } from 'pinia'
import { fetchMe, login as apiLogin } from '../api/auth'
import type { User } from '../types/models'
import { TOKEN_KEY } from '../utils/http'

interface AuthState {
  token: string
  user: User | null
  loading: boolean
  error: string
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY) ?? '',
    user: null,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token),
    role: (state) => state.user?.role ?? 'viewer',
    displayName: (state): string => state.user?.display_name ?? '',
    initials: (state): string => (state.user?.display_name ?? '?').slice(0, 1),
  },
  actions: {
    async login(email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await apiLogin(email, password)
        this.token = result.token
        this.user = result.user
        localStorage.setItem(TOKEN_KEY, result.token)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async restore() {
      if (!this.token) return
      try {
        const result = await fetchMe()
        this.user = result.user
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
