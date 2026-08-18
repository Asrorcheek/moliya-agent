import type { ReactNode } from 'react'
import { useI18n } from '@/i18n'
import { Button } from './Button'

function Frame({ children }: { children: ReactNode }) {
  return <div className="state-frame">{children}</div>
}

export function LoadingState({ label }: { label?: string }) {
  const { t } = useI18n()
  return (
    <Frame>
      <span className="state-spinner" aria-hidden="true" />
      <p>{label ?? t('common.loading')}</p>
    </Frame>
  )
}

export function EmptyState({ title, description }: { title?: string; description?: string }) {
  const { t } = useI18n()
  return (
    <Frame>
      <span className="state-glyph" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 7h16M4 12h11M4 17h7" />
        </svg>
      </span>
      <h3>{title ?? t('state.empty')}</h3>
      {description && <p>{description}</p>}
    </Frame>
  )
}

export function ErrorState({ onRetry, description }: { onRetry?: () => void; description?: string }) {
  const { t } = useI18n()
  return (
    <Frame>
      <span className="state-glyph state-glyph-danger" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 8v5M12 16.5v.01" />
          <path d="M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0Z" />
        </svg>
      </span>
      <h3 style={{ color: 'var(--color-danger-strong)' }}>{t('state.error')}</h3>
      <p>{description ?? t('state.errorDesc')}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} style={{ marginTop: 6 }}>
          {t('common.retry')}
        </Button>
      )}
    </Frame>
  )
}

export function PermissionDeniedState() {
  const { t } = useI18n()
  return (
    <Frame>
      <span className="state-glyph state-glyph-amber" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4.5" y="10.5" width="15" height="9.5" rx="2" />
          <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
        </svg>
      </span>
      <h3>{t('state.permissionDenied')}</h3>
      <p>{t('state.permissionDeniedDesc')}</p>
    </Frame>
  )
}
