import { formatUzsCompact } from '@/lib/format'

interface CategoryPoint {
  category: string
  amount_uzs: number
}

/** Horizontal bar list for category breakdowns — reads better than a pie
 * chart at this width and scales cleanly on mobile. */
export function CategoryBars({ data }: { data: CategoryPoint[] }) {
  if (data.length === 0) {
    return <div style={{ minHeight: 120, display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)' }}>—</div>
  }
  const max = Math.max(1, ...data.map((d) => d.amount_uzs))
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {data.map((d) => (
        <div key={d.category}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
            <span>{d.category}</span>
            <span className="tabular-num" style={{ color: 'var(--color-text-secondary)' }}>{formatUzsCompact(d.amount_uzs)}</span>
          </div>
          <div style={{ height: 8, borderRadius: 999, background: 'var(--color-bg)', overflow: 'hidden' }}>
            <div
              style={{
                width: `${(d.amount_uzs / max) * 100}%`,
                height: '100%',
                borderRadius: 999,
                background: 'var(--color-primary)',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
