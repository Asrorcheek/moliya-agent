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

const fieldStyle: CSSProperties = {
  width: '100%', minWidth: 0, padding: '9px 11px', border: '1px solid var(--color-border-strong)',
  borderRadius: 'var(--radius-md)', background: 'var(--color-surface)', color: 'var(--color-text-primary)',
}

const labelStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: 6, color: 'var(--color-text-secondary)', fontSize: 13 }

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
  const [editBusiness, setEditBusiness] = useState(false)
  const [editUserId, setEditUserId] = useState<string | null>(null)
  const [showAddUser, setShowAddUser] = useState(false)
  const [manageCategories, setManageCategories] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)
  const [newUser, setNewUser] = useState<{ full_name: string; role: UserRole }>({ full_name: '', role: 'manager' })
  const [newCategoryName, setNewCategoryName] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try { setSettings(await moliyaApi.getSettings()) }
    catch (error) { setLoadError(errorMessage(error)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  const success = () => setNotice({ tone: 'success', text: t('settings.saved') })
  const failure = (error: unknown) => setNotice({ tone: 'danger', text: errorMessage(error) })

  const saveBusiness = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings) return
    setBusy('business'); setNotice(null)
    try {
      const response = await moliyaApi.updateBusiness(settings.business)
      setSettings({ ...settings, business: response.business }); setEditBusiness(false); success()
    } catch (error) { failure(error) }
    finally { setBusy(null) }
  }

  const addUser = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings || !newUser.full_name.trim()) return
    setBusy('new-user'); setNotice(null)
    try {
      const response = await moliyaApi.createUser({ ...newUser, full_name: newUser.full_name.trim() })
      setSettings({ ...settings, users: [...settings.users, response.user] })
      setNewUser({ full_name: '', role: 'manager' }); setShowAddUser(false); success()
    } catch (error) { failure(error) }
    finally { setBusy(null) }
  }

  const saveUser = async (user: AppUser) => {
    if (!settings || !user.full_name.trim()) return
    setBusy(`user-${user.id}`); setNotice(null)
    try {
      const response = await moliyaApi.updateUser(user.id, { full_name: user.full_name.trim(), role: user.role })
      setSettings({ ...settings, users: settings.users.map((item) => item.id === user.id ? response.user : item) })
      setEditUserId(null); success()
    } catch (error) { failure(error) }
    finally { setBusy(null) }
  }

  const addCategory = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings || !newCategoryName.trim()) return
    setBusy('new-category'); setNotice(null)
    const name = newCategoryName.trim()
    try {
      const response = await moliyaApi.createCategory({ name_uz: name, name_ru: name, name_en: name })
      setSettings({ ...settings, categories: [...settings.categories, response.category] })
      setNewCategoryName(''); success()
    } catch (error) { failure(error) }
    finally { setBusy(null) }
  }

  const saveCategory = async (category: Category) => {
    if (!settings) return
    setBusy(`category-${category.id}`); setNotice(null)
    try {
      const response = await moliyaApi.updateCategory(category.id, category)
      setSettings({ ...settings, categories: settings.categories.map((item) => item.id === category.id ? response.category : item) })
      success()
    } catch (error) { failure(error) }
    finally { setBusy(null) }
  }

  const confirmDelete = async () => {
    if (!settings || !deleteTarget) return
    try {
      if (deleteTarget.kind === 'user') {
        await moliyaApi.deleteUser(deleteTarget.item.id)
        setSettings({ ...settings, users: settings.users.filter((item) => item.id !== deleteTarget.item.id) })
      } else {
        await moliyaApi.deleteCategory(deleteTarget.item.id)
        setSettings({ ...settings, categories: settings.categories.filter((item) => item.id !== deleteTarget.item.id) })
      }
      setDeleteTarget(null); success()
    } catch (error) { failure(error); throw error }
  }

  const patchUser = (id: string, patch: Partial<AppUser>) => settings && setSettings({ ...settings, users: settings.users.map((item) => item.id === id ? { ...item, ...patch } : item) })
  const patchCategory = (id: string, name: string) => {
    if (!settings) return
    const key = locale === 'ru' ? 'name_ru' : locale === 'en' ? 'name_en' : 'name_uz'
    setSettings({ ...settings, categories: settings.categories.map((item) => item.id === id ? { ...item, [key]: name } : item) })
  }
  const categoryLabel = (category: Category) => locale === 'ru' ? category.name_ru : locale === 'en' ? category.name_en : category.name_uz
  const roleLabel = (role: UserRole) => role === 'owner' ? t('settings.roleOwner') : role === 'manager' ? t('settings.roleManager') : t('settings.roleAccountant')

  if (loading) return <AppShell title={t('settings.title')}><LoadingState /></AppShell>
  if (loadError || !settings) return <AppShell title={t('settings.title')}><ErrorState description={loadError ?? undefined} onRetry={load} /></AppShell>

  return (
    <AppShell title={t('settings.title')}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', maxWidth: 920 }}>
        {notice && <div aria-live="polite"><Badge tone={notice.tone}>{notice.text}</Badge></div>}

        <div className="settings-overview-grid">
          <Card>
            <div className="card-heading-row">
              <div>
                <h3>{t('settings.business')}</h3>
                {!editBusiness && <p style={{ marginTop: 5, color: 'var(--color-text-secondary)', fontSize: 13 }}>{settings.business.name}</p>}
              </div>
              {!editBusiness && <Button type="button" variant="ghost" onClick={() => setEditBusiness(true)}>{t('settings.edit')}</Button>}
            </div>
            {editBusiness ? (
              <form onSubmit={saveBusiness} className="settings-form-grid" style={{ marginTop: 'var(--space-4)' }}>
                <label style={labelStyle}>{t('settings.businessName')}<input required value={settings.business.name} onChange={(event) => setSettings({ ...settings, business: { ...settings.business, name: event.target.value } })} style={fieldStyle} /></label>
                <label style={labelStyle}>{t('settings.phone')}<input value={settings.business.phone} onChange={(event) => setSettings({ ...settings, business: { ...settings.business, phone: event.target.value } })} style={fieldStyle} placeholder="+998 90 123 45 67" /></label>
                <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>{t('settings.address')}<input value={settings.business.address} onChange={(event) => setSettings({ ...settings, business: { ...settings.business, address: event.target.value } })} style={fieldStyle} /></label>
                <div style={{ display: 'flex', gap: 8, gridColumn: '1 / -1' }}>
                  <Button type="submit" variant="primary" disabled={busy === 'business'}>{t('common.save')}</Button>
                  <Button type="button" variant="ghost" onClick={() => { setEditBusiness(false); void load() }}>{t('common.cancel')}</Button>
                </div>
              </form>
            ) : (
              <div className="business-summary">
                <SummaryItem label={t('settings.phone')} value={settings.business.phone || '—'} />
                <SummaryItem label={t('settings.address')} value={settings.business.address || '—'} />
              </div>
            )}
          </Card>

          <Card>
            <h3>{t('settings.system')}</h3>
            <div className="system-summary">
              <SummaryItem label="Google Sheets" value={settings.integration.connected ? t('settings.sheetsConnected') : t('settings.sheetsMemory')} success={settings.integration.connected} />
              <SummaryItem label={t('settings.parserMode')} value={settings.integration.parser_mode} />
              <SummaryItem label={t('settings.currency')} value="UZS" />
              {settings.integration.spreadsheet_url && <a href={settings.integration.spreadsheet_url} target="_blank" rel="noreferrer" style={{ fontSize: 13.5 }}>{t('settings.openSheet')}</a>}
            </div>
          </Card>
        </div>

        <Card>
          <div className="card-heading-row">
            <div><h3>{t('settings.users')}</h3><p className="section-count">{settings.users.length}</p></div>
            <Button type="button" variant={showAddUser ? 'ghost' : 'secondary'} onClick={() => setShowAddUser(!showAddUser)}>{showAddUser ? t('common.cancel') : `+ ${t('settings.addUser')}`}</Button>
          </div>
          {showAddUser && (
            <form onSubmit={addUser} className="settings-add-row settings-inline-form">
              <input required minLength={2} value={newUser.full_name} onChange={(event) => setNewUser({ ...newUser, full_name: event.target.value })} placeholder={t('settings.fullName')} style={fieldStyle} autoFocus />
              <select value={newUser.role} onChange={(event) => setNewUser({ ...newUser, role: event.target.value as UserRole })} style={fieldStyle}><option value="manager">{t('settings.roleManager')}</option><option value="accountant">{t('settings.roleAccountant')}</option><option value="owner">{t('settings.roleOwner')}</option></select>
              <Button type="submit" variant="primary" disabled={busy === 'new-user'}>{t('settings.add')}</Button>
            </form>
          )}
          <div className="simple-list">
            {settings.users.map((user) => editUserId === user.id ? (
              <div key={user.id} className="settings-edit-row">
                <input value={user.full_name} onChange={(event) => patchUser(user.id, { full_name: event.target.value })} style={fieldStyle} />
                <select value={user.role} onChange={(event) => patchUser(user.id, { role: event.target.value as UserRole })} style={fieldStyle}><option value="owner">{t('settings.roleOwner')}</option><option value="manager">{t('settings.roleManager')}</option><option value="accountant">{t('settings.roleAccountant')}</option></select>
                <Button type="button" onClick={() => void saveUser(user)}>{t('common.save')}</Button>
                <Button type="button" variant="ghost" onClick={() => { setEditUserId(null); void load() }}>{t('common.cancel')}</Button>
              </div>
            ) : (
              <div key={user.id} className="simple-list-row">
                <div><div style={{ fontWeight: 500 }}>{user.full_name}</div><div style={{ marginTop: 3 }}><Badge tone="neutral">{roleLabel(user.role)}</Badge></div></div>
                <div className="row-actions"><Button type="button" variant="ghost" onClick={() => setEditUserId(user.id)}>{t('settings.edit')}</Button>{(user.role !== 'owner' || settings.users.filter((item) => item.role === 'owner').length > 1) && <Button type="button" variant="ghost" onClick={() => setDeleteTarget({ kind: 'user', item: user })} style={{ color: 'var(--color-danger)' }}>{t('settings.delete')}</Button>}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="card-heading-row">
            <div><h3>{t('settings.categories')}</h3><p className="section-count">{settings.categories.length}</p></div>
            <Button type="button" variant="ghost" onClick={() => setManageCategories(!manageCategories)}>{manageCategories ? t('settings.done') : t('settings.manage')}</Button>
          </div>
          <div className="category-cloud">
            {settings.categories.map((category) => <span key={category.id} className="category-pill">{categoryLabel(category)}{manageCategories && category.is_custom && <button type="button" onClick={() => setDeleteTarget({ kind: 'category', item: category })} aria-label={t('settings.delete')}>×</button>}</span>)}
          </div>
          {manageCategories && (
            <div style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--color-border)' }}>
              {settings.categories.filter((item) => item.is_custom).map((category) => (
                <div key={category.id} className="category-edit-row"><input value={categoryLabel(category)} onChange={(event) => patchCategory(category.id, event.target.value)} style={fieldStyle} /><Button type="button" onClick={() => void saveCategory(category)} disabled={busy === `category-${category.id}`}>{t('common.save')}</Button></div>
              ))}
              <form onSubmit={addCategory} className="category-edit-row">
                <input required value={newCategoryName} onChange={(event) => setNewCategoryName(event.target.value)} placeholder={t('settings.categoryName')} style={fieldStyle} />
                <Button type="submit" variant="primary" disabled={busy === 'new-category'}>{t('settings.add')}</Button>
              </form>
            </div>
          )}
        </Card>
      </div>

      <ConfirmDialog open={deleteTarget !== null} title={t('settings.deleteTitle')} body={t('settings.deleteBody')} confirmLabel={t('settings.delete')} tone="danger" requireAcknowledge={false} onCancel={() => setDeleteTarget(null)} onConfirm={confirmDelete} />
    </AppShell>
  )
}

function SummaryItem({ label, value, success = false }: { label: string; value: string; success?: boolean }) {
  return <div><div style={{ fontSize: 11.5, color: 'var(--color-text-muted)', marginBottom: 2 }}>{label}</div><div style={{ fontSize: 13.5, color: success ? 'var(--color-success-strong)' : 'var(--color-text-primary)' }}>{value}</div></div>
}
