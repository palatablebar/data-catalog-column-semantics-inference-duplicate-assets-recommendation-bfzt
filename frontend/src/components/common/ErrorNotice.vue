<template>
  <div v-if="message" class="error-notice" role="alert">
    {{ message }}
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ message: string }>()
</script>
