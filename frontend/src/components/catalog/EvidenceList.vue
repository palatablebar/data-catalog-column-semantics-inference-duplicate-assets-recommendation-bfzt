<template>
  <ul class="evidence">
    <li v-for="(line, index) in lines" :key="index" class="evidence__item">
      <span class="evidence__index mono">{{ String(index + 1).padStart(2, '0') }}</span>
      <span class="evidence__text">{{ line }}</span>
    </li>
  </ul>
</template>

<script setup lang="ts">
defineProps<{ lines: string[] }>()
</script>

<style scoped>
.evidence {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 5px;
}
.evidence__item {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--ink-soft);
  line-height: 1.45;
}
.evidence__index {
  color: var(--brick);
  font-size: 9px;
  padding-top: 2px;
}
.evidence__text {
  min-width: 0;
  word-break: break-all;
}
</style>
