import { useI18n } from '@/i18n'
import { Link, useRouter } from '@/router'
import { NavIcon } from '@/components/ui/NavIcon'

const ITEMS = [
  { to: '/', key: 'nav.mobile.dashboard' as const, icon: 'home' as const },
  { to: '/drafts', key: 'nav.mobile.drafts' as const, icon: 'clock' as const },
  { to: '/add', key: 'nav.mobile.add' as const, icon: 'plus' as const },
  { to: '/transactions', key: 'nav.mobile.transactions' as const, icon: 'list' as const },
  { to: '/reports', key: 'nav.mobile.reports' as const, icon: 'chart' as const },
]

export function MobileNav() {
  const { t } = useI18n()
  const { path } = useRouter()
  return (
    <nav
      aria-label="Mobil navigatsiya"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        display: 'none',
        justifyContent: 'space-around',
        background: 'var(--color-surface)',
        borderTop: '1px solid var(--color-border)',
        padding: '6px 4px calc(6px + env(safe-area-inset-bottom))',
        zIndex: 20,
      }}
      className="mobile-nav"
    >
      {ITEMS.map((item) => {
        const active = path === item.to
        return (
          <Link
            key={item.to}
            to={item.to}
            aria-current={active ? 'page' : undefined}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
              padding: '6px 2px',
              fontSize: 10.5,
              lineHeight: 1.2,
              textDecoration: 'none',
              color: active ? 'var(--color-primary)' : 'var(--color-text-muted)',
              width: '20%',
              minWidth: 0,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
            }}
          >
            <NavIcon name={item.icon} />
            {t(item.key)}
          </Link>
        )
      })}
    </nav>
  )
}
