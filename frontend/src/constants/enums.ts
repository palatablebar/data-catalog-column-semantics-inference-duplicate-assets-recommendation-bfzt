/* 共享枚举组前端副本（后端对应 backend/src/constants/enums.ts→enums.py / roles.py）。
   README 列出全部出现位置。 */
import type { ColumnSemanticType, Role } from '../types/models'

export const ROLE_LABELS: Record<Role, string> = {
  admin: '平台管理员',
  analyst: '数据分析',
  viewer: '数据管家',
}

export const ROLE_ACTIONS: Record<Role, string[]> = {
  admin: ['采集', '推断', '纠错', '相似表', '合并', '打标', '导出'],
  analyst: ['检索', '纠错标注', '打标'],
  viewer: ['目录浏览', '敏感标签', '导出'],
}

export const COLUMN_TYPE_LABELS: Record<ColumnSemanticType, string> = {
  phone: '手机号',
  id_card: '身份证',
  email: '邮箱',
  amount: '金额',
  datetime: '日期时间',
  enum: '枚举',
  ambiguous: '待定歧义',
  unknown: '未知',
}

export const COLUMN_TYPE_ORDER: ColumnSemanticType[] = [
  'phone',
  'id_card',
  'email',
  'amount',
  'datetime',
  'enum',
  'ambiguous',
  'unknown',
]

export const LAYER_LABELS: Record<string, string> = {
  ods: 'ODS 原始层',
  dwd: 'DWD 明细层',
  dws: 'DWS 汇总层',
  ads: 'ADS 应用层',
}

export const JOB_STATUS_LABELS: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
}

export const TAG_CATEGORY_LABELS: Record<string, string> = {
  pii: '隐私 PII',
  business: '业务语义',
  governance: '治理',
}

export const TAG_SOURCE_LABELS: Record<string, string> = {
  manual: '人工',
  inferred: '算法',
}

export const INFERENCE_SOURCE_LABELS: Record<string, string> = {
  auto: '算法推断',
  manual: '人工纠正',
}

export const PAIR_STATUS_LABELS: Record<string, string> = {
  recommended: '待确认',
  dismissed: '已排除',
  merged: '已合并',
}

export const VERDICT_LABELS: Record<string, string> = {
  identical_copy: '完全复制',
  likely_duplicate: '高度疑似重复',
  review: '需人工复核',
  weak: '弱相似',
}
