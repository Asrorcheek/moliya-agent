import { formatUzsCompact } from '@/lib/format'

interface Point {
  date: string
  income_uzs: number
  expense_uzs: number
}

/** Simple, accessible grouped bar chart. Hand-rolled SVG rather than a
 * charting library so the whole project stays dependency-light and easy to
 * audit — the data volume here (a handful of days per month) does not need
 * a general-purpose charting engine. */
export function IncomeExpenseChart({ data, incomeLabel, expenseLabel }: { data: Point[]; incomeLabel: string; expenseLabel: string }) {
  if (data.length === 0) {
    return <div style={{ minHeight: 220, display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)' }}>—</div>
  }
  const width = 640
  const height = 220
  const paddingLeft = 8
  const paddingBottom = 24
  const chartHeight = height - paddingBottom
  const max = Math.max(1, ...data.flatMap((d) => [d.income_uzs, d.expense_uzs]))
  const groupWidth = (width - paddingLeft) / data.length
  const barWidth = Math.min(18, groupWidth / 3)

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${incomeLabel} / ${expenseLabel} chart`}>
        {data.map((d, i) => {
          const groupX = paddingLeft + i * groupWidth + groupWidth / 2
          const incomeH = (d.income_uzs / max) * (chartHeight - 20)
          const expenseH = (d.expense_uzs / max) * (chartHeight - 20)
          return (
            <g key={d.date}>
              <rect
                x={groupX - barWidth - 2}
                y={chartHeight - incomeH}
                width={barWidth}
                height={incomeH}
                rx={3}
                fill="var(--color-success)"
              />
              <rect
                x={groupX + 2}
                y={chartHeight - expenseH}
                width={barWidth}
                height={expenseH}
                rx={3}
                fill="var(--color-danger)"
                opacity={0.85}
              />
              <text
                x={groupX}
                y={height - 6}
                textAnchor="middle"
                fontSize="11"
                fill="var(--color-text-muted)"
              >
                {d.date}
              </text>
            </g>
          )
        })}
        <line x1={paddingLeft} y1={chartHeight} x2={width} y2={chartHeight} stroke="var(--color-border)" />
      </svg>
      <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12.5, color: 'var(--color-text-secondary)' }}>
        <LegendDot color="var(--color-success)" label={incomeLabel} />
        <LegendDot color="var(--color-danger)" label={expenseLabel} />
        <span style={{ marginLeft: 'auto', color: 'var(--color-text-muted)' }}>{formatUzsCompact(max)} {'\u2248'} max</span>
      </div>
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }} />
      {label}
    </span>
  )
}
