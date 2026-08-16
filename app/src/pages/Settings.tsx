import { useEffect, useState } from 'react'
import { useI18n } from '@/i18n'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { MockNotice } from '@/components/ui/MockNotice'
import { LoadingState } from '@/components/ui/States'
import { mockApi } from '@/lib/mock/mockApi'
import { moliyaApi, type HealthResponse } from '@/lib/apiClient'
import type { AppUser, Category } from '@/lib/types'

export function SettingsPage() {
  const { t, locale } = useI18n()
  const [users, setUsers] = useState<AppUser[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState(false)

  useEffect(() => {
    Promise.all([mockApi.listUsers(), mockApi.listCategories()]).then(([u, c]) => {
      setUsers(u)
      setCategories(c)
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    moliyaApi
      .health()
      .then((response) => {
        setHealth(response)
        setHealthError(false)
      })
      .catch(() => {
        setHealth(null)
        setHealthError(true)
      })
  }, [])

  const categoryLabel = (c: Category) => (locale === 'ru' ? c.name_ru : locale === 'en' ? c.name_en : c.name_uz)

  return (
    <AppShell title={t('settings.title')}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        <Card>
          <h3 style={{ marginBottom: 8 }}>{t('settings.business')}</h3>
          <MockNotice note="Biznes profilini tahrirlash uchun API yo'q." />
        </Card>

        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <h3>{t('settings.users')}</h3>
          </div>
          <MockNotice note="GET /v1/users hali mavjud emas." />
          {loading ? (
            <LoadingState />
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {users.map((u) => (
                <li key={u.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
                  <span>{u.full_name}</span>
                  <Badge tone="neutral">{u.role}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h3 style={{ marginBottom: 8 }}>{t('settings.categories')}</h3>
          <MockNotice note="GET /v1/categories hali mavjud emas." />
          {loading ? (
            <LoadingState />
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {categories.map((c) => (
                <Badge key={c.id} tone="primary">{categoryLabel(c)}</Badge>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h3 style={{ marginBottom: 8 }}>{t('settings.currency')}</h3>
          <p style={{ fontSize: 13.5, color: 'var(--color-text-secondary)' }}>UZS \u2014 MVP faqat shu valyutani qo'llab-quvvatlaydi (domain.py talabi).</p>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 8 }}>{t('settings.sheets')}</h3>
          {healthError ? (
            <Badge tone="danger">{t('settings.sheetsUnavailable')}</Badge>
          ) : !health ? (
            <span style={{ color: 'var(--color-text-muted)', fontSize: 13.5 }}>{t('common.loading')}</span>
          ) : health.sheet_mode === 'google' ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <Badge tone="success">{t('settings.sheetsConnected')}</Badge>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 12.5 }}>
                {t('settings.parserMode')}: {health.parser_mode}
              </span>
            </div>
          ) : (
            <Badge tone="amber">{t('settings.sheetsMemory')}</Badge>
          )}
        </Card>
      </div>
    </AppShell>
  )
}
