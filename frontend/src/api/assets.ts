import { http } from './http'
import type { AssetDetail, AssetListItem, Facets } from '../types/models'
import type { PageResult } from '../types/api'

export interface AssetQuery {
  layer?: string
  domain?: string
  q?: string
  source_kind?: string
  page?: number
  page_size?: number
}

export async function fetchFacets() {
  const { data } = await http.get('/assets/facets')
  return data as Facets
}

export async function fetchAssets(params: AssetQuery) {
  const { data } = await http.get('/assets', { params })
  return data as PageResult<AssetListItem>
}

export async function fetchAsset(assetId: string) {
  const { data } = await http.get(`/assets/${assetId}`)
  return data as AssetDetail
}

export async function exportCatalogCsv() {
  const response = await http.get('/assets/export.csv', { responseType: 'blob' })
  return response
}
