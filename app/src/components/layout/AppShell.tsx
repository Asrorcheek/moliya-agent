import { useState, type ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileNav } from './MobileNav'
import { MobileMenu } from './MobileMenu'

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)

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
      <MobileNav />
      <MobileMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
    </div>
  )
}
