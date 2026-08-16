import { useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { moliyaApi, ApiError } from '@/lib/apiClient'
import type { DraftRecord } from '@/lib/types'
import { formatUzs } from '@/lib/format'

export function AddTransactionPage() {
  const { t } = useI18n()
  const { session } = useAuth()
  const [text, setText] = useState('')
  const [draft, setDraft] = useState<DraftRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [resolution, setResolution] = useState<'confirmed' | 'rejected' | null>(null)

  const handleCreateDraft = async () => {
    if (!text.trim() || !session) return
    setSubmitting(true)
    setError(null)
    setDraft(null)
    setResolution(null)
    try {
      const res = await moliyaApi.createDraft({
        actor_id: session.actorId,
        source_id: `web-${Date.now()}`,
        text: text.trim(),
      })
      setDraft(res.draft)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('state.errorDesc'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleConfirm = async () => {
    if (!draft || !session) return
    try {
      await moliyaApi.confirmDraft(draft.id, session.actorId)
      setResolution('confirmed')
      setConfirmOpen(false)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('state.errorDesc'))
      throw e
    }
  }

  return (
    <AppShell title={t('add.title')}>
      <Card style={{ maxWidth: 640 }}>
        <label style={{ display: 'block', fontSize: 13.5, marginBottom: 8 }}>{t('add.title')}</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t('add.placeholder')}
          rows={3}
          style={{
            width: '100%',
            padding: 12,
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border-strong)',
            fontSize: 14,
            resize: 'vertical',
            fontFamily: 'inherit',
          }}
        />
        <div style={{ marginTop: 'var(--space-3)' }}>
          <Button variant="primary" onClick={handleCreateDraft} disabled={submitting || !text.trim()}>
            {submitting ? t('common.loading') : t('add.submit')}
          </Button>
        </div>

        {error && (
          <p style={{ color: 'var(--color-danger)', fontSize: 13.5, marginTop: 'var(--space-3)' }}>
            {error} \u2014 backendga ulanib bo'lmadi. VITE_MOLIYA_API_BASE_URL to'g'ri sozlanganini va backend ishga tushirilganini tekshiring.
          </p>
        )}

        {draft && !resolution && (
          <div style={{ marginTop: 'var(--space-5)', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-5)' }}>
            <h3 style={{ marginBottom: 'var(--space-3)' }}>{t('add.preview')}</h3>

            {draft.parsed.needs_clarification ? (
              <Badge tone="amber">{t('add.clarificationNeeded')}: {draft.parsed.clarification_question}</Badge>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 'var(--space-4)' }}>
                {draft.parsed.entries.map((entry, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 'var(--radius-md)' }}>
                    <span>{t(`entryKind.${entry.kind}` as const)}{entry.category ? ` \u00b7 ${entry.category}` : ''}</span>
                    <span className="tabular-num">{formatUzs(entry.amount_uzs)} · {t(`payment.${entry.payment_method}` as const)}</span>
                  </div>
                ))}
              </div>
            )}

            {!draft.parsed.needs_clarification && (
              <Button variant="primary" onClick={() => setConfirmOpen(true)}>
                {t('common.confirm')}
              </Button>
            )}
          </div>
        )}

        {resolution === 'confirmed' && (
          <p style={{ marginTop: 'var(--space-5)', color: 'var(--color-success-strong)', fontSize: 14 }}>
            <i className="ti ti-check" aria-hidden="true" /> {t('status.confirmed')}
          </p>
        )}
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        title={t('drafts.confirmTitle')}
        body={t('drafts.confirmBody')}
        confirmLabel={t('drafts.confirmAction')}
        onConfirm={() => handleConfirm().catch(() => {})}
        onCancel={() => setConfirmOpen(false)}
      />
    </AppShell>
  )
}
