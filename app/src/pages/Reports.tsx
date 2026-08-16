import { useEffect, useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { MockNotice } from '@/components/ui/MockNotice'
import { LoadingState, ErrorState } from '@/components/ui/States'
import { CategoryBars } from '@/components/charts/CategoryBars'
import { moliyaApi } from '@/lib/apiClient'
import { mockApi } from '@/lib/mock/mockApi'
import type { MonthlyReport, DashboardSummary } from '@/lib/types'
import { currentMonthTashkent, formatMonthLabel, formatUzs } from '@/lib/format'

export function ReportsPage() {
  const { t, locale } = useI18n()
  const { session } = useAuth()
  const [month, setMonth] = useState(currentMonthTashkent())
  const [report, setReport] = useState<MonthlyReport | null>(null)
  const [mocked, setMocked] = useState<DashboardSummary | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const load = () => {
    if (!session) return
    setStatus('loading')
    Promise.all([moliyaApi.monthlyReport(session.actorId, month), mockApi.dashboardSummary()])
      .then(([realReport, mockSummary]) => {
        setReport(realReport)
        setMocked(mockSummary)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }

  useEffect(load, [month]) // eslint-disable-line react-hooks/exhaustive-deps

  const numericFields = report
    ? Object.entries(report).filter(([k, v]) => k !== 'month' && typeof v === 'number')
    : []

  return (
    <AppShell title={t('reports.title')}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 'var(--space-4)' }}>
        <label style={{ fontSize: 13.5 }}>{t('dashboard.month')}</label>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} style={{ padding: '8px 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-strong)' }} />
      </div>

      {status === 'loading' && <LoadingState />}
      {status === 'error' && (
        <>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 13.5, marginBottom: 8 }}>
            GET /v1/reports/monthly chaqiruvi muvaffaqiyatsiz tugadi \u2014 backend ishga tushirilganini tekshiring.
          </p>
          <ErrorState onRetry={load} />
        </>
      )}

      {status === 'ready' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <Card>
            <h3 style={{ marginBottom: 4 }}>{formatMonthLabel(month, locale)}</h3>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>GET /v1/reports/monthly \u2014 haqiqiy backend ma'lumoti</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 'var(--space-4)' }}>
              {numericFields.map(([key, value]) => (
                <div key={key}>
                  <div style={{ fontSize: 12.5, color: 'var(--color-text-secondary)', marginBottom: 4 }}>{key}</div>
                  <div className="tabular-num" style={{ fontSize: 18 }}>{formatUzs(value as number)}</div>
                </div>
              ))}
              {numericFields.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 13.5 }}>{t('state.empty')}</p>}
            </div>
          </Card>

          <Card>
            <MockNotice note="To'lov turlari taqsimoti hozircha GET /v1/reports/monthly javobida yo'q \u2014 namunaviy ko'rsatilmoqda." />
            {mocked && (
              <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
                <Stat label={t('dashboard.cash')} value={mocked.cash_uzs} />
                <Stat label={t('dashboard.card')} value={mocked.card_uzs} />
                <Stat label={t('dashboard.transfer')} value={mocked.transfer_uzs} />
              </div>
            )}
          </Card>

          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
              <h3>{t('reports.categoryAnalysis')}</h3>
            </div>
            <MockNotice note="Kategoriya tahlili uchun endpoint yo'q \u2014 namunaviy ma'lumot." />
            {mocked && <CategoryBars data={mocked.expense_by_category} />}
          </Card>

          <Card>
            <h3 style={{ marginBottom: 8 }}>{t('reports.comparison')}</h3>
            <p style={{ color: 'var(--color-text-muted)', fontSize: 13.5 }}>{t('reports.comparisonUnavailable')}</p>
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
