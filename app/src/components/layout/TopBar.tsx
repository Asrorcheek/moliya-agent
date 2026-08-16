import { useI18n, type Locale } from '@/i18n'
import { NavIcon } from '@/components/ui/NavIcon'

const LOCALES: Locale[] = ['uz', 'ru', 'en']

export function TopBar({ title, onMenuClick }: { title: string; onMenuClick?: () => void }) {
  const { locale, setLocale, t } = useI18n()

  return (
    <header
      style={{
        height: 'var(--topbar-height)',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-5)',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {onMenuClick && (
          <button
            aria-label="Menyu"
            onClick={onMenuClick}
            className="mobile-menu-button"
            style={{ background: 'none', border: 'none', padding: 6, display: 'none' }}
          >
            <NavIcon name="menu" />
          </button>
        )}
        <h1 className="topbar-title" style={{ fontSize: 18 }}>{title}</h1>
      </div>

      <div role="group" aria-label="Til tanlash" style={{ display: 'flex', gap: 2, background: 'var(--color-bg)', borderRadius: 999, padding: 3 }}>
        {LOCALES.map((l) => (
          <button
            key={l}
            onClick={() => setLocale(l)}
            aria-pressed={locale === l}
            style={{
              padding: '5px 10px',
              fontSize: 12.5,
              borderRadius: 999,
              border: 'none',
              background: locale === l ? 'var(--color-surface)' : 'transparent',
              boxShadow: locale === l ? 'var(--shadow-sm)' : 'none',
              fontWeight: locale === l ? 500 : 400,
              color: locale === l ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
            }}
          >
            <span className="locale-full">{t(`lang.${l}` as const)}</span>
            <span className="locale-short">{l.toUpperCase()}</span>
          </button>
        ))}
      </div>
    </header>
  )
}
