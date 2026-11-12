<template>
  <div class="empty-state">
    <p class="smallcaps" style="color: var(--ink-faint); margin-bottom: 6px">{{ eyebrow }}</p>
    <p>{{ message }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ message: string; eyebrow?: string }>(), { eyebrow: 'SURVEY EMPTY' })
</script>
