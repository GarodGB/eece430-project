import { useMemo, useRef, useState } from 'react'

const STATUS_LABELS = {
  pending: 'Pending',
  sent: 'Sent',
  received: 'Received',
}

function beirutDate(iso) {
  const timestamp = new Date(iso)
  if (Number.isNaN(timestamp.getTime())) return 'Date unavailable'
  return timestamp.toLocaleString('en-GB', {
    timeZone: 'Asia/Beirut', dateStyle: 'medium', timeStyle: 'short',
  })
}

/** Owner-only UI. All permissions are independently enforced in Django. */
export default function PurchaseOrderHistory({ api, orders, suppliers, onUpdated, onRefresh }) {
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [confirmation, setConfirmation] = useState(null)
  const [acknowledged, setAcknowledged] = useState(false)
  const [deliveredQuantity, setDeliveredQuantity] = useState('')
  const [deliveredExpiry, setDeliveredExpiry] = useState('')
  const [savingId, setSavingId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const updating = useRef(false)

  const counts = useMemo(() => ({
    all: orders.length,
    pending: orders.filter(order => order.status === 'pending').length,
    sent: orders.filter(order => order.status === 'sent').length,
    received: orders.filter(order => order.status === 'received').length,
  }), [orders])

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase()
    return orders.filter(order =>
      (filter === 'all' || order.status === filter) &&
      (!term || String(order.id).includes(term) || order.medicine_name.toLowerCase().includes(term) || order.supplier_name.toLowerCase().includes(term))
    ).sort((left, right) => right.id - left.id)
  }, [orders, search, filter])

  function beginChange(order, nextStatus) {
    if (updating.current) return
    setExpandedId(order.id)
    setConfirmation({ id: order.id, nextStatus })
    setDeliveredQuantity(String(order.quantity))
    setDeliveredExpiry('')
    setAcknowledged(false)
    setError('')
    setNotice('')
  }

  async function confirmStatusChange() {
    if (!confirmation || !acknowledged || updating.current) return
    const receiving = confirmation.nextStatus === 'received'
    const quantity = Number(deliveredQuantity)
    if (receiving && (!Number.isSafeInteger(quantity) || quantity < 1 || quantity > 1000000 || !deliveredExpiry)) {
      setError('Enter a positive whole-number delivered quantity and the batch expiry date.')
      return
    }
    updating.current = true
    setSavingId(confirmation.id)
    setError('')
    setNotice('')
    try {
      const details = receiving ? { received_quantity: quantity, expiry_date: deliveredExpiry } : {}
      const updated = await api.updatePurchaseOrderStatus(confirmation.id, confirmation.nextStatus, details)
      onUpdated(updated)
      setNotice(receiving
        ? `Order #${updated.id} received: ${updated.received_quantity} units added as a stock batch expiring ${updated.received_expiry_date}. No supplier notification was sent.`
        : `Order #${updated.id} marked sent. PharmaLink did not contact the supplier or change stock.`)
      if (receiving) void onRefresh()
      setConfirmation(null)
      setAcknowledged(false)
    } catch (failure) {
      setError(`${failure.message} Refresh orders to verify their actual status before trying again.`)
    } finally {
      updating.current = false
      setSavingId(null)
    }
  }

  return (
    <section className="mt-8 space-y-4 border-t border-slate-200 pt-7" aria-labelledby="purchase-order-history-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="purchase-order-history-title" className="text-xl font-bold">Purchase order history</h2>
          <p className="mt-1 text-sm text-slate-600">Review pending orders and past reorders for your pharmacy.</p>
          <p className="mt-1 text-xs text-amber-800">Orders are stored in PharmaLink only. Contact suppliers outside the app before marking orders sent.</p>
        </div>
        <button type="button" disabled={savingId !== null} onClick={() => { setNotice(''); void onRefresh() }} className="rounded-lg border border-teal-700 px-4 py-2 text-sm font-semibold text-teal-700 disabled:opacity-50">Refresh orders</button>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter purchase orders by status">
        {[
          ['all', 'All'], ['pending', 'Pending'], ['sent', 'Sent'], ['received', 'Received'],
        ].map(([value, label]) => (
          <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}
            className={`rounded-lg px-3 py-2 text-xs font-semibold ${filter === value ? 'bg-teal-100 text-teal-900' : 'bg-slate-100 text-slate-700'}`}>
            {label} ({counts[value]})
          </button>
        ))}
      </div>
      <input aria-label="Search purchase order history" type="search" placeholder="Search order number, medicine, or supplier…" value={search} onChange={event => setSearch(event.target.value)}
        className="w-full rounded-lg border border-slate-200 bg-[#F5F7FA] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-teal-600" />

      {notice && <p role="status" className="rounded-lg bg-teal-50 p-3 text-sm text-teal-900">{notice}</p>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full min-w-[740px] text-left text-sm">
          <thead className="bg-slate-100 text-xs text-slate-600"><tr>
            <th className="px-4 py-3">ORDER</th><th className="px-4 py-3">MEDICINE</th><th className="px-4 py-3">SUPPLIER</th><th className="px-4 py-3">QTY</th><th className="px-4 py-3">CREATED (BEIRUT)</th><th className="px-4 py-3">STATUS</th><th className="px-4 py-3">DETAILS</th>
          </tr></thead>
          <tbody>
            {visible.map(order => {
              const opened = expandedId === order.id
              const supplier = suppliers.find(item => item.id === order.supplier_id)
              const nextStatus = order.status === 'pending' ? 'sent' : order.status === 'sent' ? 'received' : null
              const confirmationOpen = confirmation?.id === order.id
              return (
                <FragmentRow key={order.id}>
                  <tr className="border-t border-slate-200">
                    <td className="px-4 py-3 font-semibold">#{order.id}</td>
                    <td className="px-4 py-3">{order.medicine_name}</td>
                    <td className="px-4 py-3">{order.supplier_name}</td>
                    <td className="px-4 py-3">{order.quantity}</td>
                    <td className="px-4 py-3">{beirutDate(order.created_at)}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${order.status === 'received' ? 'bg-green-100 text-green-800' : order.status === 'sent' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'}`}>{STATUS_LABELS[order.status] || order.status}</span></td>
                    <td className="px-4 py-3"><button type="button" aria-expanded={opened} onClick={() => { setExpandedId(opened ? null : order.id); setConfirmation(null); setAcknowledged(false) }} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-teal-700">{opened ? 'Hide' : 'Review'}</button></td>
                  </tr>
                  {opened && <tr className="border-t border-slate-100 bg-slate-50"><td colSpan={7} className="px-5 py-4">
                    <div className="space-y-3 text-sm">
                      <p><strong>Order #{order.id}:</strong> {order.quantity} units of {order.medicine_name} from {order.supplier_name}.</p>
                      <p className="text-slate-600">Created: {beirutDate(order.created_at)} · Current status: {STATUS_LABELS[order.status] || order.status}</p>
                      {supplier && <p className="text-slate-600">Supplier contact (demo data): {supplier.phone || 'No phone'}{supplier.email ? ` · ${supplier.email}` : ''}</p>}
                      {order.status === 'received' && (
                        order.received_stock_id ? <p className="text-green-800">Received {order.received_quantity} units on {beirutDate(order.received_at)} · Batch expires {order.received_expiry_date} · Inventory batch #{order.received_stock_id}</p>
                          : <p className="text-amber-800">Legacy received order: no inventory intake recorded. Check stock manually; this order will not be credited again.</p>
                      )}
                      {nextStatus && !confirmationOpen && <button type="button" disabled={savingId !== null} onClick={() => beginChange(order, nextStatus)} className="rounded-lg bg-teal-700 px-4 py-2 text-xs font-bold text-white disabled:opacity-50">{nextStatus === 'sent' ? 'Mark as sent' : 'Mark as received'}</button>}
                      {confirmationOpen && <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
                        <p className="font-semibold text-amber-950">Confirm status update for order #{order.id}</p>
                        {confirmation.nextStatus === 'received' && <div className="grid gap-3 sm:grid-cols-2">
                          <label className="text-sm font-semibold text-amber-950">Actual delivered quantity
                            <input type="number" min="1" max="1000000" step="1" required value={deliveredQuantity} disabled={savingId !== null} onChange={event => setDeliveredQuantity(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2" />
                          </label>
                          <label className="text-sm font-semibold text-amber-950">Received batch expiry date
                            <input type="date" required value={deliveredExpiry} disabled={savingId !== null} onChange={event => setDeliveredExpiry(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2" />
                          </label>
                          <p className="text-xs text-amber-950 sm:col-span-2">This closes the order and records the specified delivered quantity as a new stock batch. If the delivery was partial, verify the quantity before closing the order.</p>
                        </div>}
                        <label className="flex items-start gap-2 text-sm text-amber-900">
                          <input type="checkbox" checked={acknowledged} disabled={savingId !== null} onChange={event => setAcknowledged(event.target.checked)} className="mt-1" />
                          <span>{confirmation.nextStatus === 'sent' ? 'I have already contacted the supplier outside PharmaLink. This button will not send an email or order.' : 'I physically received this delivery and checked the quantity and expiry date. Confirming will add a stock batch exactly once.'}</span>
                        </label>
                        <div className="flex flex-wrap gap-2">
                          <button type="button" disabled={!acknowledged || savingId !== null} onClick={() => { void confirmStatusChange() }} className="rounded-lg bg-teal-700 px-4 py-2 text-xs font-bold text-white disabled:opacity-50">{savingId === order.id ? 'Saving…' : `Confirm ${confirmation.nextStatus}`}</button>
                          <button type="button" disabled={savingId !== null} onClick={() => { setConfirmation(null); setAcknowledged(false) }} className="rounded-lg border px-4 py-2 text-xs">Cancel</button>
                        </div>
                      </div>}
                    </div>
                  </td></tr>}
                </FragmentRow>
              )
            })}
            {visible.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">{orders.length === 0 ? 'No purchase orders have been created yet.' : 'No orders match this search or status.'}</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-600">History remains in PostgreSQL. Marking Sent does not contact suppliers. Confirming Received adds the delivered quantity to inventory once; it does not notify a supplier.</p>
    </section>
  )
}

// A fragment groups a main table row with its optional detail row without adding invalid HTML.
function FragmentRow({ children }) {
  return <>{children}</>
}
