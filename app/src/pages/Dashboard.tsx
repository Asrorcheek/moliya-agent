import { useEffect, useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { CurrencyAmount } from '@/components/ui/CurrencyAmount'
import { Badge } from '@/components/ui/Badge'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { IncomeExpenseChart } from '@/components/charts/IncomeExpenseChart'
import { CategoryBars } from '@/components/charts/CategoryBars'
import { moliyaApi } from '@/lib/apiClient'
import type { DashboardSummary } from '@/lib/types'
import { currentMonthTashkent, formatDateTime, formatMonthLabel } from '@/lib/format'
import { Link } from '@/router'

export function DashboardPage() {
  const { t, locale } = useI18n()
  const { session } = useAuth()
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const load = () => {
    if (!session) return
    setStatus('loading')
    moliyaApi
      .dashboardSummary(session.actorId, currentMonthTashkent())
      .then((res) => {
        setData(res)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }

  useEffect(load, [session]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AppShell title={t('dashboard.title')}>
      {status === 'loading' && <LoadingState />}
      {status === 'error' && <ErrorState onRetry={load} />}
      {status === 'ready' && data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <h2 style={{ fontSize: 15, color: 'var(--color-text-secondary)', fontWeight: 400 }}>
              {t('dashboard.month')}: {formatMonthLabel(data.month, locale)}
            </h2>
            <SyncBadge status={data.sync_status} lastSyncedAt={data.last_synced_at} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(300px, 100%), 1fr))', gap: 'var(--space-4)' }}>
            <StatCard label={t('dashboard.income')} value={data.income_uzs} tone="positive" />
            <StatCard label={t('dashboard.expense')} value={data.expense_uzs} tone="negative" />
            <StatCard label={t('dashboard.costOfGoods')} value={data.cost_of_goods_uzs} />
            <StatCard label={t('dashboard.grossProfit')} value={data.gross_profit_uzs} tone="positive" />
            <StatCard label={t('dashboard.netProfit')} value={data.net_profit_uzs} tone="positive" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-4)' }}>
            <StatCard label={t('dashboard.cash')} value={data.cash_uzs} size="sm" />
            <StatCard label={t('dashboard.card')} value={data.card_uzs} size="sm" />
            <StatCard label={t('dashboard.transfer')} value={data.transfer_uzs} size="sm" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 'var(--space-4)' }} className="dashboard-grid">
            <Card>
              <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('dashboard.incomeVsExpense')}</h3>
              <IncomeExpenseChart data={data.income_vs_expense_by_day} incomeLabel={t('dashboard.income')} expenseLabel={t('dashboard.expense')} />
            </Card>
            <Card>
              <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('dashboard.expenseByCategory')}</h3>
              <CategoryBars data={data.expense_by_category} />
            </Card>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 'var(--space-4)' }} className="dashboard-grid">
            <Card padded={false}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-5) var(--space-5) 0' }}>
                <h3>{t('dashboard.recentTransactions')}</h3>
                <Link to="/transactions" style={{ fontSize: 13 }}>{t('dashboard.viewAll')}</Link>
              </div>
              {data.recent_transactions.length === 0 ? (
                <EmptyState />
              ) : (
                <ul style={{ listStyle: 'none', margin: 0, padding: 'var(--space-3) var(--space-5) var(--space-5)' }}>
                  {data.recent_transactions.map((tx) => (
                    <li key={tx.entry_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
                      <div>
                        <div style={{ fontSize: 14 }}>{t(`entryKind.${tx.kind}` as const)}</div>
                        <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)' }}>{tx.counterparty ?? '\u2014'}</div>
                      </div>
                      <CurrencyAmount value={tx.kind === 'expense' || tx.kind === 'cost_of_goods' ? -tx.amount_uzs : tx.amount_uzs} size="sm" />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                <h3>{t('dashboard.pendingConfirmations')}</h3>
                <Link to="/drafts" style={{ fontSize: 13 }}>{t('dashboard.viewAll')}</Link>
              </div>
              <div style={{ fontSize: 32, fontFamily: 'var(--font-display)' }}>{data.pending_draft_count}</div>
            </Card>
          </div>
        </div>
      )}

      <style>{`@media (max-width: 900px) { .dashboard-grid { grid-template-columns: 1fr !important; } }`}</style>
    </AppShell>
  )
}

function StatCard({ label, value, tone = 'neutral', size = 'md' }: { label: string; value: number; tone?: 'neutral' | 'positive' | 'negative'; size?: 'sm' | 'md' }) {
  return (
    <Card style={{ padding: size === 'sm' ? 'var(--space-4)' : 'var(--space-5)' }}>
      <div style={{ fontSize: 12.5, color: 'var(--color-text-secondary)', marginBottom: 6 }}>{label}</div>
      <CurrencyAmount value={value} tone={tone} size={size === 'sm' ? 'md' : 'lg'} />
    </Card>
  )
}

function SyncBadge({ status, lastSyncedAt }: { status: DashboardSummary['sync_status']; lastSyncedAt: string | null }) {
  const { t } = useI18n()
  const map = {
    ok: { tone: 'success' as const, label: t('dashboard.syncOk') },
    degraded: { tone: 'amber' as const, label: t('dashboard.syncDegraded') },
    failed: { tone: 'danger' as const, label: t('dashboard.syncFailed') },
  }
  const cfg = map[status]
  return (
    <Badge tone={cfg.tone}>
      {cfg.label}
      {lastSyncedAt ? ` \u00b7 ${formatDateTime(lastSyncedAt)}` : ''}
    </Badge>
  )
}
