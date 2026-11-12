import { computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { can } from '../utils/permission'

export function usePermission() {
  const auth = useAuthStore()
  const role = computed(() => auth.user?.role)
  return {
    role,
    can: (action: string) => can(role.value, action),
  }
}
