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
import { UsersPage } from '@/pages/Users'
import { LoadingState, PermissionDeniedState } from '@/components/ui/States'
import { AppShell } from '@/components/layout/AppShell'
import { useI18n } from '@/i18n'

const ROUTES: Record<string, () => ReactElement> = {
  '/': DashboardPage,
  '/drafts': DraftsPage,
  '/transactions': TransactionsPage,
  '/add': AddTransactionPage,
  '/reports': ReportsPage,
  '/audit': AuditLogPage,
  '/users': UsersPage,
  '/settings': SettingsPage,
}

export function App() {
  const { session, loading } = useAuth()
  const { path } = useRouter()
  const { t } = useI18n()

  if (loading) return <LoadingState />
  if (!session) return <LoginPage />
  if (session.role !== 'owner' && ['/users', '/audit', '/settings'].includes(path)) {
    return <AppShell title={t('state.permissionDenied')}><PermissionDeniedState /></AppShell>
  }

  const Page = ROUTES[path] ?? DashboardPage
  return <Page />
}
