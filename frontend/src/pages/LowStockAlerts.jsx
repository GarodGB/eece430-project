import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import PurchaseOrderHistory from './PurchaseOrderHistory'

// PHAR-13: live threshold-based stock alerts and owner-only pending reorders.
// PHAR-12 stockout predictions remain separate and are NOT represented here.
export default function LowStockAlerts({ api, user, onOpenInventory }) {
  const isOwner = user.role === 'owner'
  const [alerts, setAlerts] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState(null)
  const [saving, setSaving] = useState(false)
  const inFlight = useRef(false)
  const requestController = useRef(null)

  const reload = useCallback(async () => {
    requestController.current?.abort()
    const controller = new AbortController()
    requestController.current = controller
    setLoading(true)
    setError('')
    try {
      const [nextAlerts, nextSuppliers, nextOrders] = await Promise.all([
        api.lowStockAlerts(controller.signal),
        isOwner ? api.reorderSuppliers(controller.signal) : Promise.resolve([]),
        isOwner ? api.purchaseOrders(controller.signal) : Promise.resolve([]),
      ])
      if (!controller.signal.aborted) {
        setAlerts(nextAlerts)
        setSuppliers(nextSuppliers)
        setOrders(nextOrders)
      }
    } catch (failure) {
      if (!controller.signal.aborted && failure.name !== 'AbortError') {
        setError(failure.message)
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [api, isOwner])

  useEffect(() => {
    const timer = setTimeout(() => { void reload() }, 0)
    return () => {
      clearTimeout(timer)
      requestController.current?.abort()
    }
  }, [reload])

  const filteredAlerts = useMemo(() => {
    const term = query.trim().toLowerCase()
    return alerts.filter((alert) => alert.medicine_name.toLowerCase().includes(term))
  }, [alerts, query])

  const activeOrder = (medicineId) => orders.find((order) =>
    order.medicine_id === medicineId && ['pending', 'sent'].includes(order.status)
  )

  function openReorder(alert) {
    if (inFlight.current || !isOwner || !suppliers.length) return
    setError('')
    setNotice('')
    setDraft({
      medicine_id: alert.medicine_id,
      quantity: String(Math.max(1, alert.shortfall)),
      supplier_id: String(suppliers[0].id),
    })
  }

  async function submitOrder(event) {
    event.preventDefault()
    if (!isOwner || !draft || inFlight.current) return
    const quantity = Number(draft.quantity)
    const supplierId = Number(draft.supplier_id)
    if (!Number.isSafeInteger(quantity) || quantity < 1 || quantity > 1000000 || !Number.isSafeInteger(supplierId) || supplierId <= 0) {
      setError('Choose a supplier and enter a positive whole-number quantity (at most 1,000,000).')
      return
    }
    inFlight.current = true
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const order = await api.createPurchaseOrder({
        medicine_id: draft.medicine_id,
        supplier_id: supplierId,
        quantity,
      })
      setOrders((current) => [order, ...current.filter((previous) => previous.id !== order.id)])
      setNotice(`Purchase order #${order.id} saved as ${order.status}. It has NOT been sent to the supplier and stock has NOT been increased.`)
      setDraft(null)
    } catch (failure) {
      setError(`${failure.message} If the connection was interrupted, refresh orders before retrying to avoid confusion.`)
    } finally {
      inFlight.current = false
      setSaving(false)
    }
  }

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 text-[#142440] lg:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Live low-stock alerts</h2>
          <p className="mt-1 text-sm text-[#6A7C94]">
            Actual unexpired inventory for {user.pharmacy_name || 'your pharmacy'}, compared with each medicine's reorder threshold.
          </p>
          <p className="mt-1 text-xs text-[#6A7C94]">Threshold alerts are not ML predictions of stockout dates.</p>
        </div>
        <button type="button" onClick={() => { setNotice(''); void reload() }} disabled={loading || saving}
          className="rounded-lg border border-teal-600 px-4 py-2 text-sm font-semibold text-teal-700 disabled:opacity-50">
          {loading ? 'Loading…' : 'Refresh alerts'}
        </button>
      </div>

      {!loading && !error && <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900" role="status">
        {alerts.length} medicine{alerts.length === 1 ? '' : 's'} below the configured reorder threshold.
        {!isOwner && ' Only pharmacy owners may create purchase orders.'}
      </p>}
      {error && <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {notice && <p role="status" className="rounded-lg bg-teal-50 px-4 py-3 text-sm text-teal-800">{notice}</p>}

      <input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search low-stock alerts"
        placeholder="Search low-stock medicines…"
        className="w-full rounded-lg border border-slate-200 bg-[#F5F7FA] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-teal-600" />

      {loading ? <p className="py-8 text-center text-sm text-slate-500">Loading current low-stock alerts…</p> : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-[#EDF2F7] text-xs text-[#6A7C94]">
              <tr>
                <th className="px-4 py-3">MEDICINE</th>
                <th className="px-4 py-3">AVAILABLE</th>
                <th className="px-4 py-3">REORDER LEVEL</th>
                <th className="px-4 py-3">SHORTFALL</th>
                <th className="px-4 py-3">ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.map((alert) => {
                const existing = activeOrder(alert.medicine_id)
                const isEditing = draft?.medicine_id === alert.medicine_id
                return (
                  <tr key={alert.medicine_id} className="border-b border-slate-200 align-top">
                    <td className="px-4 py-4 font-semibold">{alert.medicine_name}</td>
                    <td className="px-4 py-4">{alert.available_quantity}</td>
                    <td className="px-4 py-4">{alert.reorder_level}</td>
                    <td className="px-4 py-4 font-bold text-amber-700">{alert.shortfall}</td>
                    <td className="px-4 py-4">
                      {!isOwner ? <span className="text-xs text-slate-500">Owner approval required</span>
                        : !suppliers.length ? <span className="text-xs text-amber-800">No suppliers configured</span>
                        : !isEditing ? (
                          <div className="flex flex-col items-start gap-2">
                            {existing && <span className="text-xs font-semibold text-teal-800">
                              Existing order #{existing.id} — {existing.status}
                            </span>}
                            <button type="button" disabled={saving} onClick={() => openReorder(alert)}
                              className="rounded-lg border border-teal-600 px-4 py-2 text-xs font-bold text-teal-700 disabled:opacity-50">
                              {existing ? 'Reorder again' : 'Reorder'}
                            </button>
                          </div>
                        ) : (
                          <form onSubmit={(event) => { void submitOrder(event) }} className="space-y-2">
                            <label className="block text-xs text-slate-600">Supplier
                              <select value={draft.supplier_id} disabled={saving} onChange={(event) => setDraft((value) => ({ ...value, supplier_id: event.target.value }))}
                                className="mt-1 block w-full min-w-36 rounded-lg border px-2 py-2 text-sm">
                                {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
                              </select>
                            </label>
                            <label className="block text-xs text-slate-600">Quantity to order
                              <input type="number" min="1" max="1000000" step="1" value={draft.quantity} disabled={saving}
                                onChange={(event) => setDraft((value) => ({ ...value, quantity: event.target.value }))}
                                className="mt-1 block w-36 rounded-lg border px-2 py-2 text-sm" />
                            </label>
                            <p className="text-xs text-slate-500">Saves a pending order only; no supplier notification.</p>
                            <div className="flex flex-wrap gap-2">
                              <button type="submit" disabled={saving} className="rounded-lg bg-teal-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">
                                {saving ? 'Saving…' : 'Create pending order'}
                              </button>
                              <button type="button" disabled={saving} onClick={() => setDraft(null)} className="rounded-lg border px-3 py-2 text-xs">Cancel</button>
                            </div>
                          </form>
                        )}
                    </td>
                  </tr>
                )
              })}
              {filteredAlerts.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                {query.trim() ? 'No low-stock medicines match your search.' : 'No medicines are currently below their reorder threshold.'}
              </td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        {isOwner && <p className="text-xs text-[#6A7C94]">Purchase orders are saved as pending. They are not automatically sent or received.</p>}
        <button type="button" onClick={onOpenInventory} className="ml-auto font-bold text-teal-700">View full inventory →</button>
      </div>
      {isOwner && <PurchaseOrderHistory
        api={api}
        orders={orders}
        suppliers={suppliers}
        onUpdated={(updated) => setOrders(current => current.map(order => order.id === updated.id ? updated : order))}
        onRefresh={reload}
      />}
    </section>
  )
}
