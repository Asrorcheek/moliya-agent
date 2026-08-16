import { useI18n } from '@/i18n'

/** Marks any section backed by mock data instead of a real backend
 * endpoint. Used consistently so nothing in the app quietly looks
 * production-ready when it is not. */
export function MockNotice({ note }: { note?: string }) {
  const { t } = useI18n()
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        background: 'var(--color-amber-soft)',
        color: 'var(--color-amber-strong)',
        border: '1px solid var(--color-amber)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        fontSize: 13,
        marginBottom: 'var(--space-4)',
      }}
    >
      <strong style={{ fontWeight: 600 }}>{t('common.mocked')}.</strong>
      <span>{note ?? t('common.mockedDesc')}</span>
    </div>
  )
}
