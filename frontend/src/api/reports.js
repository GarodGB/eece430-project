// Helpers for the weekly sales and profit report (PHAR-14).

export const WEEK_CHOICES = [4, 8, 12, 26]

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// '2026-11-16' -> 'Nov 16' (read as a plain date, so the browser's time zone can't shift the day)
export function shortDate(isoDate) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(isoDate))
  if (!match) return String(isoDate ?? '')
  return `${MONTHS[Number(match[2]) - 1]} ${Number(match[3])}`
}

export function weekLabel(week) {
  return `${shortDate(week.week_start)} – ${shortDate(week.week_end)}`
}

// '13.00' -> '$13.00', '-2.00' -> '-$2.00'
export function formatMoney(value) {
  const text = String(value ?? '')
  if (!/^-?\d+(\.\d+)?$/.test(text)) return '—'
  return text.startsWith('-') ? `-$${text.slice(1)}` : `$${text}`
}

// null (nothing sold) -> '—'
export function formatMargin(value) {
  if (value === null || value === undefined || value === '') return '—'
  return `${value}%`
}

export function isLoss(value) {
  return String(value ?? '').startsWith('-')
}

// Width of the profit bar, 0 to 100, compared with the best week.
export function profitBarWidth(profit, weeks) {
  const largest = Math.max(0, ...weeks.map(week => Math.abs(Number(week.profit)) || 0))
  if (!largest) return 0
  return Math.round(Math.abs(Number(profit)) / largest * 100)
}
