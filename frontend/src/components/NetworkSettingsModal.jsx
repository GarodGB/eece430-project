import { useEffect, useRef } from 'react'

export default function NetworkSettingsModal({ onClose }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()

    return () => dialog.close()
  }, [])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="network-settings-title"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      className="fixed inset-0 m-auto max-h-[90vh] w-[calc(100%_-_2rem)] max-w-[560px] overflow-y-auto rounded-[22px] border border-[#E2E8F0] bg-white p-6 text-[#142440] shadow-xl backdrop:bg-slate-900/40 sm:p-8"
    >
      <header className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#E6F6F3] text-3xl font-light text-[#0B827B]"
        >
          +
        </span>
        <div>
          <h2 id="network-settings-title" className="text-xl font-bold">
            Network settings
          </h2>
          <p className="mt-1 text-xs text-[#6A7C94]">
            Control what your pharmacy shares.
          </p>
        </div>
      </header>

      <div className="mt-7 flex items-start justify-between gap-5">
        <div>
          <h3 id="sharing-label" className="text-lg font-bold">
            Share stock availability
          </h3>
          <p id="sharing-description" className="mt-2 text-sm text-[#6A7C94]">
            Let nearby pharmacies see which medicines you have.
          </p>
        </div>

        <button
          type="button"
          disabled
          aria-labelledby="sharing-label"
          aria-describedby="sharing-description"
          
          className={`relative mt-1 h-9 w-[72px] shrink-0 rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 ${
            'bg-slate-300'
          }`}
        >
          <span
            className={`absolute top-1 h-7 w-7 rounded-full bg-white shadow-sm transition-transform ${
              'translate-x-1'
            } left-0`}
          />
        </button>
      </div>

      <div
        role="status"
        className={`mt-6 rounded-xl p-5 ${
          'bg-slate-100'
        }`}
      >
        <p className="font-bold text-[#0B827B]">
          Stock sharing status is unavailable
        </p>
        <p className="mt-2 text-xs text-[#6A7C94]">
          Sharing settings cannot be viewed or changed in this workspace yet.
        </p>
      </div>

      <p className="mt-5 text-xs text-[#6A7C94]">
        Only medicine availability is shared, not patient or sales details.
      </p>
      <p className="mt-2 text-xs text-[#6A7C94]">
        Contact your administrator to confirm your pharmacy’s sharing settings.
      </p>

      <button
        type="button"
        onClick={onClose}
        className="mt-6 h-11 w-full rounded-lg bg-[#0B827B] text-sm font-bold text-white hover:bg-teal-800"
      >
        Done
      </button>
    </dialog>
  )
}
