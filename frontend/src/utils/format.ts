export function percent(value: number | null | undefined, digits = 1): string {
  return `${((value ?? 0) * 100).toFixed(digits)}%`
}

export function scoreText(value: number | null | undefined): string {
  return (value ?? 0).toFixed(3)
}

export function numberText(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString('zh-CN')
}

export function shortTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}
