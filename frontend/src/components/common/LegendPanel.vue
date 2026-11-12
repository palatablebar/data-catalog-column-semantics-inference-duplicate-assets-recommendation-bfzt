<template>
  <aside class="legend">
    <p class="legend__title smallcaps">{{ title }}</p>
    <ul class="legend__list">
      <li v-for="item in items" :key="item.label" class="legend__item">
        <span class="legend__swatch" :style="{ background: item.color }"></span>
        <span class="legend__label">{{ item.label }}</span>
        <span v-if="item.value !== undefined" class="legend__value numeric">{{ item.value }}</span>
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  items: { label: string; color: string; value?: string | number }[]
}>()
</script>

<style scoped>
.legend {
  border: 1px solid var(--line);
  border-left: 3px solid var(--ink);
  padding: 10px 12px;
  background: color-mix(in oklch, var(--sand-raise) 74%, transparent);
}
.legend__title {
  color: var(--ink-faint);
  margin-bottom: 8px;
}
.legend__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 5px;
}
.legend__item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
}
.legend__swatch {
  width: 9px;
  height: 9px;
  border: 1px solid color-mix(in oklch, var(--ink) 30%, transparent);
}
.legend__label {
  flex: 1;
  color: var(--ink-soft);
}
.legend__value {
  color: var(--ink);
}
</style>
