import type { Role } from '../types/models'

const MATRIX: Record<string, Role[]> = {
  'ingest:run': ['admin'],
  'column:infer': ['admin', 'analyst'],
  'column:correct': ['admin', 'analyst'],
  'duplicate:recompute': ['admin'],
  'duplicate:merge': ['admin'],
  'duplicate:dismiss': ['admin', 'analyst'],
  'tag:write': ['admin', 'analyst', 'viewer'],
  'export:run': ['admin', 'analyst', 'viewer'],
  'audit:read': ['admin'],
}

export function can(role: Role | undefined, action: string): boolean {
  if (!role) return false
  return (MATRIX[action] ?? []).includes(role)
}
