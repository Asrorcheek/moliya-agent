import { useI18n } from '@/i18n'
import { Link, useRouter } from '@/router'
import { useAuth } from '@/lib/authContext'

const NAV_ITEMS = [
  { to: '/', key: 'nav.dashboard' as const },
  { to: '/drafts', key: 'nav.drafts' as const },
  { to: '/transactions', key: 'nav.transactions' as const },
  { to: '/add', key: 'nav.add' as const },
  { to: '/reports', key: 'nav.reports' as const },
  { to: '/audit', key: 'nav.audit' as const },
  { to: '/users', key: 'nav.users' as const },
  { to: '/settings', key: 'nav.settings' as const },
]

export function Sidebar() {
  const { t } = useI18n()
  const { path } = useRouter()
  const { session, logout } = useAuth()

  return (
    <aside
      style={{
        width: 'var(--sidebar-width)',
        flexShrink: 0,
        borderRight: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--space-5) var(--space-4)',
        height: '100vh',
        position: 'sticky',
        top: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 var(--space-2)', marginBottom: 'var(--space-6)' }}>
        <LedgerMark />
        <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 500 }}>{t('app.name')}</span>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }} aria-label="Asosiy navigatsiya">
        {NAV_ITEMS.map((item) => {
          const active = path === item.to
          return (
            <Link
              key={item.to}
              to={item.to}
              className="nav-link"
              style={{
                display: 'block',
                padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                fontSize: 14,
                fontWeight: active ? 500 : 400,
                color: active ? 'var(--color-primary-strong)' : 'var(--color-text-secondary)',
                background: active ? 'var(--color-primary-soft)' : 'transparent',
                textDecoration: 'none',
              }}
            >
              {t(item.key)}
            </Link>
          )
        })}
      </nav>

      {session && (
        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: 13.5, color: 'var(--color-text-secondary)' }}>{session.displayName}</div>
          <button
            onClick={logout}
            style={{ textAlign: 'left', background: 'none', border: 'none', color: 'var(--color-text-muted)', fontSize: 13, padding: 0 }}
          >
            {t('nav.logout')}
          </button>
        </div>
      )}
    </aside>
  )
}

function LedgerMark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <rect x="1" y="1" width="24" height="24" rx="6" fill="var(--color-primary)" />
      <path d="M7 17.5 L11 9 L14 15 L19 8" stroke="var(--color-text-on-primary)" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
