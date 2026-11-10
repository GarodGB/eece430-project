import { useState } from 'react'

export default function Inventory({ stock, loading, error, onRefresh }) {
  const [sortOrder, setSortOrder] = useState('asc')
  const sortedStock = [...stock].sort((a, b) => {
    const comparison = (a.medicine_name || '').localeCompare(b.medicine_name || '', 'en', { sensitivity: 'base', numeric: true })
    return sortOrder === 'asc' ? comparison : -comparison
  })
  return (
    <section className="rounded-3xl bg-white p-5 lg:p-7">
      <div className="mb-6 flex items-center justify-between gap-3">
        <h1 className="text-3xl font-medium text-[#171717]">Inventory</h1>
        <button disabled={loading} onClick={onRefresh} className="rounded-xl bg-[#0B827B] px-4 py-2 text-white disabled:opacity-50">Refresh stock</button>
      </div>
      <p className="mb-4 text-sm text-[#6A7C94]">Stock batches and expiry dates supplied by your pharmacy workspace.</p>
      <label className="mb-4 flex flex-wrap items-center gap-3 text-sm text-[#5D7482]">
        Sort by
        <select value={sortOrder} onChange={event => setSortOrder(event.target.value)} className="rounded-lg border border-[#CCCCCC] bg-white px-3 py-2 text-[#171717] focus:ring-2 focus:ring-teal-600">
          <option value="asc">Name A–Z</option>
          <option value="desc">Name Z–A</option>
        </select>
      </label>
      {loading && <p role="status">Loading stock…</p>}
      {error && <p role="alert" className="mb-4 text-red-700">{error} Stock could not be verified. Refresh to try again.</p>}
      {!loading && !error && stock.length === 0 && <p role="status">No stock records found.</p>}
      {!error && stock.length > 0 && <div className="overflow-x-auto rounded-2xl border border-[#CCCCCC]">
        <table className="w-full min-w-[600px] text-left text-sm">
          <thead className="bg-[#E7E7E7] text-xs text-[#5D7482]"><tr>{['Medicine', 'Batch ID', 'Quantity', 'Reorder level', 'Expiry date', 'Alerts'].map(title => <th key={title} className="px-5 py-4">{title}</th>)}</tr></thead>
          <tbody>{sortedStock.map(item => <tr key={item.id} className="border-t border-[#CCCCCC]">
            <td className="px-5 py-4 font-semibold">{item.medicine_name}</td><td className="px-5 py-4">{item.id}</td>
            <td className="px-5 py-4">{item.quantity}</td><td className="px-5 py-4">{item.reorder_level}</td>
            <td className="px-5 py-4">{item.expiry_date || 'Not supplied'}</td>
            <td className="px-5 py-4 text-amber-800">{[item.is_expired && 'Expired', item.is_low && 'Low stock', item.expiring_soon && 'Expires within 30 days'].filter(Boolean).join(' · ') || '—'}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </section>
  )
}