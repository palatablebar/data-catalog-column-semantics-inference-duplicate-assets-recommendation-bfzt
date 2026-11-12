<template>
  <span class="role-badge" :class="`role-badge--${role}`">
    <span class="role-badge__dot"></span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Role } from '../../types/models'
import { ROLE_LABELS } from '../../constants/enums'

const props = defineProps<{ role: Role }>()
const label = computed(() => ROLE_LABELS[props.role] ?? props.role)
</script>

<style scoped>
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--ink-soft);
}
.role-badge__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--moss);
}
.role-badge--admin .role-badge__dot {
  background: var(--brick);
}
.role-badge--analyst .role-badge__dot {
  background: var(--moss);
}
.role-badge--viewer .role-badge__dot {
  background: var(--gold);
}
</style>
