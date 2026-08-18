import { useCallback, useEffect, useMemo, useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { CurrencyAmount } from '@/components/ui/CurrencyAmount'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { IncomeExpenseChart } from '@/components/charts/IncomeExpenseChart'
import { CategoryBars } from '@/components/charts/CategoryBars'
import { FinancialTrendChart } from '@/components/charts/FinancialTrendChart'
import { BalanceChart } from '@/components/charts/BalanceChart'
import { moliyaApi } from '@/lib/apiClient'
import type { DashboardSummary, FinancialOverview } from '@/lib/types'
import { currentMonthTashkent, formatDateTime, formatUzsCompact } from '@/lib/format'
import { Link } from '@/router'

type FinancialTab = 'pnl' | 'cashflow' | 'balance'

function todayTashkent(): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tashkent', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const value = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value
  return `${value('year')}-${value('month')}-${value('day')}`
}

function rangeForMonth(month: string): { start: string; end: string } {
  const [year, monthNumber] = month.split('-').map(Number)
  const lastDay = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate()
  const monthEnd = `${month}-${String(lastDay).padStart(2, '0')}`
  const today = todayTashkent()
  return { start: `${month}-01`, end: month === currentMonthTashkent() ? today : monthEnd }
}

function dailySeries(
  source: DashboardSummary['income_vs_expense_by_day'],
  start: string,
  end: string,
): DashboardSummary['income_vs_expense_by_day'] {
  const byDate = new Map(source.map((point) => [point.date, point]))
  const result: DashboardSummary['income_vs_expense_by_day'] = []
  const cursor = new Date(`${start}T00:00:00Z`)
  const final = new Date(`${end}T00:00:00Z`)
  while (cursor <= final) {
    const date = cursor.toISOString().slice(0, 10)
    result.push(byDate.get(date) ?? { date, income_uzs: 0, expense_uzs: 0 })
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  return result
}

export function DashboardPage() {
  const { t } = useI18n()
  const { session } = useAuth()
  const [month, setMonth] = useState(currentMonthTashkent())
  const [dateRange, setDateRange] = useState(() => rangeForMonth(currentMonthTashkent()))
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [financial, setFinancial] = useState<FinancialOverview | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const load = useCallback(() => {
    if (!session) return
    setStatus('loading')
    Promise.all([
      moliyaApi.dashboardSummary(session.actorId, month),
      moliyaApi.financialOverview(session.actorId, month),
    ])
      .then(([summary, overview]) => {
        setData(summary)
        setFinancial(overview)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [month, session])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setDateRange(rangeForMonth(month))
  }, [month])

  const chartData = useMemo(
    () => dailySeries(data?.income_vs_expense_by_day ?? [], dateRange.start, dateRange.end),
    [data?.income_vs_expense_by_day, dateRange.end, dateRange.start],
  )

  const setLastSevenDays = () => {
    const bounds = rangeForMonth(month)
    const start = new Date(`${bounds.end}T00:00:00Z`)
    start.setUTCDate(start.getUTCDate() - 6)
    setDateRange({ start: start.toISOString().slice(0, 10) < bounds.start ? bounds.start : start.toISOString().slice(0, 10), end: bounds.end })
  }

  const balanceCash = financial
    ? financial.balance.cash_uzs + financial.balance.bank_uzs
    : 0

  return (
    <AppShell title={t('dashboard.title')}>
      {status === 'loading' && <LoadingState />}
      {status === 'error' && <ErrorState onRetry={load} />}
      {status === 'ready' && data && financial && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <div className="dashboard-toolbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <label htmlFor="dashboard-month" style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{t('dashboard.month')}</label>
              <input id="dashboard-month" type="month" value={month} onChange={(event) => setMonth(event.target.value)} className="compact-field" />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <SyncBadge status={data.sync_status} lastSyncedAt={data.last_synced_at} />
            </div>
          </div>

          <div className="dashboard-kpi-grid">
            <Link
              to={`/transactions?kind=income&month=${month}`}
              className="kpi-link"
              aria-label={`${t('dashboard.income')} — ${t('common.filter')}`}
            >
              <StatCard label={t('dashboard.income')} value={data.income_uzs} tone="positive" />
            </Link>
            <Link
              to={`/transactions?kind=expense&month=${month}`}
              className="kpi-link"
              aria-label={`${t('dashboard.expense')} — ${t('common.filter')}`}
            >
              <StatCard label={t('dashboard.expense')} value={data.expense_uzs} tone="negative" />
            </Link>
            <StatCard label={t('dashboard.netProfit')} value={data.net_profit_uzs} tone={data.net_profit_uzs < 0 ? 'negative' : 'positive'} />
            <StatCard label={t('dashboard.cashBalance')} value={balanceCash} tone={balanceCash < 0 ? 'negative' : 'neutral'} />
          </div>

          <FinancialReports overview={financial} />

          <div className="dashboard-grid">
            <Card>
              <div className="chart-card-header">
                <div>
                  <h3 className="card-title">{t('dashboard.incomeVsExpense')}</h3>
                  <span className="chart-range-caption">{dateRange.start} — {dateRange.end}</span>
                </div>
                <div className="chart-date-filters" aria-label={t('dashboard.dateRange')}>
                  <label>{t('tx.dateFrom')}<input type="date" min={`${month}-01`} max={dateRange.end} value={dateRange.start} onChange={(event) => setDateRange((current) => ({ start: event.target.value, end: event.target.value > current.end ? event.target.value : current.end }))} /></label>
                  <label>{t('tx.dateTo')}<input type="date" min={dateRange.start} max={rangeForMonth(month).end} value={dateRange.end} onChange={(event) => setDateRange((current) => ({ ...current, end: event.target.value }))} /></label>
                  <Button type="button" variant="ghost" onClick={setLastSevenDays}>{t('dashboard.last7Days')}</Button>
                  <Button type="button" variant="ghost" onClick={() => setDateRange(rangeForMonth(month))}>{t('dashboard.fullMonth')}</Button>
                </div>
              </div>
              <IncomeExpenseChart data={chartData} incomeLabel={t('dashboard.income')} expenseLabel={t('dashboard.expense')} />
            </Card>
            <Card>
              <h3 className="card-title">{t('dashboard.expenseByCategory')}</h3>
              <CategoryBars data={data.expense_by_category} />
            </Card>
          </div>

          <div className="dashboard-grid">
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
                    <li key={tx.entry_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
                      <div>
                        <div style={{ fontSize: 14 }}>{t(`entryKind.${tx.kind}` as const)}</div>
                        <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)' }}>{tx.counterparty ?? '—'}</div>
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
              <div className="pending-count">{data.pending_draft_count}</div>
            </Card>
          </div>
        </div>
      )}
    </AppShell>
  )
}

function FinancialReports({ overview }: { overview: FinancialOverview }) {
  const { t } = useI18n()
  const [tab, setTab] = useState<FinancialTab>('pnl')
  const current = overview.trend.find((point) => point.month === overview.month) ?? overview.trend.at(-1)
  return (
    <Card>
      <div className="financial-header">
        <div>
          <h2 style={{ fontSize: 18 }}>{t('dashboard.financialReports')}</h2>
          <div style={{ marginTop: 5 }}>
            <Badge tone={overview.source === 'google_sheets' ? 'success' : 'neutral'}>
              {overview.source === 'google_sheets' ? t('dashboard.sourceSheets') : t('dashboard.sourceLedger')}
            </Badge>
          </div>
        </div>
        <div className="segmented-control" role="tablist" aria-label={t('dashboard.financialReports')}>
          {(['pnl', 'cashflow', 'balance'] as const).map((item) => (
            <Button key={item} type="button" variant={tab === item ? 'primary' : 'ghost'} onClick={() => setTab(item)} aria-pressed={tab === item} style={{ padding: '8px 12px' }}>
              {item === 'pnl' ? 'P&L' : item === 'cashflow' ? t('dashboard.cashFlow') : t('dashboard.balance')}
            </Button>
          ))}
        </div>
      </div>

      {tab === 'pnl' && current && (
        <div>
          <div className="financial-kpis">
            <MiniStat label={t('dashboard.netRevenue')} value={current.net_revenue_uzs} />
            <MiniStat label={t('dashboard.grossProfit')} value={current.gross_profit_uzs} />
            <MiniStat label={t('dashboard.netProfit')} value={current.net_profit_uzs} />
          </div>
          <FinancialTrendChart data={overview.trend} series={[
            { key: 'income_uzs', label: t('dashboard.income'), color: 'var(--color-primary)' },
            { key: 'gross_profit_uzs', label: t('dashboard.grossProfit'), color: 'var(--color-amber)' },
            { key: 'net_profit_uzs', label: t('dashboard.netProfit'), color: 'var(--color-success)' },
          ]} />
        </div>
      )}

      {tab === 'cashflow' && current && (
        <div>
          <div className="financial-kpis">
            <MiniStat label={t('dashboard.cashInflow')} value={current.cash_inflow_uzs} />
            <MiniStat label={t('dashboard.cashOutflow')} value={current.cash_outflow_uzs} />
            <MiniStat label={t('dashboard.netCashFlow')} value={current.net_cash_flow_uzs} />
            <MiniStat label={t('dashboard.endingCash')} value={current.ending_cash_uzs} />
          </div>
          <FinancialTrendChart data={overview.trend} series={[
            { key: 'cash_inflow_uzs', label: t('dashboard.cashInflow'), color: 'var(--color-success)' },
            { key: 'cash_outflow_uzs', label: t('dashboard.cashOutflow'), color: 'var(--color-danger)' },
            { key: 'ending_cash_uzs', label: t('dashboard.endingCash'), color: 'var(--color-primary)' },
          ]} />
        </div>
      )}

      {tab === 'balance' && (
        <BalanceChart data={overview.balance} labels={{
          cash: t('dashboard.cash'), bank: t('dashboard.bank'), receivables: t('dashboard.receivables'), inventory: t('dashboard.inventory'), payables: t('dashboard.payables'), equity: t('dashboard.equity'), totalAssets: t('dashboard.totalAssets'), liabilitiesEquity: t('dashboard.liabilitiesEquity'), difference: t('dashboard.balanceDifference'),
        }} />
      )}
    </Card>
  )
}

function StatCard({ label, value, tone = 'neutral' }: { label: string; value: number; tone?: 'neutral' | 'positive' | 'negative' }) {
  const color = tone === 'positive' ? 'var(--color-success)' : tone === 'negative' ? 'var(--color-danger)' : 'var(--color-text-primary)'
  return (
    <Card className="kpi-card" data-tone={tone} style={{ padding: 'var(--space-5)' }}>
      <span className="kpi-wash" aria-hidden="true" />
      <div className="kpi-label"><span className="kpi-dot" aria-hidden="true" />{label}</div>
      <span className="kpi-value dashboard-amount-full"><CurrencyAmount value={value} tone={tone} size="lg" /></span>
      <span className="kpi-value dashboard-amount-compact tabular-num" style={{ color, fontSize: 'clamp(17px, 5vw, 24px)', fontWeight: 650, letterSpacing: 'var(--tracking-tight)', whiteSpace: 'nowrap' }}>{formatUzsCompact(value)}</span>
    </Card>
  )
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, letterSpacing: 'var(--tracking-wide)', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: 5 }}>{label}</div>
      <CurrencyAmount value={value} size="md" />
    </div>
  )
}

function SyncBadge({ status, lastSyncedAt }: { status: DashboardSummary['sync_status']; lastSyncedAt: string | null }) {
  const { t } = useI18n()
  const map = {
    ok: { tone: 'success' as const, label: t('dashboard.syncOk') },
    degraded: { tone: 'amber' as const, label: t('dashboard.syncDegraded') },
    failed: { tone: 'danger' as const, label: t('dashboard.syncFailed') },
  }
  const config = map[status]
  return <Badge tone={config.tone}>{config.label}{lastSyncedAt ? ` · ${formatDateTime(lastSyncedAt)}` : ''}</Badge>
}
