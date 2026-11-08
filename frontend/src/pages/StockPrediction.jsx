import { useState } from 'react'

const forecasts = [
  {
    name: 'Panadol Extra',
    description: '24 tablets · Pack',
    stock: 12,
    demand: 6,
    days: 2,
    reorder: 60,
  },
  {
    name: 'Augmentin 1 g',
    description: '14 tablets · Pack',
    stock: 18,
    demand: 6,
    days: 3,
    reorder: 42,
  },
  {
    name: 'Zyrtec 10 mg',
    description: '20 tablets · Pack',
    stock: 24,
    demand: 4,
    days: 6,
    reorder: 28,
  },
]

const summaries = [
  ['Medicines tracked', '248', 'Across your inventory'],
  ['At risk this week', '8', 'Needs your attention'],
  ['Reorders suggested', '5', 'Ready for review'],
  ['Forecast window', '7 days', 'Sample update: 9:00 AM'],
]

export default function StockPrediction() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('At risk')
  const [summaryEnabled, setSummaryEnabled] = useState(true)
  const [message, setMessage] = useState('')

  const results = forecasts.filter((item) => {
    const matchesSearch = item.name
      .toLowerCase()
      .includes(search.trim().toLowerCase())

    const matchesFilter =
      filter === 'All medicines' ||
      (filter === 'At risk' && item.days <= 7) ||
      (filter === 'Healthy stock' && item.days > 7)

    return matchesSearch && matchesFilter
  })

  function previewReorder(item) {
    setMessage(
      `Reorder preview: ${item.reorder} packs of ${item.name}. No order has been placed; supplier confirmation and backend connection come later.`
    )
  }

  return (
    <div className="space-y-5 text-[#142440]">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">
            Stay ahead of stockouts
          </h1>
          <p className="mt-1 text-[#6A7C94]">
            Predict demand and reorder with confidence.
          </p>
        </div>

        <div className="flex gap-3 text-xs font-bold">
          <span className="rounded-lg border border-teal-600 bg-white px-5 py-3">
            Next 7 days
          </span>
          <button
            type="button"
            onClick={() => setMessage('Report export will be connected later.')}
            className="rounded-lg border border-teal-600 bg-white px-5 py-3 text-teal-700"
          >
            Export report
          </button>
        </div>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaries.map(([label, value, description]) => (
          <section
            key={label}
            className="rounded-xl border border-slate-200 bg-white p-5"
          >
            <h2 className="text-xs font-bold text-[#6A7C94]">{label}</h2>
            <p className="mt-2 text-3xl font-bold">{value}</p>
            <p className="mt-4 text-xs text-[#6A7C94]">{description}</p>
          </section>
        ))}
      </div>

      <section className="flex flex-wrap items-center gap-4 rounded-xl border border-orange-300 bg-[#FFF2DA] p-5">
        <span aria-hidden="true" className="text-3xl text-amber-700">⚠</span>
        <div className="flex-1">
          <h2 className="font-bold text-amber-800">
            Panadol Extra may run out in 2 days
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            Current stock: 12 packs · Suggested reorder: 60 packs
          </p>
        </div>
        <button
          type="button"
          onClick={() => previewReorder(forecasts[0])}
          className="rounded-lg bg-amber-700 px-6 py-3 text-xs font-bold text-white"
        >
          Reorder now
        </button>
      </section>

      {message && (
        <div
          role="status"
          className="flex items-center justify-between gap-4 rounded-xl border border-teal-200 bg-teal-50 p-4 text-sm"
        >
          <p>{message}</p>
          <button
            type="button"
            aria-label="Dismiss message"
            onClick={() => setMessage('')}
            className="px-2 text-xl"
          >
            ×
          </button>
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">Stock forecast</h2>
            <p className="mt-1 text-sm text-[#6A7C94]">
              Prioritize medicines that need replenishment.
            </p>
          </div>
          <span className="rounded-full bg-slate-100 px-4 py-1 text-xs text-[#6A7C94]">
            Demo data
          </span>
        </div>

        <div className="my-4 flex flex-wrap gap-3">
          <input
            aria-label="Search medicines"
            placeholder="Search medicines..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-10 min-w-0 flex-1 rounded-lg border border-slate-200 bg-[#F5F7FA] px-3 text-sm outline-none focus:ring-2 focus:ring-teal-600"
          />

          {['All medicines', 'At risk', 'Healthy stock'].map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={filter === option}
              onClick={() => setFilter(option)}
              className={`rounded-lg px-5 py-2 text-xs font-bold ${
                filter === option
                  ? 'bg-[#D9F2EF] text-teal-700'
                  : 'bg-[#F5F7FA]'
              }`}
            >
              {option}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead className="bg-[#EDF2F7] text-[10px] text-[#6A7C94]">
              <tr>
                {[
                  'MEDICINE',
                  'IN STOCK',
                  'DAILY DEMAND',
                  'STOCKOUT IN',
                  'REORDER QTY',
                  'ACTION',
                ].map((heading) => (
                  <th key={heading} className="px-4 py-3">{heading}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {results.map((item) => (
                <tr key={item.name} className="border-b border-slate-200">
                  <td className="px-4 py-3">
                    <p className="font-bold">{item.name}</p>
                    <p className="mt-1 text-[10px] text-[#6A7C94]">
                      {item.description}
                    </p>
                  </td>
                  <td className="px-4 py-3">{item.stock} packs</td>
                  <td className="px-4 py-3">{item.demand} packs</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-amber-100 px-4 py-1 font-bold text-amber-700">
                      {item.days} days
                    </span>
                  </td>
                  <td className="px-4 py-3">{item.reorder} packs</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => previewReorder(item)}
                      className="rounded-lg border border-teal-600 px-5 py-2 font-bold text-teal-700 hover:bg-teal-50"
                    >
                      Reorder
                    </button>
                  </td>
                </tr>
              ))}

              {results.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    No matching medicines in this demo dataset.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-3 flex justify-between gap-3 text-xs">
          <p className="text-[#6A7C94]">
            Showing {results.length} of 3 sample medicines
          </p>
          <button
            type="button"
            onClick={() => setMessage('The Inventory page will be added later.')}
            className="font-bold text-teal-700"
          >
            View full inventory →
          </button>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="font-bold">How this forecast works</h2>
          <p className="mt-2 text-xs text-[#6A7C94]">
            Planned inputs for the forecasting service.
          </p>
          <div className="mt-6 flex flex-wrap justify-between gap-4 text-xs font-bold">
            <span>Recent sales</span>
            <span>Current stock</span>
            <span>Lead time</span>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-4">
            <h2 id="summary-label" className="font-bold">
              Weekly owner summary
            </h2>
            <button
              type="button"
              role="switch"
              aria-checked={summaryEnabled}
              aria-labelledby="summary-label"
              onClick={() => setSummaryEnabled(!summaryEnabled)}
              className={`relative h-6 w-11 shrink-0 rounded-full ${
                summaryEnabled ? 'bg-[#0B827B]' : 'bg-slate-300'
              }`}
            >
              <span
                className={`absolute left-0 top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                  summaryEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          <p className="mt-2 text-xs text-[#6A7C94]">
            Sales, profit and stock alerts in one email.
          </p>
          <div className="mt-4 flex flex-wrap justify-between gap-3 border-t border-slate-200 pt-4 text-xs">
            <button
              type="button"
              onClick={() => setMessage('Email summary settings will be connected later.')}
              className="font-bold text-teal-700"
            >
              Manage summary →
            </button>
            <span className="text-[#6A7C94]">Every Monday · 9:00 AM</span>
          </div>
        </section>
      </div>

      <p className="text-xs text-[#6A7C94]">
        Preview only: summary counts and forecasts are sample data.
        The table contains three examples, not the full inventory.
        The email toggle is not connected to an email service.
      </p>
    </div>
  )
}