import { CurrencyAmount } from '@/components/ui/CurrencyAmount'
import type { BalanceSnapshot } from '@/lib/types'

/** Assets are read in blue/teal, obligations and equity in amber/violet, so
 * the two halves of the sheet separate at a glance without needing labels. */
export function BalanceChart({ data, labels }: { data: BalanceSnapshot; labels: Record<string, string> }) {
  const rows = [
    { label: labels.cash, value: data.cash_uzs, color: 'var(--chart-1)' },
    { label: labels.bank, value: data.bank_uzs, color: 'var(--chart-5)' },
    { label: labels.receivables, value: data.receivables_uzs, color: 'var(--chart-2)' },
    { label: labels.inventory, value: data.inventory_uzs, color: 'var(--chart-7)' },
    { label: labels.payables, value: data.payables_uzs, color: 'var(--chart-3)' },
    { label: labels.equity, value: data.equity_uzs, color: 'var(--chart-4)' },
  ]
  const max = Math.max(1, ...rows.map((item) => Math.abs(item.value)))

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(280px, 100%), 1fr))', gap: 'var(--space-5)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
        {rows.map((row, index) => {
          const color = row.value < 0 ? 'var(--color-danger)' : row.color
          return (
            <div className="meter-row" key={row.label}>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, minWidth: 0, fontSize: 'var(--text-base)' }}>
                  <span className="chart-legend-dot" style={{ background: color, flex: '0 0 8px' }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.label}</span>
                </span>
                <CurrencyAmount value={row.value} size="sm" />
              </div>
              <div className="meter-track">
                <div
                  className="meter-fill"
                  style={{
                    width: `${(Math.abs(row.value) / max) * 100}%`,
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Total label={labels.totalAssets} value={data.total_assets_uzs} />
        <Total label={labels.liabilitiesEquity} value={data.liabilities_and_equity_uzs} />
        <Total label={labels.difference} value={data.difference_uzs} danger={data.difference_uzs !== 0} />
      </div>
    </div>
  )
}

function Total({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) {
  return (
    <div
      style={{
        position: 'relative',
        overflow: 'hidden',
        padding: 'var(--space-4)',
        border: `1px solid ${danger ? 'rgba(255, 77, 94, 0.3)' : 'var(--color-border)'}`,
        borderRadius: 'var(--radius-md)',
        background: danger ? 'var(--wash-negative), var(--color-surface-sunken)' : 'var(--glass-1)',
        boxShadow: danger ? 'inset 0 0 24px -12px var(--color-danger-glow)' : 'none',
      }}
    >
      <div
        style={{
          marginBottom: 6,
          fontSize: 'var(--text-xs)',
          fontWeight: 600,
          letterSpacing: 'var(--tracking-wide)',
          textTransform: 'uppercase',
          color: danger ? 'var(--color-danger-strong)' : 'var(--color-text-muted)',
        }}
      >
        {label}
      </div>
      <CurrencyAmount value={value} size="md" tone={danger ? 'negative' : 'neutral'} />
    </div>
  )
}
