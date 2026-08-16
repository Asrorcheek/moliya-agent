import { useEffect, useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { moliyaApi, ApiError } from '@/lib/apiClient'
import type { DraftRecord } from '@/lib/types'
import { formatUzs, formatDateTime } from '@/lib/format'

export function DraftsPage() {
  const { t } = useI18n()
  const { session } = useAuth()
  const [drafts, setDrafts] = useState<DraftRecord[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [dialogFor, setDialogFor] = useState<{ draft: DraftRecord; action: 'confirm' | 'reject' } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const load = () => {
    if (!session) return
    setStatus('loading')
    moliyaApi
      .listDrafts(session.actorId, 'pending')
      .then((res) => {
        setDrafts(res.items)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }

  useEffect(load, [session]) // eslint-disable-line react-hooks/exhaustive-deps

  const runAction = async () => {
    if (!dialogFor || !session) return
    setActionError(null)
    const { draft, action } = dialogFor
    try {
      if (action === 'confirm') {
        await moliyaApi.confirmDraft(draft.id, session.actorId)
      } else {
        await moliyaApi.rejectDraft(draft.id, session.actorId)
      }
      setDrafts((prev) => prev.filter((d) => d.id !== draft.id))
      setDialogFor(null)
    } catch (e) {
      const message = e instanceof ApiError ? e.message : t('state.errorDesc')
      setActionError(message)
      // Deliberately not closing the dialog and not removing the draft —
      // a failed write must never look like a successful confirmation.
      throw e
    }
  }

  return (
    <AppShell title={t('drafts.title')}>
      {status === 'loading' && <LoadingState />}
      {status === 'error' && <ErrorState onRetry={load} />}
      {status === 'ready' && drafts.length === 0 && <EmptyState title={t('drafts.empty')} />}

      {status === 'ready' && drafts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {drafts.map((draft) => (
            <Card key={draft.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 'var(--space-3)' }}>
                <div>
                  <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)' }}>{formatDateTime(draft.created_at)}</div>
                  <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)' }}>{t('drafts.parsedDate')}: {draft.parsed.transaction_date}</div>
                </div>
                <ConfidenceBadge confidence={draft.parsed.confidence} />
              </div>

              <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', fontStyle: 'italic', marginBottom: 'var(--space-4)' }}>
                &ldquo;{draft.raw_text}&rdquo;
              </p>

              {draft.parsed.needs_clarification ? (
                <Badge tone="amber">{t('drafts.needsClarification')}: {draft.parsed.clarification_question}</Badge>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 'var(--space-4)' }}>
                  {draft.parsed.entries.map((entry, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 'var(--radius-md)' }}>
                      <span>
                        {t(`entryKind.${entry.kind}` as const)}
                        {entry.category ? ` \u00b7 ${entry.category}` : ''}
                        {entry.counterparty ? ` \u00b7 ${entry.counterparty}` : ''}
                      </span>
                      <span className="tabular-num">{formatUzs(entry.amount_uzs)} · {t(`payment.${entry.payment_method}` as const)}</span>
                    </div>
                  ))}
                </div>
              )}

              {draft.parsed.missing_fields.length > 0 && (
                <p style={{ fontSize: 12.5, color: 'var(--color-amber-strong)', marginBottom: 'var(--space-4)' }}>
                  {t('drafts.missingFields')}: {draft.parsed.missing_fields.join(', ')}
                </p>
              )}

              <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
                <Button variant="primary" onClick={() => setDialogFor({ draft, action: 'confirm' })} disabled={draft.parsed.needs_clarification}>
                  {t('common.confirm')}
                </Button>
                <Button variant="secondary" onClick={() => setDialogFor({ draft, action: 'reject' })}>
                  {t('common.reject')}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!dialogFor}
        title={dialogFor?.action === 'confirm' ? t('drafts.confirmTitle') : t('drafts.rejectTitle')}
        body={
          <>
            {dialogFor?.action === 'confirm' ? t('drafts.confirmBody') : t('drafts.rejectBody')}
            {actionError && <div style={{ color: 'var(--color-danger)', marginTop: 8 }}>{actionError}</div>}
          </>
        }
        confirmLabel={dialogFor?.action === 'confirm' ? t('drafts.confirmAction') : t('drafts.rejectAction')}
        tone={dialogFor?.action === 'reject' ? 'danger' : 'primary'}
        onConfirm={() => runAction().catch(() => {})}
        onCancel={() => {
          setDialogFor(null)
          setActionError(null)
        }}
      />
    </AppShell>
  )
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const { t } = useI18n()
  const tone = confidence >= 0.8 ? 'success' : confidence >= 0.5 ? 'amber' : 'danger'
  return <Badge tone={tone}>{t('drafts.confidence')}: {Math.round(confidence * 100)}%</Badge>
}
