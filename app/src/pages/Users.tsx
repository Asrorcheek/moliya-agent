import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { useI18n } from '@/i18n'
import { ApiError, moliyaApi } from '@/lib/apiClient'
import type { AppUser, UserRole } from '@/lib/types'

type UserForm = {
  id?: string
  full_name: string
  email: string
  password: string
  role: UserRole
  active: boolean
}

type EditorState = { mode: 'create' | 'edit'; user: UserForm }

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'U'
}

function errorText(error: unknown) {
  return error instanceof ApiError ? error.message : 'Backend bilan aloqa xatosi'
}

function formatJoined(value: string, locale: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  if (locale === 'uz') {
    return `${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}.${date.getFullYear()}`
  }
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)
}

export function UsersPage() {
  const { t, locale } = useI18n()
  const [users, setUsers] = useState<AppUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [role, setRole] = useState<'all' | UserRole>('all')
  const [status, setStatus] = useState<'all' | 'linked' | 'unlinked'>('all')
  const [editor, setEditor] = useState<EditorState | null>(null)
  const [deleteUser, setDeleteUser] = useState<AppUser | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setUsers((await moliyaApi.getSettings()).users) }
    catch (caught) { setError(errorText(caught)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase(locale)
    return users.filter((user) => {
      const matchesQuery = !needle || [user.full_name, user.email].some((value) => value.toLocaleLowerCase(locale).includes(needle))
      const matchesRole = role === 'all' || user.role === role
      const matchesStatus = status === 'all' || (status === 'linked' ? user.telegram_linked : !user.telegram_linked)
      return matchesQuery && matchesRole && matchesStatus
    })
  }, [users, query, role, status, locale])

  const roleLabel = (value: UserRole) => value === 'owner' ? t('settings.roleOwner') : value === 'manager' ? t('settings.roleManager') : t('settings.roleAccountant')
  const owners = users.filter((user) => user.role === 'owner').length

  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!editor || !editor.user.full_name.trim()) return
    setSaving(true); setNotice(null)
    try {
      if (editor.mode === 'create') {
        const response = await moliyaApi.createUser({
          full_name: editor.user.full_name.trim(),
          email: editor.user.email.trim(),
          password: editor.user.password,
          role: editor.user.role,
        })
        setUsers((current) => [...current, response.user])
      } else {
        const response = await moliyaApi.updateUser(editor.user.id ?? '', {
          full_name: editor.user.full_name.trim(),
          email: editor.user.email.trim(),
          password: editor.user.password || undefined,
          role: editor.user.role,
          active: editor.user.active,
        })
        setUsers((current) => current.map((user) => user.id === response.user.id ? response.user : user))
      }
      setEditor(null); setNotice(t('users.saved'))
    } catch (caught) { setError(errorText(caught)) }
    finally { setSaving(false) }
  }

  const remove = async () => {
    if (!deleteUser) return
    await moliyaApi.deleteUser(deleteUser.id)
    setUsers((current) => current.filter((user) => user.id !== deleteUser.id))
    setDeleteUser(null); setNotice(t('users.deleted'))
  }

  if (loading) return <AppShell title={t('users.title')}><LoadingState /></AppShell>
  if (error && users.length === 0) return <AppShell title={t('users.title')}><ErrorState description={error} onRetry={load} /></AppShell>

  return (
    <AppShell title={t('users.title')}>
      <div className="admin-page">
        {notice && <div className="admin-notice" role="status">✓ {notice}</div>}
        {error && <div className="admin-notice admin-notice-danger" role="alert">{error}</div>}

        <section className="user-table-card">
          <div className="user-table-toolbar">
            <label className="user-search"><span aria-hidden="true">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('users.search')} /></label>
            <select value={role} onChange={(event) => setRole(event.target.value as 'all' | UserRole)} aria-label={t('users.filterRole')}>
              <option value="all">{t('users.allRoles')}</option><option value="owner">{t('settings.roleOwner')}</option><option value="manager">{t('settings.roleManager')}</option><option value="accountant">{t('settings.roleAccountant')}</option>
            </select>
            <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)} aria-label={t('users.filterStatus')}>
              <option value="all">{t('users.allUsers')}</option><option value="linked">{t('settings.telegramLinked')}</option><option value="unlinked">{t('settings.telegramNotLinked')}</option>
            </select>
            <Button className="toolbar-add-user" variant="primary" onClick={() => setEditor({ mode: 'create', user: { full_name: '', email: '', password: '', role: 'manager', active: true } })}>+ {t('users.add')}</Button>
          </div>

          <div className="user-table-wrap">
            <table className="user-admin-table">
              <thead><tr><th>{t('users.user')}</th><th>{t('settings.role')}</th><th>{t('users.status')}</th><th>{t('users.telegram')}</th><th>{t('users.joined')}</th><th><span className="visually-hidden">{t('users.actions')}</span></th></tr></thead>
              <tbody>{filtered.map((user) => (
                <tr key={user.id}>
                  <td><UserIdentity user={user} /></td>
                  <td><Badge tone="neutral">{roleLabel(user.role)}</Badge></td>
                  <td>{user.active ? <span className="active-status"><i />{t('users.active')}</span> : <span className="muted-cell">{t('status.rejected')}</span>}</td>
                  <td>{user.telegram_linked ? <Badge tone="success">{t('users.connected')}</Badge> : <span className="muted-cell">{t('users.notConnected')}</span>}</td>
                  <td className="muted-cell">{formatJoined(user.created_at, locale)}</td>
                  <td><div className="user-row-actions"><button type="button" onClick={() => setEditor({ mode: 'edit', user: { ...user, password: '' } })}>{t('settings.edit')}</button>{(user.role !== 'owner' || owners > 1) && <button className="danger-text" type="button" onClick={() => setDeleteUser(user)}>{t('settings.delete')}</button>}</div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>

          <div className="user-mobile-list">
            {filtered.map((user) => <article key={user.id} className="user-mobile-card"><UserIdentity user={user} /><div className="user-mobile-meta"><Badge tone="neutral">{roleLabel(user.role)}</Badge>{user.active && <span className="active-status"><i />{t('users.active')}</span>}</div><div className="user-mobile-actions"><Button variant="ghost" onClick={() => setEditor({ mode: 'edit', user: { ...user, password: '' } })}>{t('settings.edit')}</Button>{(user.role !== 'owner' || owners > 1) && <Button variant="ghost" style={{ color: 'var(--color-danger)' }} onClick={() => setDeleteUser(user)}>{t('settings.delete')}</Button>}</div></article>)}
          </div>

          {filtered.length === 0 && <div className="user-empty-state"><strong>{t('state.empty')}</strong><span>{t('users.emptyHint')}</span></div>}
          <div className="user-table-footer"><span>{t('users.showing')} {filtered.length} / {users.length}</span><span>1 / 1</span></div>
        </section>
      </div>

      {editor && <UserEditor editor={editor} setEditor={setEditor} roleLabel={roleLabel} saving={saving} onSave={save} />}
      <ConfirmDialog open={deleteUser !== null} title={t('users.deleteTitle')} body={t('users.deleteBody')} confirmLabel={t('settings.delete')} tone="danger" requireAcknowledge={false} onCancel={() => setDeleteUser(null)} onConfirm={remove} />
    </AppShell>
  )
}

function UserIdentity({ user }: { user: AppUser }) {
  return <div className="user-identity"><span className="user-avatar">{initials(user.full_name)}</span><div><strong>{user.full_name}</strong><small>{user.email || `ID · ${user.id.slice(0, 8)}`}</small></div></div>
}

function UserEditor({ editor, setEditor, roleLabel, saving, onSave }: { editor: EditorState; setEditor: (value: EditorState | null) => void; roleLabel: (role: UserRole) => string; saving: boolean; onSave: (event: FormEvent) => Promise<void> }) {
  const { t } = useI18n()
  const patch = (value: Partial<UserForm>) => setEditor({ ...editor, user: { ...editor.user, ...value } })
  const generatePassword = () => {
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    const values = crypto.getRandomValues(new Uint8Array(10))
    patch({ password: `Ma7!${[...values].map((value) => alphabet[value % alphabet.length]).join('')}` })
  }
  const valid = editor.user.full_name.trim().length >= 2
    && editor.user.email.includes('@')
    && (editor.mode === 'edit' || editor.user.password.length >= 10)
  return (
    <div className="admin-drawer-overlay" onClick={() => setEditor(null)}>
      <aside className="admin-drawer" role="dialog" aria-modal="true" aria-labelledby="user-editor-title" onClick={(event) => event.stopPropagation()}>
        <div className="admin-drawer-heading"><div><h2 id="user-editor-title">{editor.mode === 'create' ? t('users.add') : t('users.edit')}</h2><p>{t('users.editorHint')}</p></div><button type="button" className="icon-button" aria-label={t('common.close')} onClick={() => setEditor(null)}>×</button></div>
        <form onSubmit={onSave} className="admin-drawer-form">
          <label>{t('settings.fullName')}<input autoFocus required minLength={2} value={editor.user.full_name} onChange={(event) => patch({ full_name: event.target.value })} /></label>
          <label>{t('settings.email')}<input required type="email" autoComplete="username" value={editor.user.email} onChange={(event) => patch({ email: event.target.value })} placeholder="manager@company.uz" /></label>
          <label>{editor.mode === 'create' ? t('settings.password') : t('settings.newPassword')}<div className="password-editor-row"><input required={editor.mode === 'create'} minLength={10} type="text" autoComplete="new-password" value={editor.user.password} onChange={(event) => patch({ password: event.target.value })} /><Button type="button" variant="secondary" onClick={generatePassword}>{t('settings.generatePassword')}</Button></div><small>{t('settings.passwordHint')}</small></label>
          <label>{t('settings.role')}<select value={editor.user.role} onChange={(event) => patch({ role: event.target.value as UserRole })}>{(['owner', 'manager', 'accountant'] as UserRole[]).map((item) => <option key={item} value={item}>{roleLabel(item)}</option>)}</select></label>
          <label className="user-active-toggle"><input type="checkbox" checked={editor.user.active} onChange={(event) => patch({ active: event.target.checked })} />{t('settings.active')}</label>
          <div className="role-help"><strong>{roleLabel(editor.user.role)}</strong><span>{t(`users.roleHelp.${editor.user.role}`)}</span></div>
          <div className="admin-drawer-actions"><Button type="button" variant="ghost" onClick={() => setEditor(null)}>{t('common.cancel')}</Button><Button type="submit" variant="primary" disabled={saving || !valid}>{saving ? t('settings.saving') : t('common.save')}</Button></div>
        </form>
      </aside>
    </div>
  )
}
