// Minimal dependency-free router. The app has a small, fixed set of routes
// (see REQUIRED SCREENS), so a full router library would be more surface
// area than value here — this covers push-state navigation, a current-path
// context, and an active-link helper, which is all eight screens need.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type AnchorHTMLAttributes,
  type ReactNode,
} from 'react'

interface RouterContextValue {
  path: string
  navigate: (to: string) => void
}

const RouterContext = createContext<RouterContextValue | null>(null)

export function RouterProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(window.location.pathname || '/')

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname || '/')
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const navigate = (to: string) => {
    const target = new URL(to, window.location.href)
    if (`${target.pathname}${target.search}` === `${window.location.pathname}${window.location.search}`) return
    window.history.pushState({}, '', to)
    setPath(target.pathname)
  }

  return <RouterContext.Provider value={{ path, navigate }}>{children}</RouterContext.Provider>
}

export function useRouter(): RouterContextValue {
  const ctx = useContext(RouterContext)
  if (!ctx) throw new Error('useRouter must be used within RouterProvider')
  return ctx
}

type LinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> & {
  to: string
  children: ReactNode
}

export function Link({ to, children, onClick, ...rest }: LinkProps) {
  const { navigate } = useRouter()
  return (
    <a
      {...rest}
      href={to}
      onClick={(e) => {
        onClick?.(e)
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
        e.preventDefault()
        navigate(to)
      }}
    >
      {children}
    </a>
  )
}
