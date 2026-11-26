import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { money, priceCents } from '../api/cart'
import { DAMAN_PERCENT, beirutDate, statusLabel } from '../api/daman'

const dollars = value => `$${money(priceCents(value))}`

const STATUS_STYLE = {
  unpaid: 'bg-amber-100 text-amber-900',
  sent: 'bg-sky-100 text-sky-900',
  paid: 'bg-emerald-100 text-emerald-900',
}

function StatusBadge({ status }) {
  return <span className={`rounded-full px-2 py-1 text-xs font-semibold ${STATUS_STYLE[status] || 'bg-slate-100'}`}>{statusLabel(status)}</span>
}

function TotalCard({ label, total, tone }) {
  return <div className={`rounded-2xl p-4 ${tone}`}>
    <p className="text-xs uppercase tracking-wide">{label}</p>
    <p className="mt-2 text-2xl font-semibold">{dollars(total?.amount ?? '0.00')}</p>
    <p className="text-xs">{total?.count ?? 0} claim{total?.count === 1 ? '' : 's'}</p>
  </div>
}

// The paper the pharmacist prints and takes to Daman.
function StatementPrint({ statement, onClose }) {
  const printButton = useRef(null)
  useEffect(() => {
    printButton.current?.focus()
    const onKeyDown = event => { if (event.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])
  return createPortal(<>
    <style>{`
      @media print {
        @page { size: A4; margin: 14mm; }
        body > #root { display: none !important; }
        html, body { background: #fff !important; }
        #daman-statement-overlay { position: static !important; display: block !important; padding: 0 !important; background: #fff !important; overflow: visible !important; }
        #daman-statement-panel { max-width: none !important; max-height: none !important; overflow: visible !important; box-shadow: none !important; border-radius: 0 !important; }
        .daman-no-print { display: none !important; }
      }
    `}</style>
    <div id="daman-statement-overlay" className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-slate-950/60 p-4">
      <section id="daman-statement-panel" role="dialog" aria-modal="true" aria-labelledby="daman-statement-heading" className="w-full max-w-3xl rounded-2xl bg-white text-slate-900 shadow-2xl">
        <div className="p-8">
          <header className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-slate-800 pb-4">
            <div>
              <h2 id="daman-statement-heading" className="text-2xl font-bold">Daman claim statement #{statement.number}</h2>
              <p className="mt-1 text-sm">Date: {beirutDate(statement.created_at)}</p>
            </div>
            <div className="text-right text-sm">
              <p className="font-semibold">{statement.pharmacy_name}</p>
              <p>{statement.pharmacy_address}</p>
              <p>Tel. {statement.pharmacy_phone}</p>
            </div>
          </header>
          <p className="my-4 text-sm">Claims for the {DAMAN_PERCENT}% Daman share of the sales below.</p>
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-400 text-xs uppercase text-slate-600">
              <tr><th className="py-2">Date</th><th>Sale</th><th>Daman no.</th><th className="text-right">Sale total</th><th className="text-right">Daman {DAMAN_PERCENT}%</th></tr>
            </thead>
            <tbody>{statement.claims.map(claim => <tr key={claim.id} className="border-b border-slate-200">
              <td className="py-2">{beirutDate(claim.sale_date)}</td><td>#{claim.sale_id}</td>
              <td>{claim.daman_number}</td><td className="text-right">{dollars(claim.sale_total)}</td><td className="text-right font-semibold">{dollars(claim.daman_pays)}</td>
            </tr>)}</tbody>
            <tfoot><tr className="border-t-2 border-slate-800 text-base font-bold">
              <td colSpan="4" className="py-3">Total owed by Daman ({statement.claims_count} claims)</td><td className="text-right">{dollars(statement.total)}</td>
            </tr></tfoot>
          </table>
          {statement.status === 'paid' && <p className="mt-4 text-sm font-semibold text-emerald-800">Paid on {beirutDate(statement.paid_at)}.</p>}
          <div className="mt-12 grid grid-cols-2 gap-10 text-sm">
            <p className="border-t border-slate-500 pt-2">Pharmacist signature and stamp</p>
            <p className="border-t border-slate-500 pt-2">Received by Daman</p>
          </div>
          {statement.pharmacy_name?.toLowerCase().startsWith('demo') && <p className="mt-6 text-center text-[10px] text-slate-500">Development demo statement — not an official document</p>}
        </div>
        <div className="daman-no-print flex justify-end gap-3 border-t border-slate-200 bg-slate-50 p-4">
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-semibold">Close</button>
          <button type="button" ref={printButton} onClick={() => window.print()} className="rounded-lg bg-[#0B827B] px-5 py-2 text-sm font-semibold text-white">Print / Save as PDF</button>
        </div>
      </section>
    </div>
  </>, document.body)
}

export default function InsuranceClaims({ api }) {
  const [overview, setOverview] = useState(null)
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [printing, setPrinting] = useState(null)
  const [confirmPaid, setConfirmPaid] = useState(null)
  const request = useRef(null)

  const load = useCallback(async () => {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setLoading(true); setError('')
    try {
      const [data, rows] = await Promise.all([api.damanOverview(controller.signal), api.damanStatements(controller.signal)])
      if (!controller.signal.aborted) { setOverview(data); setStatements(rows) }
    } catch (failure) {
      if (!controller.signal.aborted && failure.name !== 'AbortError') setError(failure.message)
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [api])

  useEffect(() => {
    // Defer loading so cleanup can cancel the StrictMode trial mount.
    const timer = setTimeout(() => { void load() }, 0)
    return () => { clearTimeout(timer); request.current?.abort() }
  }, [load])

  async function createStatement() {
    if (busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      const statement = await api.createDamanStatement()
      setNotice(`Statement #${statement.number} created: Daman owes ${dollars(statement.total)}. Print it and take it to Daman.`)
      setPrinting(statement)
      await load()
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }

  async function openPrint(id) {
    setError('')
    try { setPrinting(await api.damanStatement(id)) } catch (failure) { setError(failure.message) }
  }

  async function markPaid(statement) {
    if (busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      const paid = await api.markDamanStatementPaid(statement.id)
      setNotice(`Statement #${paid.number} marked as paid: ${dollars(paid.total)} received from Daman.`)
      setConfirmPaid(null)
      await load()
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }

  const unpaid = overview?.unpaid_claims || []
  const totals = overview?.totals
  return <section className="rounded-3xl bg-white p-5 lg:p-7">
    <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-3xl font-medium text-[#171717]">Insurance claims — Daman</h1>
      <button type="button" disabled={loading || busy} onClick={load} className="rounded-xl border border-[#0B827B] px-4 py-2 text-sm text-[#0B827B] disabled:opacity-50">Refresh</button>
    </div>
    <p className="mb-6 text-sm text-[#6A7C94]">For a Daman sale the customer pays {100 - DAMAN_PERCENT}% at the counter and Daman owes the pharmacy {DAMAN_PERCENT}%. When you want to collect, create a statement, print it, take it to Daman, then mark it as paid.</p>

    {loading && !overview && <p role="status" className="mb-4 text-sm">Loading claims…</p>}
    {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="mb-4 rounded-xl bg-[#E6F6F6] p-4 text-sm">{notice}</p>}

    {totals && <div className="mb-8 grid gap-3 sm:grid-cols-3">
      <TotalCard label="Unpaid — not on a statement yet" total={totals.unpaid} tone="bg-amber-50 text-amber-950" />
      <TotalCard label="Sent to Daman — waiting for money" total={totals.sent} tone="bg-sky-50 text-sky-950" />
      <TotalCard label="Paid by Daman" total={totals.paid} tone="bg-emerald-50 text-emerald-950" />
    </div>}

    {overview && <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Unpaid claims</h2>
        <button type="button" disabled={busy || unpaid.length === 0} onClick={createStatement} className="rounded-xl bg-[#0B827B] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {busy ? 'Working…' : `Create Daman statement (${unpaid.length})`}
        </button>
      </div>
      <div className="mb-10 overflow-x-auto rounded-2xl border border-[#CCCCCC]">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="bg-[#E7E7E7] text-xs text-[#5D7482]"><tr>{['Date', 'Sale', 'Daman no.', 'Sale total', 'Customer paid', `Daman owes (${DAMAN_PERCENT}%)`].map(title => <th key={title} className="px-4 py-3">{title}</th>)}</tr></thead>
          <tbody>
            {unpaid.map(claim => <tr key={claim.id} className="border-t border-[#CCCCCC]">
              <td className="px-4 py-3">{beirutDate(claim.sale_date)}</td><td className="px-4 py-3">#{claim.sale_id}</td>
              <td className="px-4 py-3 font-semibold">{claim.daman_number}</td>
              <td className="px-4 py-3">{dollars(claim.sale_total)}</td><td className="px-4 py-3">{dollars(claim.customer_paid)}</td>
              <td className="px-4 py-3 font-semibold">{dollars(claim.daman_pays)}</td>
            </tr>)}
            {unpaid.length === 0 && <tr><td colSpan="6" className="px-4 py-6 text-center text-[#6A7C94]">No unpaid claims. Daman sales from the Point of Sale appear here.</td></tr>}
          </tbody>
        </table>
      </div>

      <h2 className="mb-3 text-xl font-semibold">Statements</h2>
      <div className="overflow-x-auto rounded-2xl border border-[#CCCCCC]">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="bg-[#E7E7E7] text-xs text-[#5D7482]"><tr>{['Statement', 'Created', 'Claims', 'Total', 'Status', ''].map((title, index) => <th key={index} className="px-4 py-3">{title}</th>)}</tr></thead>
          <tbody>
            {statements.map(statement => <tr key={statement.id} className="border-t border-[#CCCCCC]">
              <td className="px-4 py-3 font-semibold">#{statement.number}</td>
              <td className="px-4 py-3">{beirutDate(statement.created_at)}</td>
              <td className="px-4 py-3">{statement.claims_count}</td>
              <td className="px-4 py-3 font-semibold">{dollars(statement.total)}</td>
              <td className="px-4 py-3"><StatusBadge status={statement.status} />{statement.status === 'paid' && <span className="ml-2 text-xs text-[#6A7C94]">{beirutDate(statement.paid_at)}</span>}</td>
              <td className="px-4 py-3 text-right">
                <button type="button" onClick={() => openPrint(statement.id)} className="mr-2 rounded-lg border border-slate-300 px-3 py-1">Print</button>
                {statement.status === 'sent' && (confirmPaid === statement.id
                  ? <><button type="button" disabled={busy} onClick={() => markPaid(statement)} className="rounded-lg bg-emerald-700 px-3 py-1 text-white disabled:opacity-50">Yes, Daman paid {dollars(statement.total)}</button>
                    <button type="button" onClick={() => setConfirmPaid(null)} className="ml-2 px-2 py-1 text-[#6A7C94]">Cancel</button></>
                  : <button type="button" disabled={busy} onClick={() => setConfirmPaid(statement.id)} className="rounded-lg bg-[#0B827B] px-3 py-1 text-white disabled:opacity-50">Mark as paid</button>)}
              </td>
            </tr>)}
            {statements.length === 0 && <tr><td colSpan="6" className="px-4 py-6 text-center text-[#6A7C94]">No statements yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </>}
    {printing && <StatementPrint statement={printing} onClose={() => setPrinting(null)} />}
  </section>
}
