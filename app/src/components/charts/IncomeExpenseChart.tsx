import { useState } from 'react'
import { formatDate, formatUzs, formatUzsCompact } from '@/lib/format'

interface Point {
  date: string
  income_uzs: number
  expense_uzs: number
}

/** Grouped bar chart. Hand-rolled SVG rather than a charting library so the
 * whole project stays dependency-light and easy to audit — the data volume
 * here (a handful of days per month) does not need a general-purpose
 * charting engine.
 *
 * Visual treatment: gradient bar fills, a four-line value grid behind the
 * plot, and thinned x-labels so a 31-day month does not collapse into an
 * unreadable band of text. */
export function IncomeExpenseChart({ data, incomeLabel, expenseLabel }: { data: Point[]; incomeLabel: string; expenseLabel: string }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  if (data.length === 0) {
    return <div style={{ minHeight: 220, display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)' }}>—</div>
  }
  const width = 640
  const height = 232
  const paddingLeft = 8
  const paddingBottom = 26
  const chartHeight = height - paddingBottom
  const max = Math.max(1, ...data.flatMap((d) => [d.income_uzs, d.expense_uzs]))
  const groupWidth = (width - paddingLeft) / data.length
  const barWidth = Math.max(3, Math.min(16, groupWidth / 2.6))
  const plot = chartHeight - 20

  // With many days, printing every label produces overlapping mush. Show at
  // most eight, evenly spaced, always including the first and last.
  const labelStep = Math.max(1, Math.ceil(data.length / 8))

  const active = activeIndex === null ? null : data[activeIndex]
  const activeX = activeIndex === null ? 50 : Math.min(82, Math.max(18, ((paddingLeft + activeIndex * groupWidth + groupWidth / 2) / width) * 100))

  return (
    <div className="chart-interactive" onMouseLeave={() => setActiveIndex(null)}>
      {active && (
        <div className="chart-tooltip" style={{ left: `${activeX}%` }} role="status">
          <strong>{formatDate(active.date)}</strong>
          <span><i style={{ background: 'var(--color-success)' }} />{incomeLabel}<b>{formatUzs(active.income_uzs)}</b></span>
          <span><i style={{ background: 'var(--color-danger)' }} />{expenseLabel}<b>{formatUzs(active.expense_uzs)}</b></span>
        </div>
      )}
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${incomeLabel} / ${expenseLabel} chart`}>
        <defs>
          <linearGradient id="moliya-income-bar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-success-strong)" />
            <stop offset="100%" stopColor="var(--color-success)" stopOpacity="0.42" />
          </linearGradient>
          <linearGradient id="moliya-expense-bar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-danger-strong)" />
            <stop offset="100%" stopColor="var(--color-danger)" stopOpacity="0.42" />
          </linearGradient>
        </defs>

        {[0.25, 0.5, 0.75, 1].map((ratio) => (
          <line
            key={ratio}
            x1={paddingLeft}
            x2={width}
            y1={chartHeight - plot * ratio}
            y2={chartHeight - plot * ratio}
            stroke="var(--chart-grid)"
            strokeDasharray="2 5"
          />
        ))}

        {data.map((d, i) => {
          const groupX = paddingLeft + i * groupWidth + groupWidth / 2
          const incomeH = Math.max(0, (d.income_uzs / max) * plot)
          const expenseH = Math.max(0, (d.expense_uzs / max) * plot)
          const showLabel = i % labelStep === 0 || i === data.length - 1
          return (
            <g key={d.date}>
              <rect
                className="chart-bar"
                style={{ animationDelay: `${i * 22}ms` }}
                x={groupX - barWidth - 1.5}
                y={chartHeight - incomeH}
                width={barWidth}
                height={incomeH}
                rx={Math.min(3, barWidth / 2)}
                fill="url(#moliya-income-bar)"
              />
              <rect
                className="chart-bar"
                style={{ animationDelay: `${i * 22 + 60}ms` }}
                x={groupX + 1.5}
                y={chartHeight - expenseH}
                width={barWidth}
                height={expenseH}
                rx={Math.min(3, barWidth / 2)}
                fill="url(#moliya-expense-bar)"
              />
              <rect
                className="chart-hit-area"
                x={paddingLeft + i * groupWidth}
                y={0}
                width={groupWidth}
                height={chartHeight}
                fill="transparent"
                tabIndex={0}
                role="button"
                aria-label={`${formatDate(d.date)} · ${incomeLabel}: ${formatUzs(d.income_uzs)} · ${expenseLabel}: ${formatUzs(d.expense_uzs)}`}
                onMouseEnter={() => setActiveIndex(i)}
                onFocus={() => setActiveIndex(i)}
                onBlur={() => setActiveIndex(null)}
              />
              {showLabel && (
                <text x={groupX} y={height - 7} textAnchor="middle" fontSize="10.5" fill="var(--color-text-faint)">
                  {d.date}
                </text>
              )}
            </g>
          )
        })}
        <line x1={paddingLeft} y1={chartHeight} x2={width} y2={chartHeight} stroke="var(--chart-axis)" />
      </svg>
      <div className="chart-legend">
        <LegendDot color="var(--color-success)" label={incomeLabel} />
        <LegendDot color="var(--color-danger)" label={expenseLabel} />
        <span className="chart-scale">{'≈'} {formatUzsCompact(max)} max</span>
      </div>
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
      <span className="chart-legend-dot" style={{ background: color }} />
      {label}
    </span>
  )
}
