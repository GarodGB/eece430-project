import { useEffect, useState } from 'react'

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' })
const rateFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function formatDate(value) {
  return dateFormat.format(new Date(value + 'T00:00:00Z'))
}

export default function StockPrediction({ api, onOpenInventory }) {
  const [forecast, setForecast] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    const controller = new AbortController()
    api.stockForecasts(controller.signal).then((data) => {
      if (!controller.signal.aborted) setForecast(data)
    }).catch((failure) => {
      if (!controller.signal.aborted) setError(failure.message)
    })
    return () => controller.abort()
  }, [api, attempt])

  const term = search.trim().toLowerCase()
  const results = forecast?.forecasts.filter((item) => {
    const matchesSearch = [item.medicine_name, item.generic_name, item.barcode]
      .some((value) => value.toLowerCase().includes(term))
    const matchesFilter = filter === 'all' ||
      (filter === 'risk' && item.days_remaining !== null && item.days_remaining <= 7) ||
      (filter === 'later' && item.status === 'estimated' && item.days_remaining > 7) ||
      (filter === 'unknown' && item.status === 'no_recent_sales')
    return matchesSearch && matchesFilter
  })

  return (
    <section aria-labelledby="forecast-heading" className="rounded-2xl border border-slate-200 bg-white p-5 text-[#142440]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="forecast-heading" className="text-xl font-bold">Estimated stock run-out</h2>
          {forecast && (
            <p className="mt-1 text-sm text-[#6A7C94]">
              As of {formatDate(forecast.as_of_date)}. Estimates use current sellable stock and average sales
              over the previous {forecast.lookback_days} completed days, including days with zero sales.
              Upcoming expiries and deliveries can change the estimate.
            </p>
          )}
        </div>
        <button type="button" onClick={onOpenInventory} className="text-sm font-bold text-teal-700">
          View inventory
        </button>
      </div>

      {!forecast && !error && <p role="status" className="mt-4 text-sm">Loading stock forecasts…</p>}
      {error && (
        <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">
          <p role="alert">{error}</p>
          <button type="button" className="mt-2 font-bold underline" onClick={() => {
            setError('')
            setForecast(null)
            setAttempt(attempt + 1)
          }}>
            Retry
          </button>
        </div>
      )}
      {!error && forecast && (
        <>
          <div className="my-4 flex flex-wrap gap-3">
            <input
              aria-label="Search medicines"
              placeholder="Search medicines"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="h-10 min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm"
            />
            <select
              aria-label="Filter forecasts"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm"
            >
              <option value="all">All medicines</option>
              <option value="risk">At risk within 7 days</option>
              <option value="later">Estimated beyond 7 days</option>
              <option value="unknown">No recent sales</option>
            </select>
          </div>

          {results.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-slate-50 text-xs text-[#6A7C94]">
                  <tr>
                    <th scope="col" className="px-4 py-3">Medicine</th>
                    <th scope="col" className="px-4 py-3">Available to sell</th>
                    <th scope="col" className="px-4 py-3">Average units sold per day</th>
                    <th scope="col" className="px-4 py-3">Estimated days left</th>
                    <th scope="col" className="px-4 py-3">Estimated run-out date</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((item) => (
                    <tr key={item.medicine_id} className="border-b border-slate-200">
                      <th scope="row" className="px-4 py-3 font-bold">{item.medicine_name}</th>
                      <td className="px-4 py-3">{item.available_quantity}</td>
                      <td className="px-4 py-3">{rateFormat.format(item.average_daily_sales)}</td>
                      {item.status === 'estimated' ? (
                        <>
                          <td className="px-4 py-3">{item.days_remaining}</td>
                          <td className="px-4 py-3">
                            {item.predicted_run_out_date ? formatDate(item.predicted_run_out_date) : 'Beyond calendar range'}
                          </td>
                        </>
                      ) : (
                        <td colSpan={2} className="px-4 py-3">
                          {item.status === 'out_of_stock' ? 'Out of stock' : 'No recent sales'}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-[#6A7C94]">
              {forecast.forecasts.length ? 'No medicines match these filters.' : 'This pharmacy has no inventory to forecast.'}
            </p>
          )}
        </>
      )}
    </section>
  )
}
