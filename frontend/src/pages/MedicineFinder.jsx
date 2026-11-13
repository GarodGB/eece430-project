import { useCallback, useEffect, useRef, useState } from 'react'
import CallPharmacyModal from '../components/CallPharmacyModal'

function directions(pharmacy) {
  const { latitude, longitude } = pharmacy
  if (latitude === null || longitude === null || latitude === undefined || longitude === undefined) return null
  if (!Number.isFinite(Number(latitude)) || !Number.isFinite(Number(longitude)) || Math.abs(Number(latitude)) > 90 || Math.abs(Number(longitude)) > 180) return null
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${latitude},${longitude}`)}`
}

export default function MedicineFinder({ api }) {
  const [medicine, setMedicine] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const controllerRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  // Fetch actual shared-stock results from Django, never sample data.
  const runSearch = useCallback(async (term) => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setLoading(true)
    setError('')
    setResults([])
    setSelected(null)
    setSubmitted(term)

    try {
      const data = await api.finder(term, controller.signal)
      if (!controller.signal.aborted) setResults(data)
    } catch (failure) {
      if (!controller.signal.aborted && failure.name !== 'AbortError') {
        setError(failure.message)
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
        if (controllerRef.current === controller) controllerRef.current = null
      }
    }
  }, [api])

  // Debounce typing to avoid querying PostgreSQL on every keystroke.
  useEffect(() => {
    const term = medicine.trim()
    if (!term) return

    const timer = setTimeout(() => { void runSearch(term) }, 300)
    timerRef.current = timer
    return () => {
      clearTimeout(timer)
      if (timerRef.current === timer) timerRef.current = null
    }
  }, [medicine, runSearch])

  function handleChange(event) {
    // Don't show results for a previous query while a new one is being typed.
    controllerRef.current?.abort()
    setMedicine(event.target.value)
    setSubmitted('')
    setResults([])
    setLoading(false)
    setError('')
    setSelected(null)
  }

  // Keep the existing Search button / Enter support for immediate searches.
  function search(event) {
    event.preventDefault()
    const term = medicine.trim()
    if (!term) return
    clearTimeout(timerRef.current)
    timerRef.current = null
    void runSearch(term)
  }

  return <div className="space-y-5 text-[#142440]">
    <div><h1 className="text-2xl font-bold sm:text-3xl">Find the medicine. Keep care moving.</h1><p className="mt-1 text-[#6A7C94]">Check availability across network pharmacies.</p></div>
    <form onSubmit={search} className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="grid items-end gap-4">
        <label className="text-xs font-semibold text-[#6A7C94]">Medicine name, generic name, or barcode<input required value={medicine} onChange={handleChange} onKeyDown={event => {
          if (event.key === 'Enter') {
            event.preventDefault()
            search(event)
          }
        }} className="mt-2 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-[#142440] outline-none focus:ring-2 focus:ring-teal-600" /></label>

      </div>
      <p className="mt-5 text-xs text-[#6A7C94]">Results update automatically as you type. Shows shared, unexpired stock at other pharmacies. Distance and opening-hours filters are not available.</p>
    </form>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error} Please search again to retry.</p>}
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-xl font-bold">{submitted && !loading && !error ? `${results.length} availability matches` : 'Pharmacy availability'}</h2>
        {submitted && <p className="mt-1 text-xs text-[#6A7C94]">Results for {submitted}</p>}
        {loading && <p role="status" className="py-8 text-sm">Loading availability…</p>}
        {!submitted && <p className="py-8 text-sm text-slate-500">Start typing a medicine name, generic name, or barcode to see availability.</p>}
        {submitted && !loading && !error && results.length === 0 && <p role="status" className="py-8 text-sm text-slate-500">No shared availability found for this medicine.</p>}
        <div className="mt-4 space-y-3">{results.map((result, index) => <article key={`${result.pharmacy.id}-${result.medicine}-${index}`} className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-start justify-between gap-3"><h3 className="font-bold">{result.pharmacy.name}</h3><span className="rounded-full bg-[#E6F6F3] px-3 py-1 text-xs text-[#0B827B]">{result.available ? 'In stock' : 'Unavailable'}</span></div>
          <p className="mt-1 text-xs text-[#6A7C94]">{result.pharmacy.address || 'Address not supplied'}</p>
          <p className="mt-3 text-sm font-semibold">{result.medicine}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={() => setSelected(result)} className="rounded-lg bg-[#0B827B] px-4 py-2 text-xs font-bold text-white">Contact pharmacy</button>
            {directions(result.pharmacy) && <a href={directions(result.pharmacy)} target="_blank" rel="noreferrer" className="rounded-lg border border-teal-600 px-4 py-2 text-xs font-bold text-teal-700">Directions ↗</a>}
          </div>
        </article>)}</div>
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-xl font-bold">Nearby availability</h2>
        <div className="mt-5 flex min-h-64 flex-col items-center justify-center rounded-xl bg-[#E8EDF1] p-8 text-center text-[#6A7C94]">
          <span aria-hidden="true" className="mb-4 text-4xl">⌕</span><p>Use Directions on a pharmacy result to view its supplied location.</p><p className="mt-3 text-xs">A nearby map and distance sorting are not available yet.</p>
        </div>
      </section>
    </div>
    <p className="rounded-xl bg-[#E6F6F6] p-4 text-xs font-semibold text-teal-700">ⓘ Call to confirm availability before referring a customer. Exact quantities and update times are not supplied.</p>
    {selected && <CallPharmacyModal pharmacy={selected.pharmacy} medicine={selected.medicine} available={selected.available} onClose={() => setSelected(null)} />}
  </div>
}
