import type { ReactNode } from 'react'

type BadgeTone = 'neutral' | 'success' | 'danger' | 'amber' | 'primary'

const TONE_STYLES: Record<BadgeTone, { bg: string; fg: string }> = {
  neutral: { bg: 'var(--color-border)', fg: 'var(--color-text-secondary)' },
  success: { bg: 'var(--color-success-soft)', fg: 'var(--color-success-strong)' },
  danger: { bg: 'var(--color-danger-soft)', fg: 'var(--color-danger-strong)' },
  amber: { bg: 'var(--color-amber-soft)', fg: 'var(--color-amber-strong)' },
  primary: { bg: 'var(--color-primary-soft)', fg: 'var(--color-primary-strong)' },
}

export function Badge({ tone = 'neutral', icon, children }: { tone?: BadgeTone; icon?: ReactNode; children: ReactNode }) {
  const style = TONE_STYLES[tone]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        background: style.bg,
        color: style.fg,
        fontSize: 12.5,
        fontWeight: 500,
        padding: '3px 10px',
        borderRadius: 999,
        maxWidth: '100%',
        lineHeight: 1.35,
        whiteSpace: 'normal',
        overflowWrap: 'anywhere',
      }}
    >
      {icon}
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: 'pending' | 'confirmed' | 'rejected' }) {
  const map = {
    pending: { tone: 'amber' as const, key: 'status.pending' as const },
    confirmed: { tone: 'success' as const, key: 'status.confirmed' as const },
    rejected: { tone: 'danger' as const, key: 'status.rejected' as const },
  }
  const cfg = map[status]
  return { tone: cfg.tone, key: cfg.key }
}
