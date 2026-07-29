export function pulsePointCallLabel(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const sourceCode = value.trim().toUpperCase()
  if (!/^[A-Z0-9]{1,3}$/.test(sourceCode)) return null
  return sourceCode === 'ME' ? 'MED' : sourceCode
}
