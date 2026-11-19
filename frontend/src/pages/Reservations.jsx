import { useCallback, useEffect, useRef, useState } from 'react'

const formatDate = (value) =>
  value ? new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Beirut',
  }).format(new Date(value)) : '—'

export default function Reservations({ api, user, onChanged }) {
  const [reservations, setReservations] = useState([])
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [selected, setSelected] = useState(null)
  const [quantity, setQuantity] = useState('1')
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [filter, setFilter] = useState('active')
  const attempt = useRef(null)

  const refresh = useCallback(async (signal) => {
    const [held, currentStock] = await Promise.all([
      api.reservations(signal), api.stock(signal),
    ])
    setReservations(held)
    setStocks(currentStock)
  }, [api])

  useEffect(() => {
    const controller = new AbortController()
    // Schedule the initial data load outside the synchronous effect body.
    const timer = setTimeout(() => {
      refresh(controller.signal)
        .catch(failure => { if (!controller.signal.aborted && failure.name !== 'AbortError') setError(failure.message) })
        .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    }, 0)
    return () => { clearTimeout(timer); controller.abort() }
  }, [refresh])

  useEffect(() => {
    const controller = new AbortController()
    if (!query.trim()) return () => controller.abort()
    const timer = setTimeout(async () => {
      try {
        const items = await api.medicines(query.trim(), controller.signal)
        if (!controller.signal.aborted) setMatches(items.slice(0, 15))
      } catch (failure) {
        if (!controller.signal.aborted && failure.name !== 'AbortError') setError(failure.message)
      }
    }, 250)
    return () => { controller.abort(); clearTimeout(timer) }
  }, [api, query])

  const selectedStock = selected && stocks.find(item => item.medicine === selected.id)
  const sellable = selectedStock ? selectedStock.available_to_sell : 0
  const validQuantity = Number.isSafeInteger(Number(quantity)) && Number(quantity) > 0
  const active = reservations.filter(item => item.status === 'active')
  const visible = reservations.filter(item => filter === 'all' || item.status === filter)

  async function refreshNow() {
    setLoading(true); setError('')
    try { await refresh() }
    catch (failure) { setError(failure.message) }
    finally { setLoading(false) }
  }

  async function create(event) {
    event.preventDefault()
    if (working || !selected || !validQuantity || !customerName.trim() ||
        Number(quantity) > sellable) return
    const body = {
      medicine_id: selected.id,
      quantity: Number(quantity),
      customer_name: customerName.trim(),
      customer_phone: customerPhone.trim(),
    }
    // If a network response was lost, retry the SAME request key rather than
    // accidentally creating a second hold. A changed form gets a new key.
    const signature = JSON.stringify(body)
    if (!attempt.current || attempt.current.signature !== signature) {
      attempt.current = { signature, key: window.crypto.randomUUID() }
    }
    setWorking(true); setError(''); setNotice('')
    try {
      const result = await api.createReservation({
        ...body, request_key: attempt.current.key,
      })
      attempt.current = null
      setNotice(`Reserved ${result.quantity} unit(s) of ${result.medicine_name} for ${result.customer_name}.`)
      setSelected(null); setQuantity('1'); setCustomerName(''); setCustomerPhone('')
      setQuery(''); setMatches([])
      try { await refresh(); await onChanged?.() }
      catch { setError('Reservation saved, but refreshing stock failed. Click Refresh.') }
    } catch (failure) {
      setError(`${failure.message} If the request may have reached the server, review Reservations before retrying.`)
    } finally { setWorking(false) }
  }

  async function release(item) {
    if (working || !window.confirm(
      `Release ${item.quantity} reserved unit(s) of ${item.medicine_name} for ${item.customer_name}?`
    )) return
    setWorking(true); setError(''); setNotice('')
    try {
      await api.releaseReservation(item.id)
      setNotice(`Reservation #${item.id} released. Those units can now be sold.`)
      try { await refresh(); await onChanged?.() }
      catch { setError('Released successfully, but refreshing failed. Click Refresh.') }
    } catch (failure) {
      setError(failure.message)
    } finally { setWorking(false) }
  }

  return <section className="space-y-6">
    <div className="rounded-3xl bg-white p-5 lg:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#142440]">Medicine Reservations</h1>
          <p className="mt-2 text-sm text-[#6A7C94]">
            Reserve medicine for a specific customer at {user.pharmacy_name || 'your pharmacy'}.
            Reserved units are blocked from normal checkout until released.
          </p>
        </div>
        <button type="button" onClick={refreshNow} disabled={loading || working}
          className="rounded-xl border border-teal-700 px-4 py-2 font-semibold text-teal-700 disabled:opacity-50">
          Refresh
        </button>
      </div>
      <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Reservations do not take payment or change physical stock. To sell a held item,
        first release the reservation, then use Point of Sale. Never reserve expired stock.
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-800">{error}</p>}
      {notice && <p role="status" className="mt-4 rounded-xl bg-teal-50 p-4 text-sm text-teal-800">{notice}</p>}
      {loading && <p className="mt-4 text-sm text-slate-500">Loading reservation and inventory data…</p>}
    </div>

    <form onSubmit={create} className="rounded-3xl bg-white p-5 lg:p-7">
      <h2 className="mb-4 text-xl font-semibold text-[#142440]">New reservation</h2>
      <label className="mb-2 block text-sm font-semibold" htmlFor="res-search">Search medicine or barcode</label>
      <input id="res-search" value={query} onChange={e => {
        setQuery(e.target.value); setSelected(null); setMatches([]); setError('')
      }} placeholder="Type medicine name, generic name or barcode…"
        className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:ring-2 focus:ring-teal-600" />
      {query.trim() && !selected && <div className="mt-2 max-h-56 overflow-auto rounded-xl border border-slate-200">
        {matches.map(m => <button key={m.id} type="button"
          onClick={() => { setSelected(m); setQuery(m.name); setMatches([]) }}
          className="flex w-full justify-between border-b border-slate-100 px-4 py-3 text-left text-sm hover:bg-teal-50">
          <span>{m.name}</span><span className="text-slate-500">{m.barcode}</span>
        </button>)}
        {!matches.length && <p className="px-4 py-3 text-xs text-slate-500">No results yet.</p>}
      </div>}
      {selected && <div className="mt-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm">
        Selected: <strong>{selected.name}</strong> · Physical stock: {selectedStock?.total_quantity ?? 0} ·
        Reserved: {selectedStock?.reserved_quantity ?? 0} ·
        <strong> Available to reserve: {sellable}</strong>
      </div>}
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <label className="block text-sm font-semibold">
          Quantity
          <input type="number" min="1" max={sellable || undefined} step="1" value={quantity}
            onChange={e => setQuantity(e.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3" />
        </label>
        <label className="block text-sm font-semibold">
          Customer name *
          <input value={customerName} maxLength={120} required
            onChange={e => setCustomerName(e.target.value)}
            placeholder="Name of person collecting"
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3" />
        </label>
        <label className="block text-sm font-semibold">
          Contact number (optional)
          <input type="tel" value={customerPhone} maxLength={25}
            onChange={e => setCustomerPhone(e.target.value)}
            placeholder="e.g. 03 123 456"
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3" />
        </label>
      </div>
      <button type="submit" disabled={working || loading || !selected || !validQuantity ||
        Number(quantity) > sellable || !customerName.trim()}
        className="mt-5 rounded-xl bg-[#0B827B] px-6 py-3 font-semibold text-white disabled:opacity-50">
        {working ? 'Saving…' : 'Reserve medicine'}
      </button>
      {selected && sellable === 0 &&
        <p className="mt-3 text-sm text-amber-800">No unreserved, unexpired quantity is available.</p>}
    </form>

    <div className="rounded-3xl bg-white p-5 lg:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-[#142440]">Reservation history</h2>
          <p className="mt-1 text-sm text-slate-500">{active.length} active reservation(s)</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {['active', 'released', 'all'].map(status => (
            <button key={status} type="button" onClick={() => setFilter(status)}
              className={`rounded-lg px-4 py-2 text-sm capitalize ${filter === status
                ? 'bg-teal-100 font-semibold text-teal-900'
                : 'bg-slate-100 text-slate-700'}`}>{status}</button>
          ))}
        </div>
      </div>
      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full min-w-[850px] text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase text-slate-600">
            <tr>{['#', 'Medicine', 'Customer / Contact', 'Qty', 'Reserved by / Date', 'Status', 'Action']
              .map(h => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
          </thead>
          <tbody>{visible.map(r => <tr key={r.id} className="border-t border-slate-200">
            <td className="px-4 py-3">#{r.id}</td>
            <td className="px-4 py-3 font-semibold">{r.medicine_name}</td>
            <td className="px-4 py-3">{r.customer_name}<div className="text-xs text-slate-500">{r.customer_phone || 'No contact provided'}</div></td>
            <td className="px-4 py-3">{r.quantity}</td>
            <td className="px-4 py-3">{r.reserved_by}<div className="text-xs text-slate-500">{formatDate(r.created_at)}</div></td>
            <td className="px-4 py-3">{r.status === 'active'
              ? <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">Reserved</span>
              : <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">Released</span>}
              {r.status === 'released' && <div className="mt-1 text-xs text-slate-500">by {r.released_by} · {formatDate(r.released_at)}</div>}
            </td>
            <td className="px-4 py-3">{r.status === 'active'
              ? <button type="button" disabled={working} onClick={() => release(r)}
                  className="rounded-lg border border-red-500 px-3 py-2 font-semibold text-red-700 disabled:opacity-50">
                  Release
                </button> : '—'}</td>
          </tr>)}
          {!visible.length && <tr><td colSpan={7} className="px-4 py-7 text-center text-slate-500">No reservations in this view.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  </section>
}
