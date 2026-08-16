import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  icon?: ReactNode
  fullWidth?: boolean
}

const BASE: Record<Variant, { bg: string; fg: string; border: string; hoverBg: string }> = {
  primary: {
    bg: 'var(--color-primary)',
    fg: 'var(--color-text-on-primary)',
    border: 'var(--color-primary)',
    hoverBg: 'var(--color-primary-strong)',
  },
  secondary: {
    bg: 'var(--color-surface)',
    fg: 'var(--color-text-primary)',
    border: 'var(--color-border-strong)',
    hoverBg: 'var(--color-bg)',
  },
  ghost: {
    bg: 'transparent',
    fg: 'var(--color-text-secondary)',
    border: 'transparent',
    hoverBg: 'var(--color-bg)',
  },
  danger: {
    bg: 'var(--color-danger)',
    fg: '#FFF6F5',
    border: 'var(--color-danger)',
    hoverBg: 'var(--color-danger-strong)',
  },
}

export function Button({ variant = 'secondary', icon, fullWidth, children, style, disabled, ...rest }: ButtonProps) {
  const c = BASE[variant]
  return (
    <button
      {...rest}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        width: fullWidth ? '100%' : undefined,
        padding: '10px 16px',
        fontSize: 14,
        fontWeight: 500,
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${c.border}`,
        background: c.bg,
        color: c.fg,
        opacity: disabled ? 0.55 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'background 120ms ease',
        ...style,
      }}
      onMouseEnter={(e) => {
        if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = c.hoverBg
      }}
      onMouseLeave={(e) => {
        if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = c.bg
      }}
    >
      {icon}
      {children}
    </button>
  )
}
