import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { money, priceCents } from '../api/cart'

function displayMoney(value) {
  return `$${money(priceCents(value))}`
}

function receiptDate(timestamp) {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return 'Date unavailable'
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Beirut',
  }).format(date)
}

export default function ReceiptModal({ sale, pharmacyName, username, onClose }) {
  const printButton = useRef(null)

  useEffect(() => {
    printButton.current?.focus()
    function onKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  const subtotal = priceCents(sale.subtotal)
  const total = priceCents(sale.total)
  const discount = Math.max(0, subtotal - total)
  const items = Array.isArray(sale.items) ? sale.items : []
  const name = pharmacyName || 'PharmaLink Pharmacy'

  return createPortal(
    <>
      <style>{`
        @media print {
          @page { margin: 12mm; }
          body > #root { display: none !important; }
          html, body { background: #fff !important; }
          #pharmalink-receipt-overlay {
            position: static !important;
            display: block !important;
            inset: auto !important;
            overflow: visible !important;
            padding: 0 !important;
            background: #fff !important;
          }
          #pharmalink-receipt-panel {
            width: 80mm !important;
            max-width: 80mm !important;
            max-height: none !important;
            overflow: visible !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
          }
          #pharmalink-receipt-content { padding: 0 !important; }
          .pharmalink-receipt-no-print { display: none !important; }
        }
      `}</style>
      <div
        id="pharmalink-receipt-overlay"
        className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-slate-950/60 p-4"
      >
        <section
          id="pharmalink-receipt-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="pharmalink-receipt-heading"
          className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white text-slate-900 shadow-2xl"
        >
          <div id="pharmalink-receipt-content" className="p-6 sm:p-8">
            <header className="border-b border-dashed border-slate-300 pb-5 text-center">
              <h2 id="pharmalink-receipt-heading" className="text-2xl font-bold">PharmaLink</h2>
              <p className="mt-1 text-sm font-semibold">{name}</p>
              <p className="mt-2 text-xs text-slate-500">Customer receipt</p>
            </header>

            <dl className="grid grid-cols-2 gap-x-3 gap-y-2 border-b border-dashed border-slate-300 py-5 text-xs">
              <dt className="text-slate-500">Sale number</dt>
              <dd className="text-right font-semibold">#{sale.id}</dd>
              <dt className="text-slate-500">Date and time (Beirut)</dt>
              <dd className="text-right">{receiptDate(sale.created_at)}</dd>
              <dt className="text-slate-500">Cashier</dt>
              <dd className="text-right">{sale.sold_by || username || '—'}</dd>
              <dt className="text-slate-500">Payment method</dt>
              <dd className="text-right capitalize">{sale.payment_method || '—'}</dd>
            </dl>

            <table className="mt-5 w-full text-left text-xs">
              <thead className="border-b border-slate-300 text-slate-500">
                <tr>
                  <th scope="col" className="pb-2 pr-2">Medicine</th>
                  <th scope="col" className="pb-2 text-center">Qty</th>
                  <th scope="col" className="pb-2 text-right">Unit</th>
                  <th scope="col" className="pb-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={`${item.medicine}-${index}`} className="border-b border-slate-100 align-top">
                    <td className="py-3 pr-2 font-medium">{item.medicine_name}</td>
                    <td className="py-3 text-center">{item.quantity}</td>
                    <td className="py-3 text-right">{displayMoney(item.unit_price)}</td>
                    <td className="py-3 text-right">{`$${money(priceCents(item.unit_price) * Number(item.quantity))}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <dl className="mt-5 space-y-2 border-t border-dashed border-slate-300 pt-4 text-sm">
              <div className="flex justify-between gap-3"><dt>Subtotal</dt><dd>{displayMoney(sale.subtotal)}</dd></div>
              <div className="flex justify-between gap-3">
                <dt>Discount ({sale.discount_percent || '0'}%)</dt>
                <dd>−${money(discount)}</dd>
              </div>
              <div className="flex justify-between gap-3 border-t border-slate-200 pt-3 text-lg font-bold">
                <dt>Total</dt><dd>${money(total)}</dd>
              </div>
            </dl>

            <p className="mt-6 text-center text-xs text-slate-500">Thank you for visiting!</p>
            {name.toLowerCase().startsWith('demo') && (
              <p className="mt-2 text-center text-[10px] text-slate-500">Development demo receipt — not a fiscal document</p>
            )}
          </div>
          <div className="pharmalink-receipt-no-print flex flex-wrap justify-end gap-3 border-t border-slate-200 bg-slate-50 p-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-semibold"
            >
              Done
            </button>
            <button
              type="button"
              ref={printButton}
              onClick={() => window.print()}
              className="rounded-lg bg-[#0B827B] px-5 py-2 text-sm font-semibold text-white"
            >
              Print / Save as PDF
            </button>
          </div>
        </section>
      </div>
    </>,
    document.body,
  )
}
