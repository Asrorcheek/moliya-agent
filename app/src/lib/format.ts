// Centralized formatting for dates, currency and statuses so no component
// hand-rolls its own number or date logic.

const SO_M = "so'm"

/** Formats a UZS integer amount as "2 500 000 so'm" with a narrow no-break space group separator. */
export function formatUzs(amount: number): string {
  const sign = amount < 0 ? '-' : ''
  const abs = Math.abs(Math.round(amount))
  const grouped = abs.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')
  return `${sign}${grouped}\u00A0${SO_M}`
}

/** Compact form for tight spaces, e.g. "2.5 mln so'm". */
export function formatUzsCompact(amount: number): string {
  const abs = Math.abs(amount)
  const sign = amount < 0 ? '-' : ''
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(1)} mlrd ${SO_M}`
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)} mln ${SO_M}`
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(0)} ming ${SO_M}`
  return formatUzs(amount)
}

const MONTH_LABELS_UZ = [
  'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
  'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr',
]

/** month is "YYYY-MM" */
export function formatMonthLabel(month: string, locale: 'uz' | 'ru' | 'en' = 'uz'): string {
  const [y, m] = month.split('-').map(Number)
  if (!y || !m) return month
  if (locale === 'uz') return `${MONTH_LABELS_UZ[m - 1]} ${y}`
  const date = new Date(Date.UTC(y, m - 1, 1))
  return date.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

/** Formats an ISO datetime string in Asia/Tashkent, since that is the system's fixed operating timezone. */
export function formatDateTime(iso: string, locale: 'uz' | 'ru' | 'en' = 'uz'): string {
  const date = new Date(iso)
  return date.toLocaleString(locale === 'ru' ? 'ru-RU' : locale === 'en' ? 'en-US' : 'en-GB', {
    timeZone: 'Asia/Tashkent',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDate(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleDateString('en-GB', {
    timeZone: 'Asia/Tashkent',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function currentMonthTashkent(): string {
  const now = new Date()
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tashkent',
    year: 'numeric',
    month: '2-digit',
  }).formatToParts(now)
  const y = parts.find((p) => p.type === 'year')?.value
  const m = parts.find((p) => p.type === 'month')?.value
  return `${y}-${m}`
}
