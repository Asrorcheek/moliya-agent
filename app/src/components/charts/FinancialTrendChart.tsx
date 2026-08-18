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

/** Multi-series trend line. Visual treatment: a soft area gradient under the
 * first series, a dashed value grid, a highlighted zero baseline and a
 * left-to-right draw-on animation so the trend reads as a movement rather
 * than a static shape. */
export function FinancialTrendChart({ data, series }: { data: FinancialTrendPoint[]; series: Series[] }) {
  const width = 1180
  const height = 292
  const padding = { top: 20, right: 14, bottom: 34, left: 14 }
  const values = data.flatMap((point) => series.map((item) => Number(point[item.key])))
  const min = Math.min(0, ...values)
  const max = Math.max(1, ...values)
  const range = Math.max(1, max - min)
  const chartHeight = height - padding.top - padding.bottom
  const y = (value: number) => padding.top + ((max - value) / range) * chartHeight
  const x = (index: number) => padding.left + (index / Math.max(1, data.length - 1)) * (width - padding.left - padding.right)
  const zeroY = y(0)
  const gridLines = [0.25, 0.5, 0.75]

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={series.map((item) => item.label).join(', ')}>
        <defs>
          <linearGradient id="moliya-trend-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={series[0]?.color ?? 'var(--color-primary)'} stopOpacity="0.24" />
            <stop offset="100%" stopColor={series[0]?.color ?? 'var(--color-primary)'} stopOpacity="0" />
          </linearGradient>
        </defs>

        {gridLines.map((ratio) => (
          <line
            key={ratio}
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + chartHeight * ratio}
            y2={padding.top + chartHeight * ratio}
            stroke="var(--chart-grid)"
            strokeDasharray="2 5"
          />
        ))}

        {series[0] && data.length > 1 && (
          <path
            d={`M ${x(0)},${zeroY} ${data
              .map((point, index) => `L ${x(index)},${y(Number(point[series[0].key]))}`)
              .join(' ')} L ${x(data.length - 1)},${zeroY} Z`}
            fill="url(#moliya-trend-area)"
          />
        )}

        <line x1={padding.left} y1={zeroY} x2={width - padding.right} y2={zeroY} stroke="var(--chart-axis)" />

        {series.map((item, seriesIndex) => {
          const points = data.map((point, index) => `${x(index)},${y(Number(point[item.key]))}`).join(' ')
          return (
            <g key={item.key}>
              <polyline
                className="chart-line"
                style={{ animationDelay: `${seriesIndex * 130}ms` }}
                points={points}
                fill="none"
                stroke={item.color}
                strokeWidth="2.75"
                strokeLinejoin="round"
                strokeLinecap="round"
                opacity="0.28"
                filter="blur(5px)"
              />
              <polyline
                className="chart-line"
                style={{ animationDelay: `${seriesIndex * 130}ms` }}
                points={points}
                fill="none"
                stroke={item.color}
                strokeWidth="2.75"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {data.map((point, index) => (
                <circle
                  key={point.month}
                  className="chart-dot"
                  style={{ animationDelay: `${400 + seriesIndex * 130 + index * 30}ms` }}
                  cx={x(index)}
                  cy={y(Number(point[item.key]))}
                  r="4"
                  fill="var(--color-surface)"
                  stroke={item.color}
                  strokeWidth="2"
                >
                  <title>{`${point.month} · ${item.label}: ${formatUzsCompact(Number(point[item.key]))}`}</title>
                </circle>
              ))}
            </g>
          )
        })}

        {data.map((point, index) => (
          <text key={point.month} x={x(index)} y={height - 9} textAnchor="middle" fontSize="12" fill="var(--color-text-faint)">
            {point.month.slice(5)}
          </text>
        ))}
      </svg>
      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
            <span className="chart-legend-dot" style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
        <span className="chart-scale">{formatUzsCompact(max)} max</span>
      </div>
    </div>
  )
}
