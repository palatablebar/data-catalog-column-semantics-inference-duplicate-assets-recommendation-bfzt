export interface NavItem {
  path: string
  index: string
  label: string
  hint: string
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/assets', index: '01', label: '资产检索', hint: 'ASSET INDEX' },
  { path: '/columns', index: '02', label: '列语义校验', hint: 'COLUMN SURVEY' },
  { path: '/duplicates', index: '03', label: '相似表推荐', hint: 'DUPLICATE PLATE' },
  { path: '/tags', index: '04', label: '标签与敏感', hint: 'TAG LEGEND' },
  { path: '/ingest', index: '05', label: '采集任务', hint: 'INGEST LOG' },
]
