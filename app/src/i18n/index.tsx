import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import uz, { type TranslationKey } from './locales/uz'
import ru from './locales/ru'
import en from './locales/en'

export type Locale = 'uz' | 'ru' | 'en'

const DICTS: Record<Locale, Record<TranslationKey, string>> = { uz, ru, en }
const STORAGE_KEY = 'moliya.locale'

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: TranslationKey) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function readInitialLocale(): Locale {
  if (typeof window === 'undefined') return 'uz'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'uz' || stored === 'ru' || stored === 'en') return stored
  return 'uz'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readInitialLocale)

  const setLocale = (next: Locale) => {
    setLocaleState(next)
    window.localStorage.setItem(STORAGE_KEY, next)
    document.documentElement.lang = next
  }

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      t: (key: TranslationKey) => DICTS[locale][key] ?? DICTS.uz[key] ?? key,
    }),
    [locale],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
