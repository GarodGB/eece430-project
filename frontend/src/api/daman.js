// PHAR-16: Daman (national social security) always pays a fixed 80% of an insured sale.
// The server calculates the real amounts; these are on-screen estimates and labels.

export const DAMAN_PERCENT = 80

// Split a sale total (in cents) into Daman's share and what the customer pays now.
export function damanSplit(totalCents) {
  const daman = Math.round(totalCents * DAMAN_PERCENT / 100)
  return { daman, customer: totalCents - daman }
}

// A Daman sale only needs the patient's Daman number (digits only).
export function damanDetails(damanNumber) {
  const number = String(damanNumber ?? '').trim()
  if (!/^\d{1,20}$/.test(number)) throw new Error('Enter the Daman number (digits only).')
  return { daman_number: number }
}

export const STATUS_LABELS = { unpaid: 'Unpaid', sent: 'Sent to Daman', paid: 'Paid' }

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

// Date in Lebanon time, e.g. "26 Nov 2026".
export function beirutDate(timestamp) {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'Asia/Beirut' }).format(date)
}
