import { formatUzs } from '@/lib/format'

const SIZES = {
  sm: { value: 'var(--text-base)', unit: '10.5px', weight: 600 },
  md: { value: 'clamp(13px, 3.1vw, 15.5px)', unit: '11px', weight: 600 },
  lg: { value: 'clamp(19px, 4.2vw, 31px)', unit: '12px', weight: 650 },
} as const

/** Renders a UZS amount with tabular numerals and semantic color: green for
 * positive/confirmed money in, red for negative amounts (e.g. reversals),
 * neutral otherwise. Color is never the only signal — the sign is always
 * printed too. The currency unit is de-emphasised so the eye lands on the
 * figure first, which is the whole job of a number in a finance panel. */
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

  const scale = SIZES[size]
  const formatted = formatUzs(value)
  const split = formatted.lastIndexOf('\u00A0')
  const figure = split === -1 ? formatted : formatted.slice(0, split)
  const unit = split === -1 ? '' : formatted.slice(split + 1)

  return (
    <span
      className="tabular-num"
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 4,
        color,
        fontSize: scale.value,
        fontWeight: scale.weight,
        letterSpacing: size === 'lg' ? 'var(--tracking-tight)' : '-0.006em',
        whiteSpace: 'nowrap',
      }}
    >
      {figure}
      {unit && (
        <span style={{ fontSize: scale.unit, fontWeight: 500, color: 'var(--color-text-muted)', letterSpacing: 0 }}>
          {unit}
        </span>
      )}
    </span>
  )
}
