<template>
  <span class="simbar" :class="{ 'is-hot': score >= 0.85 }">
    <span class="simbar__track">
      <span class="simbar__fill" :style="{ '--score': String(clamped) }"></span>
      <span class="simbar__scan"></span>
    </span>
    <span class="simbar__text numeric">{{ score.toFixed(3) }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ score: number }>()
const clamped = computed(() => Math.max(0, Math.min(1, props.score ?? 0)))
</script>

<style scoped>
.simbar {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.simbar__track {
  position: relative;
  flex: 1;
  height: 7px;
  border: 1px solid var(--line);
  background: repeating-linear-gradient(
    90deg,
    transparent 0 6px,
    color-mix(in oklch, var(--line) 55%, transparent) 6px 7px
  );
  overflow: hidden;
}
.simbar__fill {
  position: absolute;
  inset: 0;
  transform-origin: left center;
  transform: scaleX(var(--score));
  background: color-mix(in oklch, var(--moss) 72%, var(--ink));
  transition: transform 700ms var(--ease-scan);
}
.is-hot .simbar__fill {
  background: var(--brick);
}
.simbar__scan {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, color-mix(in oklch, var(--sand-raise) 70%, transparent) 50%, transparent 100%);
  transform: translateX(-110%);
  animation: scan 2.6s var(--ease) infinite;
}
.simbar__text {
  width: 42px;
  text-align: right;
  font-size: 11px;
  color: var(--ink);
}
@keyframes scan {
  0% {
    transform: translateX(-110%);
  }
  55%,
  100% {
    transform: translateX(110%);
  }
}
</style>
