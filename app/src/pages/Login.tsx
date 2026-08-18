import { useState, type FormEvent } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { Button } from '@/components/ui/Button'

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
    <div className="login-stage">
      <div className="login-card">
        <div className="login-brand">
          <span className="login-mark" aria-hidden="true">
            <svg width="30" height="30" viewBox="0 0 26 26">
              <path d="M3 19 8.5 5h4L8 19H3Zm9 0 4.2-11 6.8 11h-5l-2.2-4-1.5 4H12Z" fill="currentColor" />
            </svg>
          </span>
          <span className="login-wordmark">{t('app.name')}</span>
        </div>

        <h1 className="login-title">{t('login.title')}</h1>
        <p className="login-subtitle">{t('login.subtitle')}</p>

        <form onSubmit={handleSubmit} className="login-form">
          <label className="login-field">
            <span>{t('login.email')}</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              type="text"
              placeholder="manager@company.uz"
              required
            />
          </label>
          <label className="login-field">
            <span>{t('login.password')}</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              required
            />
          </label>
          {error && (
            <p role="alert" className="login-error">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" fullWidth disabled={submitting}>
            {submitting ? t('common.loading') : t('login.submit')}
          </Button>
        </form>
      </div>
    </div>
  )
}
