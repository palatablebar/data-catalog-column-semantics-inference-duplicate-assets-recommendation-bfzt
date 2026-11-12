<template>
  <header class="page-header">
    <div class="page-header__titles">
      <p class="smallcaps page-header__eyebrow">{{ eyebrow }}</p>
      <h2 class="page-header__title">{{ title }}</h2>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; eyebrow?: string; subtitle?: string }>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 0 0 12px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 16px;
}
.page-header__eyebrow {
  color: var(--ink-faint);
  margin-bottom: 2px;
}
.page-header__title {
  font-size: clamp(22px, 2.2vw, 30px);
  line-height: 1.1;
}
.page-header__subtitle {
  margin-top: 5px;
  color: var(--ink-soft);
  font-size: 12px;
  max-width: 62ch;
}
.page-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
</style>
