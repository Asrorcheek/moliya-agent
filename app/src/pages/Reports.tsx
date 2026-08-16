import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { LoadingState, ErrorState } from '@/components/ui/States'
import { CategoryBars } from '@/components/charts/CategoryBars'
import { moliyaApi } from '@/lib/apiClient'
import type { MonthlyReport, DashboardSummary } from '@/lib/types'
import { currentMonthTashkent, formatMonthLabel, formatUzs } from '@/lib/format'

function previousMonth(value: string): string {
  const [year, month] = value.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 2, 1))
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
}

export function ReportsPage() {
  const { t, locale } = useI18n()
  const { session } = useAuth()
  const [month, setMonth] = useState(currentMonthTashkent())
  const [report, setReport] = useState<MonthlyReport | null>(null)
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [previous, setPrevious] = useState<MonthlyReport | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const load = useCallback(() => {
    if (!session) return
    setStatus('loading')
    Promise.all([
      moliyaApi.monthlyReport(session.actorId, month),
      moliyaApi.dashboardSummary(session.actorId, month),
      moliyaApi.monthlyReport(session.actorId, previousMonth(month)),
    ])
      .then(([monthlyReport, dashboardReport, previousReport]) => {
        setReport(monthlyReport)
        setDashboard(dashboardReport)
        setPrevious(previousReport)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [month, session])

  useEffect(() => {
    load()
  }, [load])

  const metrics = report
    ? [
        [t('dashboard.income'), report.income_uzs],
        [t('entryKind.refund'), report.refund_uzs],
        [t('dashboard.costOfGoods'), report.cost_of_goods_uzs],
        [t('dashboard.expense'), report.expense_uzs],
        [t('dashboard.grossProfit'), report.gross_profit_uzs],
        [t('dashboard.netProfit'), report.net_profit_uzs],
      ] as const
    : []

  return (
    <AppShell title={t('reports.title')}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 'var(--space-4)' }}>
        <label style={{ fontSize: 13.5 }}>{t('dashboard.month')}</label>
        <input type="month" value={month} onChange={(event) => setMonth(event.target.value)} style={{ padding: '8px 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-strong)', background: 'var(--color-surface)' }} />
      </div>

      {status === 'loading' && <LoadingState />}
      {status === 'error' && <ErrorState onRetry={load} />}

      {status === 'ready' && report && dashboard && previous && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <Card>
            <h3 style={{ marginBottom: 'var(--space-4)' }}>{formatMonthLabel(month, locale)}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 'var(--space-4)' }}>
              {metrics.map(([label, value]) => <Stat key={label} label={label} value={value} />)}
            </div>
          </Card>

          <Card>
            <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('reports.paymentBreakdown')}</h3>
            <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
              <Stat label={t('dashboard.cash')} value={dashboard.cash_uzs} />
              <Stat label={t('dashboard.card')} value={dashboard.card_uzs} />
              <Stat label={t('dashboard.transfer')} value={dashboard.transfer_uzs} />
            </div>
          </Card>

          <Card>
            <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('reports.categoryAnalysis')}</h3>
            {dashboard.expense_by_category.length > 0
              ? <CategoryBars data={dashboard.expense_by_category} />
              : <p style={{ color: 'var(--color-text-muted)', fontSize: 13.5 }}>{t('state.empty')}</p>}
          </Card>

          <Card>
            <h3 style={{ marginBottom: 4 }}>{t('reports.comparison')}</h3>
            <p style={{ color: 'var(--color-text-muted)', fontSize: 12.5, marginBottom: 'var(--space-4)' }}>
              {formatMonthLabel(previousMonth(month), locale)} {t('reports.comparisonSuffix')}
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
              <Difference label={t('dashboard.income')} current={report.income_uzs} previous={previous.income_uzs} />
              <Difference label={t('dashboard.expense')} current={report.expense_uzs} previous={previous.expense_uzs} positiveIsGood={false} />
              <Difference label={t('dashboard.netProfit')} current={report.net_profit_uzs} previous={previous.net_profit_uzs} />
            </div>
          </Card>
        </div>
      )}
    </AppShell>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div style={{ fontSize: 12.5, color: 'var(--color-text-secondary)', marginBottom: 4 }}>{label}</div>
      <div className="tabular-num" style={{ fontSize: 18 }}>{formatUzs(value)}</div>
    </div>
  )
}

function Difference({ label, current, previous, positiveIsGood = true }: { label: string; current: number; previous: number; positiveIsGood?: boolean }) {
  const value = current - previous
  const isGood = value === 0 ? null : value > 0 === positiveIsGood
  return (
    <div>
      <div style={{ fontSize: 12.5, color: 'var(--color-text-secondary)', marginBottom: 4 }}>{label}</div>
      <div className="tabular-num" style={{ fontSize: 18, color: isGood === true ? 'var(--color-success)' : isGood === false ? 'var(--color-danger)' : 'var(--color-text-primary)' }}>
        {value > 0 ? '+' : ''}{formatUzs(value)}
      </div>
    </div>
  )
}
