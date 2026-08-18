import { formatUzsCompact } from '@/lib/format'

interface CategoryPoint {
  category: string
  amount_uzs: number
}

/** Eight-hue categorical ramp. Rotating colour per row is what makes this
 * read as a breakdown rather than one long blue smear — the old single-colour
 * version carried no information the numbers did not already give. */
const PALETTE = [
  'var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)',
  'var(--chart-5)', 'var(--chart-6)', 'var(--chart-7)', 'var(--chart-8)',
]

/** Horizontal bar list for category breakdowns — reads better than a pie
 * chart at this width and scales cleanly on mobile. */
export function CategoryBars({ data }: { data: CategoryPoint[] }) {
  if (data.length === 0) {
    return <div style={{ minHeight: 120, display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)' }}>—</div>
  }
  const max = Math.max(1, ...data.map((d) => d.amount_uzs))
  const total = data.reduce((sum, d) => sum + d.amount_uzs, 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
      {data.map((d, index) => {
        const color = PALETTE[index % PALETTE.length]
        const share = total > 0 ? Math.round((d.amount_uzs / total) * 100) : 0
        return (
          <div className="meter-row" key={d.category}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, minWidth: 0, fontSize: 'var(--text-base)' }}>
                <span className="chart-legend-dot" style={{ background: color, flex: '0 0 8px' }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.category}</span>
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 8, whiteSpace: 'nowrap' }}>
                <span className="tabular-num" style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {formatUzsCompact(d.amount_uzs)}
                </span>
                <span className="tabular-num" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', minWidth: 30, textAlign: 'right' }}>
                  {share}%
                </span>
              </span>
            </div>
            <div className="meter-track">
              <div
                className="meter-fill"
                style={{
                  width: `${(d.amount_uzs / max) * 100}%`,
                  animationDelay: `${index * 55}ms`,
                  background: `linear-gradient(90deg, ${color} 0%, color-mix(in srgb, ${color} 55%, transparent) 100%)`,
                  boxShadow: `0 0 12px -2px ${color}`,
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
