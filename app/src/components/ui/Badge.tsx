import type { ReactNode } from 'react'

type BadgeTone = 'neutral' | 'success' | 'danger' | 'amber' | 'primary'

const TONE_STYLES: Record<BadgeTone, { bg: string; fg: string; ring: string }> = {
  neutral: { bg: 'var(--glass-2)', fg: 'var(--color-text-secondary)', ring: 'var(--color-border-strong)' },
  success: { bg: 'var(--color-success-soft)', fg: 'var(--color-success-strong)', ring: 'rgba(18, 201, 141, 0.34)' },
  danger: { bg: 'var(--color-danger-soft)', fg: 'var(--color-danger-strong)', ring: 'rgba(255, 77, 94, 0.34)' },
  amber: { bg: 'var(--color-amber-soft)', fg: 'var(--color-amber-strong)', ring: 'rgba(255, 176, 32, 0.34)' },
  primary: { bg: 'var(--color-primary-soft)', fg: 'var(--color-primary-bright)', ring: 'rgba(46, 107, 255, 0.36)' },
}

export function Badge({ tone = 'neutral', icon, children }: { tone?: BadgeTone; icon?: ReactNode; children: ReactNode }) {
  const style = TONE_STYLES[tone]
  return (
    <span
      className="ui-badge"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        background: style.bg,
        color: style.fg,
        borderColor: style.ring,
        fontSize: 'var(--text-sm)',
        fontWeight: 600,
        letterSpacing: '-0.002em',
        padding: '3px 10px',
        borderRadius: 'var(--radius-pill)',
        maxWidth: '100%',
        lineHeight: 1.4,
        whiteSpace: 'normal',
        overflowWrap: 'anywhere',
      }}
    >
      {icon}
      {children}
    </span>
  )
}

/** Tone/label mapping for the three transaction states. Returns config rather
 * than an element so callers can feed the label through their own `t()`. */
export function statusBadgeConfig(status: 'pending' | 'confirmed' | 'rejected') {
  const map = {
    pending: { tone: 'amber' as const, key: 'status.pending' as const },
    confirmed: { tone: 'success' as const, key: 'status.confirmed' as const },
    rejected: { tone: 'danger' as const, key: 'status.rejected' as const },
  }
  return map[status]
}
