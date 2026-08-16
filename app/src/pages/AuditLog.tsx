import { useEffect, useState } from 'react'
import { useI18n } from '@/i18n'
import { useAuth } from '@/lib/authContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { moliyaApi } from '@/lib/apiClient'
import type { AuditEvent, AuditEventType } from '@/lib/types'
import { formatDateTime } from '@/lib/format'

const TONE_MAP: Record<AuditEventType, 'success' | 'danger' | 'amber' | 'neutral'> = {
  draft_created: 'neutral',
  draft_confirmed: 'success',
  draft_rejected: 'danger',
  sheet_write_succeeded: 'success',
  sheet_write_failed: 'danger',
  reversal_created: 'amber',
}

export function AuditLogPage() {
  const { t } = useI18n()
  const { session } = useAuth()
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const load = () => {
    if (!session) return
    setStatus('loading')
    moliyaApi
      .listAuditEvents(session.actorId)
      .then((res) => {
        setEvents(res)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }

  useEffect(load, [session]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AppShell title={t('audit.title')}>
      {status === 'loading' && <LoadingState />}
      {status === 'error' && <ErrorState onRetry={load} />}
      {status === 'ready' && events.length === 0 && <EmptyState />}

      {status === 'ready' && events.length > 0 && (
        <Card padded={false}>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {events.map((event) => (
              <li key={event.id} style={{ display: 'flex', gap: 12, padding: 'var(--space-4) var(--space-5)', borderBottom: '1px solid var(--color-border)' }}>
                <Badge tone={TONE_MAP[event.event_type]}>{event.event_type.replaceAll('_', ' ')}</Badge>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14 }}>{event.detail}</div>
                  <div style={{ fontSize: 12.5, color: 'var(--color-text-muted)', marginTop: 2 }}>
                    {event.actor_id} · {formatDateTime(event.occurred_at)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </AppShell>
  )
}
