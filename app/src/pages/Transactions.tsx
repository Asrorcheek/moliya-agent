import { useEffect, useState, type CSSProperties } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { CurrencyAmount } from '@/components/ui/CurrencyAmount'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { moliyaApi } from '@/lib/apiClient'
import type { EntryKind, PaymentMethod, TransactionEntry } from '@/lib/types'
import { formatDate, formatDateTime } from '@/lib/format'

const KINDS: EntryKind[] = ['income', 'expense', 'refund', 'cost_of_goods', 'receivable', 'payable', 'customer_payment', 'supplier_payment']
const METHODS: PaymentMethod[] = ['cash', 'card', 'transfer', 'mixed', 'unknown']

interface TransactionFilters {
  search?: string
  dateFrom?: string
  dateTo?: string
  type?: string
  paymentMethod?: string
  category?: string
  counterparty?: string
}

export function TransactionsPage() {
  const { t } = useI18n()
  const { session } = useAuth()
  const [items, setItems] = useState<TransactionEntry[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [filters, setFilters] = useState<TransactionFilters>({})
  const [selected, setSelected] = useState<TransactionEntry | null>(null)

  const load = (f: TransactionFilters) => {
    if (!session) return
    setStatus('loading')
    moliyaApi
      .listTransactions(session.actorId, {
        kind: f.type as EntryKind | undefined,
        paymentMethod: f.paymentMethod as PaymentMethod | undefined,
      })
      .then((res) => {
        let nextItems = res.items
        if (f.search) {
          const needle = f.search.toLocaleLowerCase()
          nextItems = nextItems.filter((item) => [
            item.note,
            item.category,
            item.counterparty,
            item.source_id,
            t(`entryKind.${item.kind}` as const),
          ].some((value) => value?.toLocaleLowerCase().includes(needle)))
        }
        if (f.counterparty) {
          const needle = f.counterparty.toLowerCase()
          nextItems = nextItems.filter((item) => item.counterparty?.toLowerCase().includes(needle))
        }
        if (f.dateFrom) nextItems = nextItems.filter((item) => item.transaction_date >= f.dateFrom!)
        if (f.dateTo) nextItems = nextItems.filter((item) => item.transaction_date <= f.dateTo!)
        if (f.category) nextItems = nextItems.filter((item) => item.category?.toLowerCase().includes(f.category!.toLowerCase()))
        setItems(nextItems)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }

  useEffect(() => load(filters), [session]) // eslint-disable-line react-hooks/exhaustive-deps

  const applyFilters = (next: Partial<TransactionFilters>) => {
    const merged = { ...filters, ...next }
    setFilters(merged)
    load(merged)
  }

  const exportCsv = () => {
    const escape = (value: string | number | null) => `"${String(value ?? '').replaceAll('"', '""')}"`
    const rows = [
      ['entry_id', 'date', 'type', 'amount_uzs', 'payment_method', 'category', 'counterparty', 'note'],
      ...items.map((item) => [item.entry_id, item.transaction_date, item.kind, item.amount_uzs, item.payment_method, item.category, item.counterparty, item.note]),
    ]
    const csv = `\uFEFF${rows.map((row) => row.map(escape).join(',')).join('\n')}`
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `moliya-transactions-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <AppShell title={t('tx.title')}>
      <Card style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 'var(--space-3)' }}>
          <label className="transaction-search-field">
            <i className="ti ti-search" aria-hidden="true" />
            <input
              placeholder={t('tx.searchName')}
              onChange={(e) => applyFilters({ search: e.target.value || undefined })}
            />
          </label>
          <input
            placeholder={t('tx.counterparty')}
            onChange={(e) => applyFilters({ counterparty: e.target.value || undefined })}
            style={fieldStyle}
          />
          <input
            placeholder={t('tx.category')}
            onChange={(e) => applyFilters({ category: e.target.value || undefined })}
            style={fieldStyle}
          />
          <select onChange={(e) => applyFilters({ type: e.target.value || undefined })} style={fieldStyle} defaultValue="">
            <option value="">{t('tx.type')}</option>
            {KINDS.map((k) => (
              <option key={k} value={k}>{t(`entryKind.${k}` as const)}</option>
            ))}
          </select>
          <select onChange={(e) => applyFilters({ paymentMethod: e.target.value || undefined })} style={fieldStyle} defaultValue="">
            <option value="">{t('tx.paymentMethod')}</option>
            {METHODS.map((m) => (
              <option key={m} value={m}>{t(`payment.${m}` as const)}</option>
            ))}
          </select>
          <input type="date" onChange={(e) => applyFilters({ dateFrom: e.target.value || undefined })} style={fieldStyle} aria-label={t('tx.dateRange')} />
          <input type="date" onChange={(e) => applyFilters({ dateTo: e.target.value || undefined })} style={fieldStyle} aria-label={t('tx.dateRange')} />
        </div>
        <div style={{ marginTop: 'var(--space-3)' }}>
          <Button variant="ghost" onClick={exportCsv} disabled={items.length === 0}>
            <i className="ti ti-download" aria-hidden="true" /> {t('common.export')}
          </Button>
        </div>
      </Card>

      {status === 'loading' && <LoadingState />}
      {status === 'error' && <ErrorState onRetry={() => load(filters)} />}
      {status === 'ready' && items.length === 0 && <EmptyState title={t('tx.empty')} />}

      {status === 'ready' && items.length > 0 && (
        <>
          <Card className="desktop-table-card" padded={false} style={{ overflowX: 'auto' }}>
            <table className="desktop-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--color-border)' }}>
                  {[t('tx.date'), t('tx.name'), t('tx.type'), t('tx.counterparty'), t('tx.paymentMethod'), t('tx.amount')].map((h) => (
                    <th key={h} style={{ padding: '10px 14px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((tx) => (
                  <tr
                    key={tx.entry_id}
                    onClick={() => setSelected(tx)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setSelected(tx)
                      }
                    }}
                    tabIndex={0}
                    aria-label={`${t(`entryKind.${tx.kind}` as const)}, ${formatDate(tx.transaction_date)}, ${tx.amount_uzs}`}
                    style={{ borderBottom: '1px solid var(--color-border)', cursor: 'pointer' }}
                  >
                    <td style={{ padding: '10px 14px' }}>{formatDate(tx.transaction_date)}</td>
                    <td style={{ padding: '10px 14px', minWidth: 190 }}>{tx.note ?? tx.category ?? t(`entryKind.${tx.kind}` as const)}</td>
                    <td style={{ padding: '10px 14px' }}>{t(`entryKind.${tx.kind}` as const)}</td>
                    <td style={{ padding: '10px 14px' }}>{tx.counterparty ?? '\u2014'}</td>
                    <td style={{ padding: '10px 14px' }}>{t(`payment.${tx.payment_method}` as const)}</td>
                    <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                      <CurrencyAmount value={tx.amount_uzs} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="mobile-cards" style={{ flexDirection: 'column', gap: 'var(--space-3)' }}>
            {items.map((tx) => (
              <Card key={tx.entry_id} style={{ padding: 'var(--space-4)' }}>
                <div onClick={() => setSelected(tx)} style={{ cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 14 }}>{tx.note ?? tx.category ?? t(`entryKind.${tx.kind}` as const)}</span>
                    <CurrencyAmount value={tx.amount_uzs} size="sm" />
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)', marginTop: 4 }}>
                    {formatDate(tx.transaction_date)} · {tx.counterparty ?? '\u2014'}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {selected && <TransactionDetail tx={selected} onClose={() => setSelected(null)} />}
    </AppShell>
  )
}

function TransactionDetail({ tx, onClose }: { tx: TransactionEntry; onClose: () => void }) {
  const { t } = useI18n()

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{ position: 'fixed', inset: 0, background: 'rgba(15,20,18,0.4)', display: 'flex', justifyContent: 'flex-end', zIndex: 90 }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: 'min(420px, 100%)', height: '100%', background: 'var(--color-surface)', padding: 'var(--space-6)', overflowY: 'auto' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-5)' }}>
          <h2>{t('common.details')}</h2>
          <button onClick={onClose} aria-label={t('common.close')} style={{ background: 'none', border: 'none' }}>
            <i className="ti ti-x" style={{ fontSize: 20 }} aria-hidden="true" />
          </button>
        </div>

        <CurrencyAmount value={tx.amount_uzs} size="lg" />
        <div style={{ marginTop: 'var(--space-5)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', fontSize: 13.5 }}>
          <Row label={t('tx.type')} value={t(`entryKind.${tx.kind}` as const)} />
          <Row label={t('tx.date')} value={formatDate(tx.transaction_date)} />
          <Row label={t('tx.paymentMethod')} value={t(`payment.${tx.payment_method}` as const)} />
          {tx.category && <Row label={t('tx.category')} value={tx.category} />}
          {tx.counterparty && <Row label={t('tx.counterparty')} value={tx.counterparty} />}
          {tx.note && <Row label={t('common.details')} value={tx.note} />}
          <Row label={t('tx.sourceId')} value={tx.source_id} mono />
          <Row label={t('audit.actor')} value={tx.confirmed_by} />
          <Row label={t('audit.timestamp')} value={formatDateTime(tx.confirmed_at)} />
          {tx.reversal_of_entry_id && <Row label={t('tx.reversalOf')} value={tx.reversal_of_entry_id} mono />}
          {tx.reversed_entry_id && <Row label={t('tx.reversedBy')} value={tx.reversed_entry_id} mono />}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
      <span style={{ fontFamily: mono ? 'var(--font-mono)' : undefined, textAlign: 'right' }}>{value}</span>
    </div>
  )
}

const fieldStyle: CSSProperties = {
  padding: '9px 10px',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--color-border-strong)',
  background: 'var(--color-surface)',
  fontSize: 13.5,
}
