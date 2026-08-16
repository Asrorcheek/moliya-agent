import { useState, type CSSProperties, type FormEvent } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export function LoginPage() {
  const { t } = useI18n()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    const result = await login(username, password)
    setSubmitting(false)
    if (!result.ok) setError(result.error ?? t('state.error'))
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        background: 'var(--color-bg)',
      }}
    >
      <Card style={{ width: '100%', maxWidth: 380 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 'var(--space-2)' }}>
          <svg width="28" height="28" viewBox="0 0 26 26" aria-hidden="true">
            <rect x="1" y="1" width="24" height="24" rx="6" fill="var(--color-primary)" />
            <path d="M7 17.5 L11 9 L14 15 L19 8" stroke="var(--color-text-on-primary)" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <h1 style={{ fontSize: 20 }}>{t('app.name')}</h1>
        </div>
        <h2 style={{ marginBottom: 4 }}>{t('login.title')}</h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 13.5, marginBottom: 'var(--space-5)' }}>{t('login.subtitle')}</p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13.5 }}>
            {t('login.username')}
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              style={inputStyle}
              required
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13.5 }}>
            {t('login.password')}
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              style={inputStyle}
              required
            />
          </label>
          {error && <p role="alert" style={{ color: 'var(--color-danger)', fontSize: 13 }}>{error}</p>}
          <Button type="submit" variant="primary" fullWidth disabled={submitting}>
            {submitting ? t('common.loading') : t('login.submit')}
          </Button>
        </form>

      </Card>
    </div>
  )
}

const inputStyle: CSSProperties = {
  padding: '10px 12px',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--color-border-strong)',
  background: 'var(--color-surface)',
}
