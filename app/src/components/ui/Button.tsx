import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  icon?: ReactNode
  fullWidth?: boolean
}

/** Styling lives in global.css under `.ui-btn` so that hover, focus-visible
 * and active states are real CSS states rather than JS mouse handlers — the
 * previous inline approach left keyboard users with no visible feedback. */
export function Button({ variant = 'secondary', icon, fullWidth, children, style, className, disabled, ...rest }: ButtonProps) {
  const classes = ['ui-btn', `ui-btn-${variant}`]
  if (fullWidth) classes.push('ui-btn-block')
  if (className) classes.push(className)
  return (
    <button {...rest} disabled={disabled} className={classes.join(' ')} style={style}>
      {icon}
      {children}
    </button>
  )
}
