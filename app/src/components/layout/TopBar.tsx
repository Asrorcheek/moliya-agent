import { useI18n, type Locale } from '@/i18n'
import { NavIcon } from '@/components/ui/NavIcon'
import { Link, useRouter } from '@/router'
import { useAuth } from '@/lib/authContext'

const LOCALES: Locale[] = ['uz', 'ru', 'en']

export function TopBar({ title, onMenuClick }: { title: string; onMenuClick?: () => void }) {
  const { locale, setLocale, t } = useI18n()
  const { path } = useRouter()
  const { session } = useAuth()

  return (
    <header className="metronic-topbar">
      <div className="topbar-left">
        {onMenuClick && (
          <button
            aria-label="Menyu"
            onClick={onMenuClick}
            className="mobile-menu-button"
            style={{ background: 'none', border: 'none', padding: 6, display: 'none' }}
          >
            <NavIcon name="menu" />
          </button>
        )}
        <h1 className="topbar-title">{title}</h1>
        <nav className="topbar-nav" aria-label="Tezkor navigatsiya">
          <Link to="/" className={path === '/' ? 'active' : ''}>Home</Link>
          <Link to="/reports" className={path === '/reports' ? 'active' : ''}>{t('nav.reports')}</Link>
          {session?.role === 'owner' && <Link to="/users" className={path === '/users' ? 'active' : ''}>{t('nav.users')}</Link>}
          {session?.role === 'owner' && <Link to="/settings" className={path === '/settings' ? 'active' : ''}>{t('nav.settings')}</Link>}
        </nav>
      </div>

      <div className="topbar-actions">
        <button className="topbar-icon" aria-label={t('common.search')}>⌕</button>
        <span className="topbar-status-dot" title="Online" />
        <div role="group" aria-label="Til tanlash" className="locale-switcher">
        {LOCALES.map((l) => (
          <button
            key={l}
            onClick={() => setLocale(l)}
            aria-pressed={locale === l}
            className={locale === l ? 'active' : ''}
          >
            <span className="locale-full">{t(`lang.${l}` as const)}</span>
            <span className="locale-short">{l.toUpperCase()}</span>
          </button>
        ))}
        </div>
        <span className="topbar-avatar">{session?.displayName.slice(0, 1).toUpperCase() ?? 'A'}</span>
      </div>
    </header>
  )
}
