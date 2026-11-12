export function confidenceTone(confidence: number, type: string | null): 'high' | 'mid' | 'low' | 'fail' {
  if (type === 'unknown' || type === 'ambiguous') return 'fail'
  if (confidence >= 0.9) return 'high'
  if (confidence >= 0.6) return 'mid'
  return 'low'
}

export function confidenceLabel(confidence: number): string {
  return `${Math.round((confidence ?? 0) * 100)}%`
}
