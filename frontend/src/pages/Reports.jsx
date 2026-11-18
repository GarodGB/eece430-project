import { useCallback, useEffect, useRef, useState } from 'react'
import { WEEK_CHOICES, formatMargin, formatMoney, isLoss, profitBarWidth, weekLabel } from '../api/reports'

function SummaryCard({ label, value, loss }) {
  return <div className="rounded-2xl border border-[#CCCCCC] p-4">
    <p className="text-xs uppercase tracking-wide text-[#6A7C94]">{label}</p>
    <p className={`mt-2 text-2xl font-semibold ${loss ? 'text-red-700' : 'text-[#171717]'}`}>{value}</p>
  </div>
}

export default function Reports({ api, user }) {
  const isOwner = user.role === 'owner'
  const [weeks, setWeeks] = useState(8)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const request = useRef(null)

  const load = useCallback(async (count) => {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setLoading(true); setError('')
    try {
      const data = await api.weeklyReport(count, controller.signal)
      if (!controller.signal.aborted) setReport(data)
    } catch (failure) {
      if (!controller.signal.aborted && failure.name !== 'AbortError') { setReport(null); setError(failure.message) }
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [api])

  useEffect(() => {
    if (!isOwner) return
    // Defer loading so cleanup can cancel the StrictMode trial mount.
    const timer = setTimeout(() => { void load(weeks) }, 0)
    return () => { clearTimeout(timer); request.current?.abort() }
  }, [isOwner, weeks, load])

  if (!isOwner) {
    return <section className="rounded-3xl bg-white p-5 lg:p-7">
      <h1 className="mb-4 text-3xl font-medium text-[#171717]">Reports</h1>
      <p role="status" className="rounded-xl bg-[#E6F6F6] p-4 text-sm">Sales and profit reports are only available to the pharmacy owner.</p>
    </section>
  }

  const totals = report?.totals
  const rows = report?.results || []
  return <section className="rounded-3xl bg-white p-5 lg:p-7">
    <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-3xl font-medium text-[#171717]">Weekly sales &amp; profit</h1>
      <div className="flex items-center gap-3">
        <label className="text-sm text-[#5D7482]">Show
          <select aria-label="Number of weeks" value={weeks} disabled={loading} onChange={event => setWeeks(Number(event.target.value))} className="ml-2 rounded-lg border border-[#CCCCCC] bg-white px-3 py-2 text-[#171717]">
            {WEEK_CHOICES.map(count => <option key={count} value={count}>Last {count} weeks</option>)}
          </select>
        </label>
        <button type="button" disabled={loading} onClick={() => load(weeks)} className="rounded-xl bg-[#0B827B] px-4 py-2 text-sm text-white disabled:opacity-50">Refresh</button>
      </div>
    </div>
    <p className="mb-6 text-sm text-[#6A7C94]">{report?.pharmacy || user.pharmacy_name}. Weeks run Monday to Sunday. Revenue is what customers paid after discounts; profit is revenue minus the buying cost of what was sold.</p>

    {loading && <p role="status" className="mb-4 text-sm">Loading report…</p>}
    {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error} <button onClick={() => load(weeks)} className="ml-2 underline">Try again</button></p>}

    {totals && <>
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <SummaryCard label="Sales" value={totals.sales_count} />
        <SummaryCard label="Revenue" value={formatMoney(totals.revenue)} />
        <SummaryCard label="Cost" value={formatMoney(totals.cost)} />
        <SummaryCard label="Profit" value={formatMoney(totals.profit)} loss={isLoss(totals.profit)} />
        <SummaryCard label="Margin" value={formatMargin(totals.margin_percent)} loss={isLoss(totals.margin_percent)} />
      </div>
      {totals.sales_count === 0 && <p role="status" className="mb-4 rounded-xl bg-[#E6F6F6] p-4 text-sm">No sales in this period yet. Completed sales from the Point of Sale appear here.</p>}
      <div className="overflow-x-auto rounded-2xl border border-[#CCCCCC]">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-[#E7E7E7] text-xs text-[#5D7482]"><tr>{['Week', 'Sales', 'Revenue', 'Cost', 'Profit', 'Margin'].map(title => <th key={title} className="px-4 py-4">{title}</th>)}</tr></thead>
          <tbody>{rows.map(week => <tr key={week.week_start} className="border-t border-[#CCCCCC]">
            <td className="px-4 py-4 font-semibold">{weekLabel(week)}{week.is_current && <span className="ml-2 rounded-full bg-[#E6F6F6] px-2 py-1 text-xs font-normal text-[#0B827B]">This week</span>}</td>
            <td className="px-4 py-4">{week.sales_count}</td>
            <td className="px-4 py-4">{formatMoney(week.revenue)}</td>
            <td className="px-4 py-4">{formatMoney(week.cost)}{week.cost_estimated && <span title="Includes old sales saved before buying prices were recorded; today's cost was used." className="ml-1 text-amber-700">*</span>}</td>
            <td className={`px-4 py-4 font-semibold ${isLoss(week.profit) ? 'text-red-700' : 'text-[#171717]'}`}>
              <div className="flex items-center gap-3">
                <span className="w-20">{formatMoney(week.profit)}</span>
                <span aria-hidden="true" className="h-2 flex-1 rounded-full bg-slate-100"><span className={`block h-2 rounded-full ${isLoss(week.profit) ? 'bg-red-400' : 'bg-[#0B827B]'}`} style={{ width: `${profitBarWidth(week.profit, rows)}%` }} /></span>
              </div>
            </td>
            <td className="px-4 py-4">{formatMargin(week.margin_percent)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {totals.cost_estimated && <p className="mt-3 text-xs text-amber-800">* Some old sales were saved before buying prices were recorded, so today's cost was used for them.</p>}
    </>}
  </section>
}
