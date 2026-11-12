import type { Router } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

let restored = false

export function setupGuards(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    if (!restored && auth.token) {
      restored = true
      await auth.restore()
    }
    if (to.meta.public) {
      if (auth.isAuthenticated && to.path === '/login') return { path: '/assets' }
      return true
    }
    if (!auth.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    return true
  })
}
