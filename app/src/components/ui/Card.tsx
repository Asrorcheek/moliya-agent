import type { HTMLAttributes, ReactNode } from 'react'

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
  padded?: boolean
}

export function Card({ children, style, padded = true, ...rest }: CardProps) {
  return (
    <div
      {...rest}
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: padded ? 'var(--space-5)' : 0,
        ...style,
      }}
    >
      {children}
    </div>
  )
}
