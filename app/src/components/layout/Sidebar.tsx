import { useI18n } from '@/i18n'
import { Link, useRouter } from '@/router'
import { useAuth } from '@/lib/authContext'
import { NavIcon } from '@/components/ui/NavIcon'

const NAV_ITEMS = [
  { to: '/', key: 'nav.dashboard' as const, icon: 'home' as const, group: 'ASOSIY' },
  { to: '/drafts', key: 'nav.drafts' as const, icon: 'clock' as const, group: 'MOLIYA' },
  { to: '/transactions', key: 'nav.transactions' as const, icon: 'list' as const, group: 'MOLIYA' },
  { to: '/add', key: 'nav.add' as const, icon: 'plus' as const, group: 'MOLIYA' },
  { to: '/reports', key: 'nav.reports' as const, icon: 'chart' as const, group: 'MOLIYA' },
  { to: '/users', key: 'nav.users' as const, icon: 'users' as const, group: 'ADMIN' },
  { to: '/audit', key: 'nav.audit' as const, icon: 'history' as const, group: 'ADMIN' },
  { to: '/settings', key: 'nav.settings' as const, icon: 'settings' as const, group: 'ADMIN' },
]

export function Sidebar() {
  const { t } = useI18n()
  const { path } = useRouter()
  const { session, logout } = useAuth()

  return (
    <aside className="metronic-sidebar">
      <div className="sidebar-logo">
        <LedgerMark />
        <span>{t('app.name')}</span>
      </div>

      <nav className="sidebar-nav" aria-label="Asosiy navigatsiya">
        {NAV_ITEMS.map((item, index) => {
          const active = path === item.to
          return (
            <div key={item.to}>
              {(index === 0 || NAV_ITEMS[index - 1].group !== item.group) && <div className="sidebar-group-label">{item.group}</div>}
              <Link to={item.to} className={`nav-link ${active ? 'active' : ''}`}>
                <NavIcon name={item.icon} size={18} />
                <span>{t(item.key)}</span>
                <b>›</b>
              </Link>
            </div>
          )
        })}
      </nav>

      {session && (
        <div className="sidebar-account">
          <span className="sidebar-account-avatar">{session.displayName.slice(0, 1).toUpperCase()}</span>
          <div><strong>{session.displayName}</strong>
          <button
            onClick={logout}
          >
            {t('nav.logout')}
          </button>
          </div>
        </div>
      )}
    </aside>
  )
}

function LedgerMark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <path d="M3 19 8.5 5h4L8 19H3Zm9 0 4.2-11 6.8 11h-5l-2.2-4-1.5 4H12Z" fill="#ff2f6d" />
    </svg>
  )
}
