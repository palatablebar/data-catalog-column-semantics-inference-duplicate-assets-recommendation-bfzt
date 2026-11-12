import { http } from './http'
import type { IngestJob } from '../types/models'

export async function fetchJobs(limit = 20) {
  const { data } = await http.get('/ingest/jobs', { params: { limit } })
  return data as { items: IngestJob[]; total: number; counts: Record<string, number> }
}

export async function fetchJob(jobId: string) {
  const { data } = await http.get(`/ingest/jobs/${jobId}`)
  return data as IngestJob
}

export async function runIngest() {
  const { data } = await http.post('/ingest/jobs', {
    job_name: '样例表列统计采集',
    connection_name: 'pg-catmap-sample',
    scope: '5 张样例数据表 · 48 列',
  })
  return data as IngestJob
}

export async function fetchIngestOverview() {
  const { data } = await http.get('/ingest/overview')
  return data
}

export async function fetchMetaOverview() {
  const { data } = await http.get('/meta/overview')
  return data
}
