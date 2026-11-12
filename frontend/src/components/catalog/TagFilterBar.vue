<template>
  <div class="tagbar">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="tagbar__item"
      :class="{ 'is-active': modelValue === option.value }"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
      <span v-if="option.count !== undefined" class="numeric">{{ option.count }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  options: { value: string; label: string; count?: number }[]
}>()
defineEmits<{ (event: 'update:modelValue', value: string): void }>()
</script>

<style scoped>
.tagbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tagbar__item {
  border: 1px solid var(--line);
  background: transparent;
  padding: 3px 9px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.05em;
  color: var(--ink-soft);
  border-radius: var(--radius-sm);
  display: inline-flex;
  gap: 6px;
  transition: all 160ms var(--ease);
}
.tagbar__item:hover {
  border-color: var(--ink);
  color: var(--ink);
}
.tagbar__item.is-active {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--sand);
}
</style>
