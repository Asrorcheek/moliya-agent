import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useI18n } from '@/i18n'
import { Button } from './Button'
import { NavIcon } from './NavIcon'

interface ConfirmDialogProps {
  open: boolean
  title: string
  body: ReactNode
  confirmLabel: string
  cancelLabel?: string
  tone?: 'primary' | 'danger'
  requireAcknowledge?: boolean
  acknowledgeLabel?: string
  onConfirm: () => Promise<void> | void
  onCancel: () => void
}

/**
 * Strong confirmation dialog for financial writes. Financial actions in this
 * product are irreversible except via a reversal entry, so this dialog:
 *  - requires an explicit acknowledgement checkbox for destructive/committing actions
 *  - disables the confirm button the instant it is clicked, and again while the
 *    async action is in flight, so a double click can never submit twice
 *  - only closes after the action genuinely resolves
 */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel,
  tone = 'primary',
  requireAcknowledge = true,
  acknowledgeLabel,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useI18n()
  const [acknowledged, setAcknowledged] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusTimer = window.setTimeout(() => {
      dialogRef.current?.querySelector<HTMLElement>('input, button, [tabindex]:not([tabindex="-1"])')?.focus()
    }, 0)
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onCancel()
      if (e.key === 'Tab' && dialogRef.current) {
        const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>('input, button, [href], [tabindex]:not([tabindex="-1"])')]
          .filter((element) => !element.hasAttribute('disabled'))
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(focusTimer)
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      previousFocus?.focus()
    }
  }, [open, submitting, onCancel])

  if (!open) return null

  const canConfirm = (!requireAcknowledge || acknowledged) && !submitting

  const handleConfirm = async () => {
    if (!canConfirm) return
    setSubmitting(true)
    try {
      await onConfirm()
    } finally {
      setSubmitting(false)
      setAcknowledged(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      className="dialog-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: 16,
      }}
      onClick={() => !submitting && onCancel()}
    >
      <div
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
        className="dialog-panel"
        style={{ width: '100%', maxWidth: 440, padding: 'var(--space-6)' }}
      >
        <div className="dialog-heading">
          <h2 id="confirm-dialog-title">{title}</h2>
          <button type="button" className="icon-button" aria-label={t('common.close')} onClick={onCancel} disabled={submitting}>
            <NavIcon name="close" />
          </button>
        </div>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-base)', lineHeight: 1.6, marginBottom: 'var(--space-4)' }}>{body}</div>

        {requireAcknowledge && (
          <label className="dialog-ack" style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 'var(--text-base)', marginBottom: 'var(--space-5)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              style={{ marginTop: 2 }}
            />
            <span>{acknowledgeLabel ?? body}</span>
          </label>
        )}

        <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end' }}>
          <Button variant="ghost" onClick={onCancel} disabled={submitting}>
            {cancelLabel ?? t('common.cancel')}
          </Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={handleConfirm} disabled={!canConfirm}>
            {submitting ? t('drafts.processing') : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
