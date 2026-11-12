import { http } from './http'
import type { Overview } from '../types/models'

export async function fetchOverview() {
  const { data } = await http.get('/meta/overview')
  return data as Overview
}

export async function fetchAuditLogs(limit = 50) {
  const { data } = await http.get('/audit', { params: { limit } })
  return data as { items: Record<string, string>[] }
}
