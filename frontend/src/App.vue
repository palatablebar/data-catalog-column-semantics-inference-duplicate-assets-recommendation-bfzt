<template>
  <AtlasShell v-if="!isPublic"><router-view /></AtlasShell>
  <router-view v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AtlasShell from './components/common/AtlasShell.vue'

const route = useRoute()
const isPublic = computed(() => Boolean(route.meta.public))
</script>
