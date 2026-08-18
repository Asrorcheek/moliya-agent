import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { NavIcon } from '@/components/ui/NavIcon'
import { LoadingState } from '@/components/ui/States'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'

export function ProfilePage() {
  const { t } = useI18n()
  const { session, logout } = useAuth()
  if (!session) return <LoadingState />

  const roleLabel = session.role === 'owner'
    ? t('settings.roleOwner')
    : session.role === 'manager'
      ? t('settings.roleManager')
      : t('settings.roleAccountant')

  return (
    <AppShell title={t('profile.title')}>
      <div className="profile-page">
        <Card className="profile-hero-card">
          <div className="profile-avatar">{session.displayName.slice(0, 1).toUpperCase()}</div>
          <div className="profile-identity">
            <h2>{session.displayName}</h2>
            <p>{t('profile.subtitle')}</p>
            <Badge tone="primary">{roleLabel}</Badge>
          </div>
        </Card>

        <Card className="profile-details-card">
          <div className="profile-section-heading">
            <div>
              <h3>{t('profile.accountDetails')}</h3>
              <p>{t('profile.subtitle')}</p>
            </div>
          </div>
          <dl className="profile-details">
            <div><dt>{t('profile.fullName')}</dt><dd>{session.displayName}</dd></div>
            <div><dt>{t('profile.email')}</dt><dd>{session.username}</dd></div>
            <div><dt>{t('profile.role')}</dt><dd>{roleLabel}</dd></div>
          </dl>
          <div className="profile-actions">
            <Button variant="danger" onClick={logout} icon={<NavIcon name="logout" size={18} />}>
              {t('nav.logout')}
            </Button>
          </div>
        </Card>
      </div>
    </AppShell>
  )
}
