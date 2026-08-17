import { useEffect, useRef } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { Link, useRouter } from '@/router'
import { NavIcon } from '@/components/ui/NavIcon'

const ITEMS = [
  { to: '/', key: 'nav.dashboard' as const, icon: 'home' as const },
  { to: '/drafts', key: 'nav.drafts' as const, icon: 'clock' as const },
  { to: '/transactions', key: 'nav.transactions' as const, icon: 'list' as const },
  { to: '/add', key: 'nav.add' as const, icon: 'plus' as const },
  { to: '/reports', key: 'nav.reports' as const, icon: 'chart' as const },
  { to: '/audit', key: 'nav.audit' as const, icon: 'history' as const },
  { to: '/users', key: 'nav.users' as const, icon: 'users' as const },
  { to: '/settings', key: 'nav.settings' as const, icon: 'settings' as const },
]

export function MobileMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n()
  const { path } = useRouter()
  const { session, logout } = useAuth()
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement as HTMLElement | null
    closeButtonRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKeyDown)
      previousFocus?.focus()
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="mobile-menu-overlay" onClick={onClose}>
      <aside
        aria-label="Mobil menyu"
        className="mobile-menu-panel"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mobile-menu-heading">
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 18 }}>{t('app.name')}</span>
          <button ref={closeButtonRef} onClick={onClose} aria-label={t('common.close')} className="icon-button">
            <NavIcon name="close" />
          </button>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {ITEMS.map((item) => {
            const active = path === item.to
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={onClose}
                aria-current={active ? 'page' : undefined}
                className="mobile-menu-link"
                style={{
                  color: active ? 'var(--color-primary-strong)' : 'var(--color-text-secondary)',
                  background: active ? 'var(--color-primary-soft)' : 'transparent',
                }}
              >
                <NavIcon name={item.icon} />
                {t(item.key)}
              </Link>
            )
          })}
        </nav>

        {session && (
          <div className="mobile-menu-account">
            <span>{session.displayName}</span>
            <button
              onClick={() => {
                logout()
                onClose()
              }}
            >
              <NavIcon name="logout" size={18} />
              {t('nav.logout')}
            </button>
          </div>
        )}
      </aside>
    </div>
  )
}
