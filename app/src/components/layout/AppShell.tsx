import { useState, type ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileNav } from './MobileNav'
import { MobileMenu } from './MobileMenu'
import { useI18n } from '@/i18n'
import { Link, useRouter } from '@/router'
import { NavIcon } from '@/components/ui/NavIcon'

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { path } = useRouter()
  const { t } = useI18n()
  const adminPaths = new Set(['/users', '/audit', '/settings'])
  const showQuickAdd = path !== '/add' && !adminPaths.has(path)

  return (
    <div className="app-shell">
      <div className="desktop-sidebar">
        <Sidebar />
      </div>
      <div className="app-shell-body">
        <TopBar title={title} onMenuClick={() => setMenuOpen(true)} />
        <main className="app-content">
          <div className="page-heading">
            <h1>{title}</h1>
            <div className="page-breadcrumb"><span>Home</span><b>›</b><span>{title}</span></div>
          </div>
          {children}
        </main>
      </div>
      {showQuickAdd && (
        <Link
          to="/add"
          className="floating-add-button"
          aria-label={t('nav.add')}
          onClick={() => window.sessionStorage.setItem('moliya:add-return', path)}
        >
          <NavIcon name="plus" size={19} />
          <span>{t('nav.add')}</span>
        </Link>
      )}
      <MobileNav />
      <MobileMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
    </div>
  )
}
