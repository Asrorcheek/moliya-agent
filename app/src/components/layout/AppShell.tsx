import { useState, type ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileNav } from './MobileNav'
import { MobileMenu } from './MobileMenu'

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <div className="desktop-sidebar">
        <Sidebar />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <TopBar title={title} onMenuClick={() => setMenuOpen(true)} />
        <main style={{ padding: 'var(--space-5)', paddingBottom: 88, maxWidth: 1180, margin: '0 auto' }}>
          {children}
        </main>
      </div>
      <MobileNav />
      <MobileMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
    </div>
  )
}
