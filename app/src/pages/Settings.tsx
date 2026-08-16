import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from 'react'
import { useI18n } from '@/i18n'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { ApiError, moliyaApi } from '@/lib/apiClient'
import type { AppSettings, AppUser, Category, UserRole } from '@/lib/types'

type DeleteTarget = { kind: 'user'; item: AppUser } | { kind: 'category'; item: Category }

const inputStyle: CSSProperties = {
  width: '100%',
  minWidth: 0,
  padding: '9px 11px',
  border: '1px solid var(--color-border-strong)',
  borderRadius: 'var(--radius-md)',
  background: 'var(--color-surface)',
  color: 'var(--color-text-primary)',
}

const labelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  color: 'var(--color-text-secondary)',
  fontSize: 13,
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Backend bilan aloqa xatosi'
}

export function SettingsPage() {
  const { t, locale } = useI18n()
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)
  const [newUser, setNewUser] = useState<{ full_name: string; role: UserRole }>({ full_name: '', role: 'manager' })
  const [newCategory, setNewCategory] = useState({ name_uz: '', name_ru: '', name_en: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      setSettings(await moliyaApi.getSettings())
    } catch (error) {
      setLoadError(errorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const showSuccess = () => setNotice({ tone: 'success', text: t('settings.saved') })
  const showError = (error: unknown) => setNotice({ tone: 'danger', text: errorMessage(error) })

  const saveBusiness = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings) return
    setBusy('business')
    setNotice(null)
    try {
      const response = await moliyaApi.updateBusiness(settings.business)
      setSettings({ ...settings, business: response.business })
      showSuccess()
    } catch (error) {
      showError(error)
    } finally {
      setBusy(null)
    }
  }

  const addUser = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings || !newUser.full_name.trim()) return
    setBusy('new-user')
    setNotice(null)
    try {
      const response = await moliyaApi.createUser({ ...newUser, full_name: newUser.full_name.trim() })
      setSettings({ ...settings, users: [...settings.users, response.user] })
      setNewUser({ full_name: '', role: 'manager' })
      showSuccess()
    } catch (error) {
      showError(error)
    } finally {
      setBusy(null)
    }
  }

  const saveUser = async (user: AppUser) => {
    if (!settings || !user.full_name.trim()) return
    setBusy(`user-${user.id}`)
    setNotice(null)
    try {
      const response = await moliyaApi.updateUser(user.id, {
        full_name: user.full_name.trim(),
        role: user.role,
      })
      setSettings({
        ...settings,
        users: settings.users.map((item) => (item.id === user.id ? response.user : item)),
      })
      showSuccess()
    } catch (error) {
      showError(error)
    } finally {
      setBusy(null)
    }
  }

  const addCategory = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings || Object.values(newCategory).some((value) => !value.trim())) return
    setBusy('new-category')
    setNotice(null)
    try {
      const input = {
        name_uz: newCategory.name_uz.trim(),
        name_ru: newCategory.name_ru.trim(),
        name_en: newCategory.name_en.trim(),
      }
      const response = await moliyaApi.createCategory(input)
      setSettings({ ...settings, categories: [...settings.categories, response.category] })
      setNewCategory({ name_uz: '', name_ru: '', name_en: '' })
      showSuccess()
    } catch (error) {
      showError(error)
    } finally {
      setBusy(null)
    }
  }

  const saveCategory = async (category: Category) => {
    if (!settings) return
    setBusy(`category-${category.id}`)
    setNotice(null)
    try {
      const response = await moliyaApi.updateCategory(category.id, category)
      setSettings({
        ...settings,
        categories: settings.categories.map((item) =>
          item.id === category.id ? response.category : item,
        ),
      })
      showSuccess()
    } catch (error) {
      showError(error)
    } finally {
      setBusy(null)
    }
  }

  const confirmDelete = async () => {
    if (!settings || !deleteTarget) return
    const target = deleteTarget
    setNotice(null)
    try {
      if (target.kind === 'user') {
        await moliyaApi.deleteUser(target.item.id)
        setSettings({ ...settings, users: settings.users.filter((item) => item.id !== target.item.id) })
      } else {
        await moliyaApi.deleteCategory(target.item.id)
        setSettings({ ...settings, categories: settings.categories.filter((item) => item.id !== target.item.id) })
      }
      setDeleteTarget(null)
      showSuccess()
    } catch (error) {
      showError(error)
      throw error
    }
  }

  const patchUser = (id: string, patch: Partial<AppUser>) => {
    if (!settings) return
    setSettings({ ...settings, users: settings.users.map((item) => (item.id === id ? { ...item, ...patch } : item)) })
  }

  const patchCategory = (id: string, patch: Partial<Category>) => {
    if (!settings) return
    setSettings({ ...settings, categories: settings.categories.map((item) => (item.id === id ? { ...item, ...patch } : item)) })
  }

  const categoryLabel = (category: Category) =>
    locale === 'ru' ? category.name_ru : locale === 'en' ? category.name_en : category.name_uz

  if (loading) return <AppShell title={t('settings.title')}><LoadingState /></AppShell>
  if (loadError || !settings) {
    return <AppShell title={t('settings.title')}><ErrorState description={loadError ?? undefined} onRetry={load} /></AppShell>
  }

  return (
    <AppShell title={t('settings.title')}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        {notice && (
          <div aria-live="polite">
            <Badge tone={notice.tone}>{notice.text}</Badge>
          </div>
        )}

        <Card>
          <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('settings.business')}</h3>
          <form onSubmit={saveBusiness} className="settings-form-grid">
            <label style={labelStyle}>
              {t('settings.businessName')}
              <input
                required
                maxLength={160}
                value={settings.business.name}
                onChange={(event) => setSettings({ ...settings, business: { ...settings.business, name: event.target.value } })}
                style={inputStyle}
              />
            </label>
            <label style={labelStyle}>
              {t('settings.phone')}
              <input
                maxLength={64}
                value={settings.business.phone}
                onChange={(event) => setSettings({ ...settings, business: { ...settings.business, phone: event.target.value } })}
                style={inputStyle}
                placeholder="+998 90 123 45 67"
              />
            </label>
            <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
              {t('settings.address')}
              <input
                maxLength={300}
                value={settings.business.address}
                onChange={(event) => setSettings({ ...settings, business: { ...settings.business, address: event.target.value } })}
                style={inputStyle}
              />
            </label>
            <label style={labelStyle}>
              {t('settings.timezone')}
              <input disabled value="Asia/Tashkent (UTC+5)" style={{ ...inputStyle, opacity: 0.7 }} />
            </label>
            <div style={{ alignSelf: 'end' }}>
              <Button type="submit" variant="primary" disabled={busy === 'business'}>
                {busy === 'business' ? t('settings.saving') : t('common.save')}
              </Button>
            </div>
          </form>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('settings.users')}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {settings.users.map((user) => (
              <div key={user.id} className="settings-list-row">
                <input
                  aria-label={t('settings.fullName')}
                  value={user.full_name}
                  onChange={(event) => patchUser(user.id, { full_name: event.target.value })}
                  style={inputStyle}
                  maxLength={160}
                />
                <select
                  aria-label={t('settings.role')}
                  value={user.role}
                  onChange={(event) => patchUser(user.id, { role: event.target.value as UserRole })}
                  style={inputStyle}
                >
                  <option value="owner">{t('settings.roleOwner')}</option>
                  <option value="manager">{t('settings.roleManager')}</option>
                  <option value="accountant">{t('settings.roleAccountant')}</option>
                </select>
                <Badge tone={user.telegram_linked ? 'success' : 'neutral'}>
                  {user.telegram_linked ? t('settings.telegramLinked') : t('settings.telegramNotLinked')}
                </Badge>
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button type="button" onClick={() => void saveUser(user)} disabled={busy === `user-${user.id}`} style={{ padding: '8px 11px' }}>
                    {t('common.save')}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setDeleteTarget({ kind: 'user', item: user })} style={{ padding: '8px 11px', color: 'var(--color-danger)' }}>
                    {t('settings.delete')}
                  </Button>
                </div>
              </div>
            ))}
          </div>
          <form onSubmit={addUser} className="settings-add-row">
            <input
              required
              minLength={2}
              maxLength={160}
              value={newUser.full_name}
              onChange={(event) => setNewUser({ ...newUser, full_name: event.target.value })}
              placeholder={t('settings.fullName')}
              style={inputStyle}
            />
            <select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value as UserRole })} style={inputStyle}>
              <option value="manager">{t('settings.roleManager')}</option>
              <option value="accountant">{t('settings.roleAccountant')}</option>
              <option value="owner">{t('settings.roleOwner')}</option>
            </select>
            <Button type="submit" variant="primary" disabled={busy === 'new-user'}>{t('settings.addUser')}</Button>
          </form>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 'var(--space-4)' }}>{t('settings.categories')}</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 'var(--space-4)' }}>
            {settings.categories.filter((category) => !category.is_custom).map((category) => (
              <Badge key={category.id} tone="primary">{categoryLabel(category)}</Badge>
            ))}
          </div>
          {settings.categories.filter((category) => category.is_custom).map((category) => (
            <div key={category.id} className="settings-category-row">
              <input aria-label="O‘zbekcha" value={category.name_uz} onChange={(event) => patchCategory(category.id, { name_uz: event.target.value })} style={inputStyle} />
              <input aria-label="Русский" value={category.name_ru} onChange={(event) => patchCategory(category.id, { name_ru: event.target.value })} style={inputStyle} />
              <input aria-label="English" value={category.name_en} onChange={(event) => patchCategory(category.id, { name_en: event.target.value })} style={inputStyle} />
              <div style={{ display: 'flex', gap: 6 }}>
                <Button type="button" onClick={() => void saveCategory(category)} disabled={busy === `category-${category.id}`} style={{ padding: '8px 11px' }}>{t('common.save')}</Button>
                <Button type="button" variant="ghost" onClick={() => setDeleteTarget({ kind: 'category', item: category })} style={{ padding: '8px 11px', color: 'var(--color-danger)' }}>{t('settings.delete')}</Button>
              </div>
            </div>
          ))}
          <form onSubmit={addCategory} className="settings-category-row" style={{ paddingTop: 12, borderTop: '1px solid var(--color-border)' }}>
            <input required value={newCategory.name_uz} onChange={(event) => setNewCategory({ ...newCategory, name_uz: event.target.value })} placeholder={t('settings.nameUz')} style={inputStyle} />
            <input required value={newCategory.name_ru} onChange={(event) => setNewCategory({ ...newCategory, name_ru: event.target.value })} placeholder={t('settings.nameRu')} style={inputStyle} />
            <input required value={newCategory.name_en} onChange={(event) => setNewCategory({ ...newCategory, name_en: event.target.value })} placeholder={t('settings.nameEn')} style={inputStyle} />
            <Button type="submit" variant="primary" disabled={busy === 'new-category'}>{t('settings.addCategory')}</Button>
          </form>
        </Card>

        <div className="settings-two-columns">
          <Card>
            <h3 style={{ marginBottom: 8 }}>{t('settings.currency')}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Badge tone="primary">UZS</Badge>
              <span style={{ fontSize: 13.5, color: 'var(--color-text-secondary)' }}>{t('settings.currencyHint')}</span>
            </div>
          </Card>
          <Card>
            <h3 style={{ marginBottom: 8 }}>{t('settings.sheets')}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <Badge tone={settings.integration.connected ? 'success' : 'amber'}>
                {settings.integration.connected ? t('settings.sheetsConnected') : t('settings.sheetsMemory')}
              </Badge>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 12.5 }}>
                {t('settings.parserMode')}: {settings.integration.parser_mode}
              </span>
              {settings.integration.spreadsheet_url && (
                <a href={settings.integration.spreadsheet_url} target="_blank" rel="noreferrer" style={{ fontSize: 13.5 }}>
                  {t('settings.openSheet')}
                </a>
              )}
            </div>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t('settings.deleteTitle')}
        body={t('settings.deleteBody')}
        confirmLabel={t('settings.delete')}
        tone="danger"
        requireAcknowledge={false}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
      />
    </AppShell>
  )
}
