import { computed, ref } from 'vue'
import { fetchFacets } from '../api/assets'
import type { Facets } from '../types/models'

export function useAssetTree() {
  const facets = ref<Facets | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function load() {
    loading.value = true
    error.value = ''
    try {
      facets.value = await fetchFacets()
    } catch (err) {
      error.value = (err as { message?: string }).message ?? '读取资产树失败'
    } finally {
      loading.value = false
    }
  }

  const layers = computed(() => facets.value?.layers ?? [])
  const domains = computed(() => facets.value?.domains ?? [])
  const stats = computed(() => facets.value?.stats ?? null)
  return { facets, layers, domains, stats, loading, error, load }
}
