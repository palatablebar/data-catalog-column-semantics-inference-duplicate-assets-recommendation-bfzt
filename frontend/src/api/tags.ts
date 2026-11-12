import { http } from './http'
import type { TagRow } from '../types/models'

export async function fetchTags(params: { category?: string; source?: string; q?: string } = {}) {
  const { data } = await http.get('/tags', { params })
  return data as {
    items: TagRow[]
    total: number
    summary: { by_category: Record<string, number>; by_source: Record<string, number>; sensitive_columns: number }
  }
}

export async function createTag(columnId: string, tagName: string, category = 'pii') {
  const { data } = await http.post('/tags', { column_id: columnId, tag_name: tagName, category })
  return data
}

export async function bulkTag(columnIds: string[], tagName: string, category = 'pii') {
  const { data } = await http.post('/tags/bulk', { column_ids: columnIds, tag_name: tagName, category })
  return data
}
