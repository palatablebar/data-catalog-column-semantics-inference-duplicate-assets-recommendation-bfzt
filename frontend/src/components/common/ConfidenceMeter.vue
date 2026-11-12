<template>
  <span class="confidence" :class="`confidence--${tone}`">
    <span class="confidence__track">
      <span class="confidence__fill" :style="{ transform: `scaleX(${clamped})` }"></span>
    </span>
    <span class="confidence__text numeric">{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { confidenceLabel, confidenceTone } from '../../utils/confidence'

const props = defineProps<{
  value: number
  type?: string | null
}>()

const clamped = computed(() => Math.max(0, Math.min(1, props.value ?? 0)))
const tone = computed(() => confidenceTone(props.value ?? 0, props.type ?? null))
const text = computed(() => confidenceLabel(props.value ?? 0))
</script>

<style scoped>
.confidence {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.confidence__track {
  position: relative;
  width: 54px;
  height: 4px;
  background: var(--line-soft);
  overflow: hidden;
}
.confidence__fill {
  position: absolute;
  inset: 0;
  transform-origin: left center;
  background: var(--moss);
  transition: transform 420ms var(--ease-scan);
}
.confidence--mid .confidence__fill {
  background: var(--gold);
}
.confidence--low .confidence__fill,
.confidence--fail .confidence__fill {
  background: var(--brick-soft);
}
.confidence__text {
  font-size: 10.5px;
  color: var(--ink-soft);
}
</style>
