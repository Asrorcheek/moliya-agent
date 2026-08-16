import { formatUzs } from '@/lib/format'

/** Renders a UZS amount with tabular numerals and semantic color: green for
 * positive/confirmed money in, red for negative amounts (e.g. reversals),
 * neutral otherwise. Color is never the only signal — the sign is always
 * printed too. */
export function CurrencyAmount({
  value,
  tone = 'neutral',
  size = 'md',
}: {
  value: number
  tone?: 'neutral' | 'positive' | 'negative'
  size?: 'sm' | 'md' | 'lg'
}) {
  const resolvedTone = tone !== 'neutral' ? tone : value < 0 ? 'negative' : 'neutral'
  const color =
    resolvedTone === 'positive'
      ? 'var(--color-success)'
      : resolvedTone === 'negative'
        ? 'var(--color-danger)'
        : 'var(--color-text-primary)'
  const fontSize = size === 'lg' ? 'clamp(23px, 2.1vw, 28px)' : size === 'sm' ? '13px' : '15px'
  return (
    <span className="tabular-num" style={{ color, fontSize, fontWeight: size === 'lg' ? 500 : 400, whiteSpace: 'nowrap' }}>
      {formatUzs(value)}
    </span>
  )
}
