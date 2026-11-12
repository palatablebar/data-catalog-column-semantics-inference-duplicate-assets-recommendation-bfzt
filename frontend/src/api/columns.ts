import { http } from './http'
import type { ColumnItem } from '../types/models'
import type { PageResult } from '../types/api'

export interface ColumnQuery {
  inferred_type?: string
  layer?: string
  q?: string
  only_profiled?: boolean
  page?: number
  page_size?: number
}

export async function fetchColumnSummary() {
  const { data } = await http.get('/columns/summary')
  return data
}

export async function fetchColumns(params: ColumnQuery) {
  const { data } = await http.get('/columns', { params })
  return data as PageResult<ColumnItem>
}

export async function fetchColumn(columnId: string) {
  const { data } = await http.get(`/columns/${columnId}`)
  return data as ColumnItem
}

export async function inferColumns() {
  const { data } = await http.post('/columns/infer')
  return data as { processed: number; updated: number; by_type: Record<string, number>; human_corrected: number }
}

export async function correctColumnType(columnId: string, inferred_type: string, note = '') {
  const { data } = await http.patch(`/columns/${columnId}/type`, { inferred_type, note })
  return data
}
