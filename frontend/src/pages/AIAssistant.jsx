import { useEffect, useRef, useState } from 'react'

const initialMessages = [
  {
    role: 'user',
    text: 'Can you help me find a lower-cost alternative to Panadol Extra?',
  },
  {
    role: 'assistant',
    text: 'I can help compare options. First, confirm the exact product and pack size.',
  },
]

export default function AIAssistant({ onOpenFinder }) {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')
  const [chatTitle, setChatTitle] = useState('Panadol alternatives')
  const [showProduct, setShowProduct] = useState(true)
  const chatRef = useRef(null)

  useEffect(() => {
    const chat = chatRef.current
    if (chat) chat.scrollTop = chat.scrollHeight
  }, [messages])

  function sendMessage(text) {
    const trimmed = text.trim()
    if (!trimmed) return

    setMessages((previous) => [
      ...previous,
      { role: 'user', text: trimmed },
      {
        role: 'assistant',
        text: 'Demo response: your message was received. Live AI answers and inventory lookup are not connected yet.',
      },
    ])
    setInput('')
  }

  function startConversation(title = 'New conversation') {
    setChatTitle(title)
    setMessages([])
    setShowProduct(false)
    setInput('')
  }

  const actionStyle =
    'rounded-lg border border-teal-600 px-3 py-2 text-xs font-bold text-teal-700 hover:bg-teal-50'

  return (
    <div className="space-y-6 text-[#142440]">
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">
          Your pharmacy copilot
        </h1>
        <p className="mt-1 text-[#6A7C94]">Quick answers. Clear next steps.</p>
      </header>

      <div className="grid gap-4 xl:grid-cols-[210px_minmax(0,1fr)_240px]">
        <aside className="flex flex-col rounded-2xl border border-slate-200 bg-white p-3">
          <button
            type="button"
            onClick={() => startConversation()}
            className="rounded-lg bg-[#0B827B] px-4 py-3 text-sm font-bold text-white"
          >
            + New conversation
          </button>

          <h2 className="mb-3 mt-7 px-2 text-xs font-bold text-[#6A7C94]">
            SAMPLE CHATS
          </h2>

          {['Panadol alternatives', 'Inventory check', 'Medicine information'].map(
            (title) => (
              <button
                key={title}
                type="button"
                onClick={() => {
                  if (title === 'Panadol alternatives') {
                    setChatTitle(title)
                    setMessages(initialMessages)
                    setShowProduct(true)
                    setInput('')
                  } else {
                    startConversation(title)
                  }
                }}
                className={`mb-2 rounded-lg border-l-4 p-3 text-left text-xs ${
                  chatTitle === title
                    ? 'border-teal-600 bg-[#E8F6F6]'
                    : 'border-transparent hover:bg-slate-50'
                }`}
              >
                <span className="font-bold">{title}</span>
                <span className="mt-2 block text-[11px] text-[#6A7C94]">
                  Demo conversation
                </span>
              </button>
            )
          )}

          <div className="mt-auto rounded-lg bg-[#F5F7FA] p-3 text-xs">
            <p className="font-bold">Preview mode</p>
            <p className="mt-2 text-[#6A7C94]">Inventory not connected yet</p>
          </div>
        </aside>

        <section className="flex min-w-0 flex-col rounded-2xl border border-slate-200 bg-white">
          <header className="flex items-center gap-3 border-b border-slate-200 p-5">
            <span
              aria-hidden="true"
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#E6F6F6] text-2xl text-teal-700"
            >
              ✧
            </span>
            <div>
              <h2 className="font-bold">Pharmacist Assistant</h2>
              <p className="mt-1 text-xs text-[#6A7C94]">
                Drug information & inventory support
              </p>
            </div>
          </header>

          <div
            ref={chatRef}
            className="h-[480px] overflow-y-auto p-5"
          >
            <p className="mb-6 text-center text-[11px] text-[#6A7C94]">
              Demo conversation
            </p>

            <div role="log" aria-label="Conversation" aria-live="polite">
              {messages.map((message, index) => (
                <div key={index} className="mb-5">
                  {message.role === 'assistant' && (
                    <p className="mb-2 text-xs font-bold">
                      ✧ PharmaLink AI · Demo
                    </p>
                  )}
                  <div
                    className={`max-w-[90%] whitespace-pre-wrap break-words rounded-xl px-4 py-3 text-sm leading-6 ${
                      message.role === 'user'
                        ? 'ml-auto bg-[#152540] text-white'
                        : 'bg-[#F5F7FA]'
                    }`}
                  >
                    {message.text}
                  </div>
                </div>
              ))}
            </div>

            {messages.length === 0 && (
              <p className="py-8 text-center text-sm text-[#6A7C94]">
                Type a message to try the conversation interface.
              </p>
            )}

            {showProduct && (
              <>
                <article className="rounded-xl border border-slate-200 p-4">
                  <h3 className="font-bold">Panadol Extra</h3>
                  <p className="mt-1 text-xs text-[#6A7C94]">
                    Sample product from your design
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-200 pt-4">
                    <div>
                      <p className="text-xs text-[#6A7C94]">Pack size</p>
                      <p className="mt-2 text-sm font-bold">24 tablets</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#6A7C94]">Demo availability</p>
                      <p className="mt-2 text-sm font-bold text-red-600">
                        Out of stock
                      </p>
                    </div>
                  </div>
                </article>

                <p className="mb-3 mt-5 text-sm">
                  What would you like to check?
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => sendMessage('Show drug information for Panadol Extra.')}
                    className={actionStyle}
                  >
                    Drug information
                  </button>
                  <button
                    type="button"
                    onClick={() => sendMessage('Compare prices for Panadol Extra.')}
                    className={actionStyle}
                  >
                    Compare prices
                  </button>
                  <button
                    type="button"
                    onClick={onOpenFinder}
                    className={actionStyle}
                  >
                    Find nearby stock
                  </button>
                </div>
              </>
            )}
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault()
              sendMessage(input)
            }}
            className="mx-4 mt-auto flex gap-2 rounded-xl border border-slate-200 p-2"
          >
            <input
              aria-label="Message the pharmacy assistant"
              placeholder="Ask your pharmacy assistant..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              className="min-w-0 flex-1 rounded-lg bg-[#F5F7FA] px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-teal-600"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="Send message"
              className="rounded-lg bg-[#0B827B] px-4 text-xl text-white disabled:opacity-40"
            >
              ➤
            </button>
          </form>

          <p className="p-3 text-center text-[10px] text-[#6A7C94]">
            Demo only. AI can make mistakes. Verify medicine information.
          </p>
        </section>

        <aside className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="mb-5 text-xs font-bold text-[#6A7C94]">
            QUICK ACTIONS
          </h2>

          {[
            ['Check interactions', 'Review a medicine combination'],
            ['Find alternatives', 'Compare equivalent products'],
            ['Medicine finder', 'Check nearby pharmacies'],
          ].map(([title, description]) => (
            <button
              key={title}
              type="button"
              onClick={() => {
                if (title === 'Medicine finder') {
                  onOpenFinder()
                } else {
                  setInput(
                    title === 'Check interactions'
                      ? 'Check interactions between '
                      : 'Find alternatives for '
                  )
                }
              }}
              className="mb-3 block w-full rounded-xl border border-slate-200 p-5 text-left hover:bg-teal-50"
            >
              <span className="block text-sm font-bold">{title}</span>
              <span className="mt-2 block text-xs leading-5 text-[#6A7C94]">
                {description}
              </span>
            </button>
          ))}

          <div className="mt-7 rounded-xl bg-[#E8F6F6] p-5">
            <h3 className="text-xs font-bold text-teal-700">
              Built for pharmacists
            </h3>
            <p className="mt-3 text-xs leading-5 text-[#6A7C94]">
              Your inventory and medicine tools, in one conversation.
            </p>
          </div>
        </aside>
      </div>
    </div>
  )
}