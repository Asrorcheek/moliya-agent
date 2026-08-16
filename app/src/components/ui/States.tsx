import type { ReactNode } from 'react'
import { useI18n } from '@/i18n'
import { Button } from './Button'

function Frame({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        gap: 8,
        padding: '48px 24px',
        color: 'var(--color-text-secondary)',
      }}
    >
      {children}
    </div>
  )
}

export function LoadingState({ label }: { label?: string }) {
  const { t } = useI18n()
  return (
    <Frame>
      <div
        aria-hidden="true"
        style={{
          width: 22,
          height: 22,
          borderRadius: '50%',
          border: '2px solid var(--color-border-strong)',
          borderTopColor: 'var(--color-primary)',
          animation: 'moliya-spin 0.8s linear infinite',
        }}
      />
      <p>{label ?? t('common.loading')}</p>
      <style>{`@keyframes moliya-spin { to { transform: rotate(360deg); } }`}</style>
    </Frame>
  )
}

export function EmptyState({ title, description }: { title?: string; description?: string }) {
  const { t } = useI18n()
  return (
    <Frame>
      <h3 style={{ color: 'var(--color-text-primary)' }}>{title ?? t('state.empty')}</h3>
      {description && <p>{description}</p>}
    </Frame>
  )
}

export function ErrorState({ onRetry, description }: { onRetry?: () => void; description?: string }) {
  const { t } = useI18n()
  return (
    <Frame>
      <h3 style={{ color: 'var(--color-danger)' }}>{t('state.error')}</h3>
      <p>{description ?? t('state.errorDesc')}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {t('common.retry')}
        </Button>
      )}
    </Frame>
  )
}

export function PermissionDeniedState() {
  const { t } = useI18n()
  return <Frame><h3 style={{ color: 'var(--color-text-primary)' }}>{t('state.permissionDenied')}</h3><p>{t('state.permissionDeniedDesc')}</p></Frame>
}
