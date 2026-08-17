import { formatUzsCompact } from '@/lib/format'
import type { FinancialTrendPoint } from '@/lib/types'

type NumericKey = {
  [K in keyof FinancialTrendPoint]: FinancialTrendPoint[K] extends number ? K : never
}[keyof FinancialTrendPoint]

interface Series {
  key: NumericKey
  label: string
  color: string
}

export function FinancialTrendChart({ data, series }: { data: FinancialTrendPoint[]; series: Series[] }) {
  const width = 720
  const height = 250
  const padding = { top: 16, right: 12, bottom: 30, left: 12 }
  const values = data.flatMap((point) => series.map((item) => Number(point[item.key])))
  const min = Math.min(0, ...values)
  const max = Math.max(1, ...values)
  const range = Math.max(1, max - min)
  const chartHeight = height - padding.top - padding.bottom
  const y = (value: number) => padding.top + ((max - value) / range) * chartHeight
  const x = (index: number) => padding.left + (index / Math.max(1, data.length - 1)) * (width - padding.left - padding.right)
  const zeroY = y(0)

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={series.map((item) => item.label).join(', ')}>
        <line x1={padding.left} y1={zeroY} x2={width - padding.right} y2={zeroY} stroke="var(--color-border-strong)" />
        {series.map((item) => {
          const points = data.map((point, index) => `${x(index)},${y(Number(point[item.key]))}`).join(' ')
          return (
            <g key={item.key}>
              <polyline points={points} fill="none" stroke={item.color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
              {data.map((point, index) => (
                <circle key={point.month} cx={x(index)} cy={y(Number(point[item.key]))} r="4" fill="var(--color-surface)" stroke={item.color} strokeWidth="2" />
              ))}
            </g>
          )
        })}
        {data.map((point, index) => (
          <text key={point.month} x={x(index)} y={height - 7} textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">
            {point.month.slice(5)}
          </text>
        ))}
      </svg>
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 14, fontSize: 12.5, color: 'var(--color-text-secondary)' }}>
        {series.map((item) => (
          <span key={item.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: item.color }} />
            {item.label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto', color: 'var(--color-text-muted)' }}>{formatUzsCompact(max)} max</span>
      </div>
    </div>
  )
}
