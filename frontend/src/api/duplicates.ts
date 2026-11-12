import { http } from './http'
import type { SimilarityPair } from '../types/models'

export async function fetchPairs(limit = 5) {
  const { data } = await http.get('/duplicates', { params: { limit } })
  return data as {
    items: SimilarityPair[]
    total: number
    recommended_total: number
    dismissed_total: number
    true_duplicate_total: number
  }
}

export async function recomputePairs(topN = 6) {
  const { data } = await http.post('/duplicates/recompute', { top_n: topN, min_score: 0.45 })
  return data
}

export async function fetchPair(pairId: string) {
  const { data } = await http.get(`/duplicates/${pairId}`)
  return data as SimilarityPair
}

export async function generateMergeSuggestion(pairId: string) {
  const { data } = await http.post(`/duplicates/${pairId}/merge-suggestion`)
  return data
}

export async function dismissPair(pairId: string, note = '人工确认非重复') {
  const { data } = await http.post(`/duplicates/${pairId}/dismiss`, { note })
  return data
}
