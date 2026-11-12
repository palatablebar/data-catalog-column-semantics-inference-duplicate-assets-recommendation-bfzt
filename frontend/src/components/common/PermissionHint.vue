<template>
  <span class="hint smallcaps" :title="detail">{{ label }}</span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label?: string; detail?: string }>(), {
  label: '当前角色只读',
  detail: '',
})
</script>

<style scoped>
.hint {
  color: var(--ink-faint);
  border: 1px dashed var(--line);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  cursor: help;
}
</style>
