import { CurrencyAmount } from '@/components/ui/CurrencyAmount'
import type { BalanceSnapshot } from '@/lib/types'

export function BalanceChart({ data, labels }: { data: BalanceSnapshot; labels: Record<string, string> }) {
  const rows = [
    { label: labels.cash, value: data.cash_uzs },
    { label: labels.bank, value: data.bank_uzs },
    { label: labels.receivables, value: data.receivables_uzs },
    { label: labels.inventory, value: data.inventory_uzs },
    { label: labels.payables, value: data.payables_uzs },
    { label: labels.equity, value: data.equity_uzs },
  ]
  const max = Math.max(1, ...rows.map((item) => Math.abs(item.value)))
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(280px, 100%), 1fr))', gap: 'var(--space-5)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {rows.map((row) => (
          <div key={row.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 4, fontSize: 13 }}>
              <span>{row.label}</span>
              <CurrencyAmount value={row.value} size="sm" />
            </div>
            <div style={{ height: 8, borderRadius: 999, background: 'var(--color-bg)', overflow: 'hidden' }}>
              <div style={{ width: `${Math.abs(row.value) / max * 100}%`, height: '100%', borderRadius: 999, background: row.value < 0 ? 'var(--color-danger)' : 'var(--color-primary)' }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Total label={labels.totalAssets} value={data.total_assets_uzs} />
        <Total label={labels.liabilitiesEquity} value={data.liabilities_and_equity_uzs} />
        <Total label={labels.difference} value={data.difference_uzs} danger={data.difference_uzs !== 0} />
      </div>
    </div>
  )
}

function Total({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) {
  return (
    <div style={{ padding: 'var(--space-4)', background: danger ? 'var(--color-danger-soft)' : 'var(--color-bg)', borderRadius: 'var(--radius-md)' }}>
      <div style={{ fontSize: 12.5, color: danger ? 'var(--color-danger-strong)' : 'var(--color-text-secondary)', marginBottom: 5 }}>{label}</div>
      <CurrencyAmount value={value} size="md" tone={danger ? 'negative' : 'neutral'} />
    </div>
  )
}
