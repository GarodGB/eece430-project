import { useEffect, useRef, useState } from 'react'
import { addMedicine, cartTotal, discountPercent, discountedTotal, money, priceCents, salePayload } from '../api/cart'
import ReceiptModal from './ReceiptModal'

export default function PointOfSale({ api, user, onSale }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [cart, setCart] = useState([])
  const [payment, setPayment] = useState('cash')
  const [discount, setDiscount] = useState('')
  const [lastReceipt, setLastReceipt] = useState(null)
  const [receiptOpen, setReceiptOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const [selling, setSelling] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [uncertain, setUncertain] = useState(false)
  const input = useRef(null)
  const searchController = useRef(null)
  const liveSearchTimer = useRef(null)
  const saleInFlight = useRef(false)
  useEffect(() => () => searchController.current?.abort(), [])

  // Search medicines automatically as the user types
  useEffect(() => {
    const term = query.trim()

    if (!term || selling || uncertain) return

    const controller = new AbortController()

    const timer = setTimeout(async () => {
      if (controller.signal.aborted) return

      searchController.current?.abort()
      searchController.current = controller
      setSearching(true)

      try {
        const medicines = await api.medicines(
          term,
          controller.signal
        )

        if (!controller.signal.aborted) {
          setResults(medicines)
          setError('')
        }
      } catch (failure) {
        if (
          !controller.signal.aborted &&
          failure.name !== 'AbortError'
        ) {
          setError(failure.message)
        }
      } finally {
        if (!controller.signal.aborted) {
          setSearching(false)
        }
      }
    }, 300)
    liveSearchTimer.current = timer

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [query, api, selling, uncertain])


  function add(medicine) {
    try { setCart(addMedicine(cart, medicine)); setError(''); setNotice('') }
    catch (failure) { setError(failure.message) }
  }

  async function search(event) {
    event.preventDefault()
    if (!query.trim() || saleInFlight.current || uncertain) return
    clearTimeout(liveSearchTimer.current)
    searchController.current?.abort()
    const controller = new AbortController()
    searchController.current = controller
    setSearching(true); setError(''); setNotice(''); setResults(null)
    try {
      const medicines = await api.medicines(query.trim(), controller.signal)
      if (controller.signal.aborted) return
      const exact = medicines.find(item => item.barcode === query.trim())
      if (exact) {
        // Keyboard-wedge scanners submit with Enter, just like manual barcode entry.
        priceCents(exact.price)
        setCart(current => addMedicine(current, exact))
        setQuery(''); setNotice(`${exact.name} added to cart.`)
      } else setResults(medicines)
    } catch (failure) {
      if (failure.name !== 'AbortError') setError(failure.message)
    } finally {
      if (!controller.signal.aborted) { setSearching(false); input.current?.focus() }
    }
  }

  async function checkout() {
    if (saleInFlight.current || uncertain || searching) return
    let payload
    try { payload = salePayload(cart, payment, discount) }
    catch (failure) { setError(failure.message); return }
    saleInFlight.current = true
    setSelling(true); setError(''); setNotice('')
    try {
      const sale = await api.sale(payload)
      setCart([]); setResults(null); setDiscount(''); setQuery('')
      // Store the server-confirmed sale, not the cart's estimated totals.
      setLastReceipt(sale)
      setReceiptOpen(true)
      const discountNote = Number(sale.discount_percent) > 0 ? ` (subtotal $${sale.subtotal}, ${sale.discount_percent}% discount)` : ''
      setNotice(`Sale #${sale.id} completed. Server total: $${sale.total}${discountNote}.`)
      // Stock refresh failure must not turn an already recorded sale into a failed checkout.
      try {
        await onSale()
      } catch {
        setError('Sale completed, but stock could not refresh. Use Inventory to refresh stock.')
      }
    } catch (failure) {
      setError(failure.message)
      if (!failure.notSent && (!failure.status || failure.status >= 500)) setUncertain(true)
    } finally { saleInFlight.current = false; setSelling(false) }
  }

  const locked = selling || uncertain
  const validQuantities = cart.every(item => Number.isSafeInteger(Number(item.quantity)) && Number(item.quantity) > 0)
  const percent = (() => { try { return discountPercent(discount) } catch { return null } })()
  const subtotalCents = validQuantities ? cartTotal(cart) : null
  return <section className="rounded-3xl bg-white p-5 lg:p-7">
    <h1 className="mb-8 text-3xl font-medium text-[#171717]"><span aria-hidden="true" className="mr-4 text-slate-400">▱</span>Point of Sale</h1>
    <form onSubmit={search} className="mb-3 flex flex-wrap gap-2">
      <input ref={input} aria-label="Search medicine or barcode" value={query} disabled={locked} onChange={event => {
        searchController.current?.abort()
        setQuery(event.target.value)
        setResults(null)
        setError('')
        setSearching(false)
      }} onKeyDown={event => {
        // Keep scanner/keyboard Enter-to-add behavior without a submit button.
        if (event.key === 'Enter') {
          event.preventDefault()
          void search(event)
        }
      }} placeholder="Scan a barcode or type a medicine name…" className="h-11 min-w-0 flex-1 rounded-xl bg-[#F0F0F0] px-4 text-sm outline-none focus:ring-2 focus:ring-teal-600" />
      <button type="button" disabled={locked} onClick={() => { input.current?.focus(); setNotice('Scan into the search field. Press Enter if your scanner does not send it automatically.') }} className="rounded-xl bg-[#19243F] px-5 py-2 text-white">Scan</button>

    </form>
    <p className="mb-5 text-xs text-[#6A7C94]">Use a keyboard barcode scanner or enter a barcode and press Enter. Exact barcode matches are added directly.</p>
    {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="mb-4 rounded-xl bg-[#E6F6F6] p-4 text-sm">{notice}</p>}
    {lastReceipt && !receiptOpen && <button type="button" onClick={() => setReceiptOpen(true)} className="mb-4 rounded-lg border border-teal-700 px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50">View last receipt #{lastReceipt.id}</button>}
    {uncertain && <div role="alert" className="mb-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
      <p>The sale may have reached the server. Check with your administrator before trying again to avoid a duplicate sale.</p>
      <button onClick={() => { setUncertain(false); setError('') }} className="mt-3 rounded-lg border px-3 py-2">I verified that this sale was not recorded — unlock cart</button>
      <button onClick={() => { setUncertain(false); setCart([]); setError(''); void onSale() }} className="ml-3 mt-3 rounded-lg border px-3 py-2">Sale was recorded — clear cart and refresh</button>
    </div>}
    {results !== null && <div className="mb-6 space-y-2 rounded-xl border border-slate-200 p-4">
      <h2 className="font-semibold">Medicine search results</h2>
      {results.length === 0 && <p role="status" className="text-sm text-slate-500">No matching medicines found.</p>}
      {results.map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 py-3 text-sm">
        <div><strong>{item.name}</strong><p className="text-[#6A7C94]">{item.generic_name} · {item.barcode} · ${item.price}{item.needs_prescription && ' · Prescription required'}</p></div>
        <button disabled={locked} onClick={() => add(item)} className="rounded-lg bg-[#0B827B] px-4 py-2 text-white disabled:opacity-50">Add to cart</button>
      </div>)}
    </div>}
    <div className="overflow-x-auto rounded-2xl border border-[#CCCCCC]">
      <table className="w-full min-w-[600px] text-left text-sm">
        <thead className="bg-[#E7E7E7] text-xs text-[#5D7482]"><tr>{['CODE', 'MEDICINE', 'QUANTITY', 'UNIT PRICE', 'TOTAL', ''].map((title, index) => <th key={index} className="px-4 py-4">{title}</th>)}</tr></thead>
        <tbody className="text-[#5D7482]">{cart.map(item => <tr key={item.barcode} className="border-t border-[#CCCCCC]">
          <td className="px-4 py-5">{item.barcode}</td><td className="px-4 py-5 font-semibold">{item.name}{item.needs_prescription && <p className="text-xs text-amber-800">Prescription required</p>}</td>
          <td className="px-4 py-5"><input type="number" min="1" max="2147483647" step="1" disabled={locked || searching} aria-label={`Quantity for ${item.name}`} value={item.quantity} onChange={event => setCart(current => current.map(row => row.barcode === item.barcode ? { ...row, quantity: event.target.value } : row))} className="w-20 rounded-lg border border-slate-300 px-2 py-2" /></td>
          <td className="px-4 py-5">${money(priceCents(item.price))}</td><td className="px-4 py-5 font-bold">${money(priceCents(item.price) * Number(item.quantity))}</td>
          <td className="px-4 py-5"><button disabled={locked || searching} aria-label={`Remove ${item.name}`} onClick={() => setCart(current => current.filter(row => row.barcode !== item.barcode))} className="text-red-700">Remove</button></td>
        </tr>)}{cart.length === 0 && <tr><td colSpan="6" className="px-6 py-8 text-center">Your cart is empty. Search or scan a medicine to begin.</td></tr>}</tbody>
      </table>
      <div className="flex flex-wrap items-center gap-3 bg-[#D9D9D9] px-5 py-3 text-[#171717]">
        <label className="mr-auto text-sm">Payment <select aria-label="Payment method" disabled={locked} value={payment} onChange={event => setPayment(event.target.value)} className="ml-2 rounded-lg bg-white px-3 py-2"><option value="cash">Cash</option><option value="card">Card</option></select></label>
        <label className="text-sm">Discount % <input type="number" min="0" max="100" step="0.01" inputMode="decimal" aria-label="Discount percent" disabled={locked} value={discount} onChange={event => setDiscount(event.target.value)} placeholder="0" className="ml-2 w-20 rounded-lg bg-white px-2 py-2" /></label>
        {percent === null && <span role="alert" className="text-sm text-red-700">Discount must be 0–100%.</span>}
        {subtotalCents !== null && percent > 0 && <span className="text-sm">Subtotal ${money(subtotalCents)}</span>}
        <strong>Total {subtotalCents !== null && percent !== null ? `$${money(discountedTotal(subtotalCents, percent))}` : '—'}</strong>
        <button onClick={checkout} disabled={locked || searching || !cart.length || !user.pharmacy || !validQuantities || percent === null} className="rounded-xl bg-[#0B827B] px-4 py-2 text-white disabled:opacity-50">{selling ? 'Completing sale…' : 'Checkout'}</button>
      </div>
    </div>
    {!user.pharmacy && <p className="mt-4 text-sm text-amber-800">Your account must belong to a pharmacy to complete a sale.</p>}
    <p className="mt-3 text-xs text-[#6A7C94]">The server confirms prices, unexpired stock and the discount at checkout. A discount can never bring the sale below cost. Card selects the sale’s payment record; it does not charge a card.</p>
    {lastReceipt && receiptOpen && (
      <ReceiptModal
        sale={lastReceipt}
        pharmacyName={user.pharmacy_name}
        username={user.username}
        onClose={() => setReceiptOpen(false)}
      />
    )}
  </section>
}
