import { useCallback, useEffect, useRef, useState } from 'react'
import MedicineFinder from './MedicineFinder'
import NetworkSettingsModal from '../components/NetworkSettingsModal'
import StockPrediction from './StockPrediction'
import AIAssistant from './AIAssistant'
import Inventory from './Inventory'
import PointOfSale from './PointOfSale'

const navigation = [
  ['⌂', 'Dashboard'],
  ['▣', 'Inventory'],
  ['▤', 'Prescriptions'],
  ['▥', 'Stock Prediction'],
  ['⌕', 'Medicine Finder'],
  ['◇', 'Insurance Claims'],
  ['▥', 'Reports'],
]

export default function Dashboard({ user, api, onLogout }) {
  const [showNetworkSettings, setShowNetworkSettings] = useState(false)
  const [activePage, setActivePage] = useState('Dashboard')
  const [message, setMessage] = useState('')
  const [stock, setStock] = useState([])
  const [stockLoading, setStockLoading] = useState(true)
  const [stockError, setStockError] = useState('')
  const stockRequest = useRef(null)
  const initials = ([user.first_name, user.last_name].filter(Boolean).map(name => name[0]).join('') || user.username?.slice(0, 2) || '?').toUpperCase()
  const refreshStock = useCallback(async () => {
    stockRequest.current?.abort()
    const controller = new AbortController()
    stockRequest.current = controller
    setStockLoading(true); setStockError('')
    try {
      const rows = await api.stock(controller.signal)
      if (!controller.signal.aborted) setStock(rows)
    } catch (error) {
      if (error.name !== 'AbortError') { setStock([]); setStockError(error.message) }
    } finally { if (!controller.signal.aborted) setStockLoading(false) }
  }, [api])
  useEffect(() => {
    // Defer initial loading so cleanup can cancel the StrictMode trial mount.
    const timer = setTimeout(() => { void refreshStock() }, 0)
    return () => { clearTimeout(timer); stockRequest.current?.abort() }
  }, [refreshStock])

  function comingSoon(feature) {
    setMessage(`${feature} will be connected in a later step.`)
  }

  return (
    <div className="min-h-screen bg-[#D9D9D9] font-sans text-[#142440]">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-16 flex-col bg-[#152540] text-white lg:w-56">
        <div className="flex h-[72px] items-center gap-3 px-4 lg:px-6">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#00BDCE] text-2xl">
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-6 w-6"
                aria-hidden="true"
                >
                <path d="M8.5 4.5a5 5 0 0 1 7 0l4 4a5 5 0 0 1-7 7l-4-4a5 5 0 0 1 0-7Z"
                    transform="rotate(90 12 12)" />
                <path d="m8.5 8.5 7 7" />
            </svg>
          </span>
          <span className="hidden text-xl font-bold lg:block">
            PharmaLink
          </span>
        </div>

        <nav aria-label="Main navigation" className="space-y-2 px-2 pt-5 lg:px-3">
          {navigation.map(([icon, label]) => (
            <button
              key={label}
              type="button"
              title={label}
              aria-label={label}
              aria-current={label === activePage ? 'page' : undefined}
              onClick={() => {
                if (
                    label === 'Dashboard' ||
                    label === 'Inventory' ||
                    label === 'Medicine Finder' ||
                    label === 'Stock Prediction'
                ) {
                    setActivePage(label)
                    setMessage('')
                } else {
                    comingSoon(label)
                }
                }}
              className={`flex h-11 w-full items-center gap-4 rounded-lg px-3 text-left text-sm transition ${
                label === activePage
                  ? 'border-l-4 border-[#00BDCE] bg-[#1D4555] font-semibold text-white'
                  : 'text-[#BAC8DB] hover:bg-white/10'
              }`}
            >
              <span aria-hidden="true" className="text-xl">{icon}</span>
              <span className="hidden lg:inline">{label}</span>
            </button>
          ))}
        </nav>

        <div className="mt-auto space-y-5 p-3 pb-5">
          <button
            type="button"
            aria-label="Settings"
            onClick={() => comingSoon('Settings')}
            className="flex items-center gap-4 px-3 text-sm text-[#BAC8DB]"
          >
            <span aria-hidden="true" className="text-xl">⚙</span>
            <span className="hidden lg:inline">Settings</span>
          </button>

          <button onClick={onLogout} aria-label="Log out" title="Log out" className="w-full rounded-lg px-3 py-2 text-left text-sm text-[#BAC8DB] hover:bg-white/10">↪ <span className="hidden lg:inline">Log out</span></button>
          <div className="flex items-center gap-3 rounded-xl bg-[#30435F] p-2 lg:p-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-[#142440]">
              {initials}
            </span>
            <div className="hidden lg:block">
              <p className="text-xs font-semibold">{[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username}</p>
              <p className="mt-1 text-xs text-[#BAC8DB]">	{user.role}</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="ml-16 lg:ml-56">
        <header className="flex min-h-[72px] flex-wrap items-center justify-between gap-3 bg-white px-5 py-3 lg:px-10">
          <button
            type="button"
            onClick={() => setShowNetworkSettings(true)}
            className="text-sm font-medium"
          >
            ◉ Network Settings
          </button>

          <p className="hidden text-xs text-[#6A7C94] xl:block">
            Workspace <span className="mx-4">/</span>
            <strong className="text-[#142440]">{activePage}</strong>
          </p>

          <div className="flex items-center gap-3">
            <select
              aria-label="Language"
              defaultValue=""
              onChange={() => comingSoon('Translations')}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs"
            >
              <option value="" disabled>Language</option>
              <option value="en">English</option>
              <option value="ar">العربية</option>
              <option value="fr">Français</option>
            </select>

            <span className="hidden rounded-lg border border-slate-200 px-4 py-2 text-xs sm:block">
              {user.pharmacy_name || 'No pharmacy assigned'}
            </span>
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-xs font-bold">
              {initials}
            </span>
          </div>
        </header>

        <main className="space-y-8 p-4 pb-28 lg:p-9">
          <div hidden={activePage !== 'Dashboard'}>
            <PointOfSale api={api} user={user} onSale={refreshStock} />
            {stockError && <p role="alert" className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Stock refresh failed: {stockError} <button onClick={refreshStock} className="ml-2 underline">Retry stock refresh</button></p>}
          </div>
          {activePage === 'Inventory' && <Inventory stock={stock} loading={stockLoading} error={stockError} onRefresh={refreshStock} />}
          {activePage === 'Medicine Finder' && <MedicineFinder api={api} />}
          {activePage === 'Stock Prediction' && <><p className="text-sm text-slate-600">Preview with sample data — planned for a later sprint.</p><StockPrediction onOpenInventory={() => { setActivePage('Inventory'); setMessage('') }} /></>}
          {activePage === 'AI Assistant' && <><p className="text-sm text-slate-600">Preview with sample data — planned for a later sprint.</p><AIAssistant onOpenFinder={() => setActivePage('Medicine Finder')} /></>}
          {message && <div role="status" className="flex items-center justify-between gap-4 rounded-xl bg-white p-4 text-sm"><p>{message}</p><button aria-label="Dismiss message" onClick={() => setMessage('')} className="px-2 text-xl">×</button></div>}
        </main>
      </div>

      <button
        type="button"
        aria-label="Open AI Assistant"
        title="AI Assistant"
        onClick={() => {
            setActivePage('AI Assistant')
            setMessage('')
        }}
        className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-[#0B827B] text-white shadow-lg"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-8 w-8" aria-hidden="true">
          <path d="M21 11.5a9 9 0 0 1-9 9 10 10 0 0 1-4-.9L3 21l1.4-4.6A9 9 0 1 1 21 11.5Z" />
        </svg>
      </button>
      {showNetworkSettings && (
        <NetworkSettingsModal
            onClose={() => setShowNetworkSettings(false)}
        />
        )}
    </div>
  )
}
