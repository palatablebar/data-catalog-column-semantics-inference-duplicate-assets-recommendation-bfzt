<template>
  <span class="jobtag" :class="`jobtag--${status}`">
    <span class="jobtag__dot"></span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { JOB_STATUS_LABELS } from '../../constants/enums'

const props = defineProps<{ status: string }>()
const label = computed(() => JOB_STATUS_LABELS[props.status] ?? props.status)
</script>

<style scoped>
.jobtag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
}
.jobtag__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--line);
}
.jobtag--completed {
  color: var(--moss);
}
.jobtag--completed .jobtag__dot {
  background: var(--moss);
}
.jobtag--running {
  color: var(--gold);
}
.jobtag--running .jobtag__dot {
  background: var(--gold);
  animation: pulse 1.4s var(--ease) infinite;
}
.jobtag--failed {
  color: var(--brick);
}
.jobtag--failed .jobtag__dot {
  background: var(--brick);
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.4;
    transform: scale(0.7);
  }
}
</style>
