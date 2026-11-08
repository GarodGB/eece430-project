import { useEffect, useRef } from 'react'

export default function CallPharmacyModal({ pharmacy, medicine, available, onClose }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()

    return () => {
      dialog.close()
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="contact-title"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      className="fixed inset-0 m-auto max-h-[90vh] w-[calc(100%_-_2rem)] max-w-[560px] overflow-y-auto rounded-[22px] border border-[#E2E8F0] bg-white p-6 text-[#142440] shadow-xl backdrop:bg-slate-900/40 sm:p-8"
    >
      <header className="flex items-center gap-3">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#E6F6F3] text-[#0B827B]">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            className="h-7 w-7"
            aria-hidden="true"
          >
            <path d="m7 3 3 4-2 3c1.5 3 3 4.5 6 6l3-2 4 3-1 4C10 22 2 14 3 4Z" />
          </svg>
        </span>
        <div>
          <h2 id="contact-title" className="text-xl font-bold">
            Contact pharmacy
          </h2>
          <p className="mt-1 text-xs text-[#6A7C94]">
            {pharmacy.name}
          </p>
        </div>
      </header>

      <section className="mt-6 rounded-xl bg-[#F5F7FA] p-5">
        <h3 className="text-xl font-bold">{pharmacy.name}</h3>

        <p className="mt-2 text-sm text-[#6A7C94]">
          {pharmacy.address || 'Address not supplied'}
        </p>

        <p className="mt-4 text-sm font-bold">
          {medicine}
        </p>

        <div className="mt-3 flex flex-wrap justify-between gap-2 text-xs">
          <span
            className={`font-bold ${
              available
                ? 'text-[#0B827B]'
                : 'text-amber-700'
            }`}
          >
            {available ? 'In stock' : 'Unavailable'}
          </span>
        </div>
      </section>

      <p className="mt-4 text-lg font-bold">
        Phone: {pharmacy.phone ? <a href={`tel:${pharmacy.phone.replace(/[^+0-9]/g, '')}`} className="underline">{pharmacy.phone}</a> : 'Not supplied'}
      </p>
      <p className="mt-1 text-xs text-[#6A7C94]">
        Confirm availability before referring a customer.
      </p>

      <button
        type="button"
        autoFocus
        onClick={onClose}
        className="mt-5 h-11 w-full rounded-lg bg-[#0B827B] text-sm font-bold text-white hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
      >
        Back to results
      </button>
    </dialog>
  )
}