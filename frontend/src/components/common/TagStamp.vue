<template>
  <span class="stamp" :class="[`stamp--${tone}`, { 'stamp--inferred': source === 'inferred' }]">
    <span class="stamp__name">{{ tagName }}</span>
    <span class="stamp__meta">{{ sourceLabel }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TAG_SOURCE_LABELS } from '../../constants/enums'

const props = defineProps<{ tagName: string; source?: string; animate?: boolean }>()
const tone = computed(() => {
  if (props.tagName.startsWith('sensitive:high')) return 'high'
  if (props.tagName.startsWith('sensitive:')) return 'mid'
  if (props.tagName.startsWith('pii:')) return 'info'
  if (props.tagName.startsWith('business:')) return 'biz'
  return 'gov'
})
const sourceLabel = computed(() => TAG_SOURCE_LABELS[props.source ?? 'manual'] ?? '人工')
</script>

<style scoped>
.stamp {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 2px 8px;
  border: 1.5px solid currentColor;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transform: rotate(-1.2deg);
  animation: stamp-in 460ms var(--ease) both;
}
.stamp__meta {
  font-size: 8.5px;
  opacity: 0.7;
  border-left: 1px dashed currentColor;
  padding-left: 6px;
}
.stamp--high {
  color: var(--brick);
  background: color-mix(in oklch, var(--brick-wash) 65%, transparent);
}
.stamp--mid {
  color: var(--brick-soft);
}
.stamp--info {
  color: var(--moss);
}
.stamp--biz {
  color: var(--ink-soft);
}
.stamp--gov {
  color: var(--gold);
}
.stamp--inferred {
  border-style: dashed;
}
@keyframes stamp-in {
  0% {
    opacity: 0;
    transform: rotate(-8deg) scale(1.6);
  }
  100% {
    opacity: 1;
    transform: rotate(-1.2deg) scale(1);
  }
}
</style>
