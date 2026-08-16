import type { ReactElement } from 'react'
import { useAuth } from '@/lib/authContext'
import { useRouter } from '@/router'
import { LoginPage } from '@/pages/Login'
import { DashboardPage } from '@/pages/Dashboard'
import { DraftsPage } from '@/pages/Drafts'
import { TransactionsPage } from '@/pages/Transactions'
import { AddTransactionPage } from '@/pages/AddTransaction'
import { ReportsPage } from '@/pages/Reports'
import { AuditLogPage } from '@/pages/AuditLog'
import { SettingsPage } from '@/pages/Settings'
import { LoadingState } from '@/components/ui/States'

const ROUTES: Record<string, () => ReactElement> = {
  '/': DashboardPage,
  '/drafts': DraftsPage,
  '/transactions': TransactionsPage,
  '/add': AddTransactionPage,
  '/reports': ReportsPage,
  '/audit': AuditLogPage,
  '/settings': SettingsPage,
}

export function App() {
  const { session, loading } = useAuth()
  const { path } = useRouter()

  if (loading) return <LoadingState />
  if (!session) return <LoginPage />

  const Page = ROUTES[path] ?? DashboardPage
  return <Page />
}
