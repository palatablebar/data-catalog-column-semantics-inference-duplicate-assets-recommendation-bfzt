export interface ApiError {
  code: string
  message: string
  detail?: string
  traceId?: string | null
  status?: number
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
