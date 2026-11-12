import { defineStore } from 'pinia'
import { fetchOverview } from '../api/meta'
import type { Overview } from '../types/models'

export const useCatalogStore = defineStore('catalog', {
  state: () => ({
    overview: null as Overview | null,
    loaded: false,
  }),
  actions: {
    async refresh() {
      try {
        this.overview = await fetchOverview()
        this.loaded = true
      } catch {
        this.loaded = false
      }
    },
  },
})
