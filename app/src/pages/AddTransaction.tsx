import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { moliyaApi, ApiError } from '@/lib/apiClient'
import type { DraftRecord } from '@/lib/types'
import { formatUzs } from '@/lib/format'
import { Link } from '@/router'

export function AddTransactionPage() {
  const { t } = useI18n()
  const { session } = useAuth()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [text, setText] = useState('')
  const [draft, setDraft] = useState<DraftRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [resolution, setResolution] = useState<'confirmed' | null>(null)

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const createDraft = async (event?: FormEvent) => {
    event?.preventDefault()
    if (!text.trim() || !session || submitting) return
    setSubmitting(true)
    setError(null)
    setResolution(null)
    try {
      if (draft?.status === 'pending') {
        await moliyaApi.rejectDraft(draft.id, session.actorId).catch(() => undefined)
      }
      const response = await moliyaApi.createDraft({
        actor_id: session.actorId,
        source_id: `web-${Date.now()}`,
        text: text.trim(),
      })
      setDraft(response.draft)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t('state.errorDesc'))
    } finally {
      setSubmitting(false)
    }
  }

  const confirm = async () => {
    if (!draft || !session || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await moliyaApi.confirmDraft(draft.id, session.actorId)
      setResolution('confirmed')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t('state.errorDesc'))
    } finally {
      setSubmitting(false)
    }
  }

  const discard = async () => {
    if (draft && session) {
      setSubmitting(true)
      await moliyaApi.rejectDraft(draft.id, session.actorId).catch(() => undefined)
      setSubmitting(false)
    }
    setDraft(null)
    setError(null)
    textareaRef.current?.focus()
  }

  const reset = () => {
    setText('')
    setDraft(null)
    setResolution(null)
    setError(null)
    window.setTimeout(() => textareaRef.current?.focus(), 0)
  }

  const examples = [t('add.exampleIncome'), t('add.exampleExpense'), t('add.exampleDebt')]

  return (
    <AppShell title={t('add.title')}>
      <div style={{ width: '100%', maxWidth: 760, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {!resolution && (
          <Card>
            <div className="add-step-heading">
              <span className="step-number">1</span>
              <div>
                <h2 style={{ fontSize: 18 }}>{t('add.stepInput')}</h2>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, marginTop: 3 }}>{t('add.inputHint')}</p>
              </div>
            </div>
            <form onSubmit={createDraft}>
              <textarea
                ref={textareaRef}
                value={text}
                onChange={(event) => setText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) void createDraft()
                }}
                placeholder={t('add.placeholder')}
                rows={4}
                className="add-transaction-textarea"
              />
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
                {examples.map((example) => (
                  <button key={example} type="button" className="example-chip" onClick={() => { setText(example); textareaRef.current?.focus() }}>
                    {example}
                  </button>
                ))}
              </div>
              <div className="add-actions">
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{t('add.shortcut')}</span>
                <Button type="submit" variant="primary" disabled={submitting || !text.trim()}>
                  {submitting && !draft ? t('common.loading') : draft ? t('add.reanalyze') : t('add.analyze')}
                </Button>
              </div>
            </form>
            {error && <p role="alert" style={{ color: 'var(--color-danger)', fontSize: 13.5, marginTop: 'var(--space-3)' }}>{error}</p>}
          </Card>
        )}

        {draft && !resolution && (
          <Card>
            <div className="add-step-heading">
              <span className="step-number">2</span>
              <div>
                <h2 style={{ fontSize: 18 }}>{t('add.stepReview')}</h2>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, marginTop: 3 }}>{draft.parsed.transaction_date}</p>
              </div>
            </div>
            {draft.parsed.needs_clarification ? (
              <div style={{ padding: 'var(--space-4)', background: 'var(--color-amber-soft)', borderRadius: 'var(--radius-md)' }}>
                <Badge tone="amber">{t('add.clarificationNeeded')}</Badge>
                <p style={{ marginTop: 8, color: 'var(--color-amber-strong)', fontSize: 14 }}>{draft.parsed.clarification_question}</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {draft.parsed.entries.map((entry, index) => (
                  <div key={`${entry.kind}-${index}`} className="parsed-entry-row">
                    <div>
                      <div style={{ fontWeight: 500 }}>{t(`entryKind.${entry.kind}` as const)}</div>
                      <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)' }}>
                        {[entry.category, entry.counterparty, t(`payment.${entry.payment_method}` as const)].filter(Boolean).join(' · ')}
                      </div>
                    </div>
                    <span className="tabular-num" style={{ fontWeight: 600 }}>{formatUzs(entry.amount_uzs)}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="add-actions" style={{ marginTop: 'var(--space-4)' }}>
              <Button type="button" variant="ghost" onClick={() => void discard()} disabled={submitting}>{t('add.discard')}</Button>
              {!draft.parsed.needs_clarification && (
                <Button type="button" variant="primary" onClick={() => void confirm()} disabled={submitting}>
                  {submitting ? t('common.loading') : t('add.confirmAndSave')}
                </Button>
              )}
            </div>
          </Card>
        )}

        {resolution === 'confirmed' && (
          <Card style={{ textAlign: 'center', padding: 'var(--space-7) var(--space-5)' }}>
            <div className="success-mark" aria-hidden="true">✓</div>
            <h2 style={{ marginTop: 'var(--space-4)' }}>{t('add.savedTitle')}</h2>
            <p style={{ marginTop: 6, color: 'var(--color-text-secondary)' }}>{t('add.savedDesc')}</p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 10, flexWrap: 'wrap', marginTop: 'var(--space-5)' }}>
              <Button type="button" variant="primary" onClick={reset}>{t('add.addAnother')}</Button>
              <Link to="/transactions" className="secondary-link-button">{t('nav.transactions')}</Link>
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  )
}
