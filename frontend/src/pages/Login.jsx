import { useState } from 'react'
import { login } from '../api/auth'

export default function Login({ onLogin, sessionMessage }) {
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const inputStyle =
    'mt-2 h-11 w-full rounded-lg border border-[#E2E8F0] bg-white px-4 text-sm outline-none focus:border-[#0B827B] focus:ring-2 focus:ring-[#0B827B]/15'

  async function handleSubmit(event) {
    event.preventDefault()
    if (loading) return

    const form = new FormData(event.currentTarget)
    setMessage('')
    setLoading(true)

    try {
      const session = await login(
        form.get('username').trim(),
        form.get('password')
      )
      onLogin(session)
    } catch (error) {
      setMessage(
        error instanceof TypeError
          ? 'Cannot connect to the server. Check that Docker is running.'
          : error.message
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#F5F7FA] px-5 pb-12 font-sans text-[#142440]">
      <header className="mx-auto flex max-w-7xl justify-end py-6">
        <select
          aria-label="Language"
          defaultValue=""
          className="rounded-lg border border-[#E2E8F0] bg-white px-4 py-2 text-sm"
          onChange={() => setMessage('Translations will be connected later.')}
        >
          <option value="" disabled>Language</option>
          <option value="en">English</option>
          <option value="ar">العربية</option>
          <option value="fr">Français</option>
        </select>
      </header>

      <section
        aria-labelledby="login-heading"
        className="mx-auto mt-10 w-full max-w-[480px] rounded-[18px] border border-[#E2E8F0] bg-white p-6 sm:mt-20 sm:p-10"
      >
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#00BDCE]">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="1.7"
              className="h-6 w-6"
              aria-hidden="true"
            >
              <path d="M9 15 15 9M6 18a5 5 0 0 1 0-7l5-5a5 5 0 0 1 7 7l-5 5a5 5 0 0 1-7 0Z" />
            </svg>
          </span>
          <span className="text-2xl font-bold">PharmaLink</span>
        </div>

        <h1 id="login-heading" className="mt-5 text-[28px] font-bold">
          Welcome back
        </h1>
        <p className="mt-1 text-sm text-[#6A7C94]">
          Log in to your pharmacy workspace.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
<div>
            <label htmlFor="username" className="text-sm font-semibold">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              placeholder="Enter your username"
              required
              className={inputStyle}
            />
          </div>

          <div>
            <label htmlFor="password" className="text-sm font-semibold">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                required
                className={`${inputStyle} pr-14`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                className="absolute right-3 top-2 flex h-11 items-center text-[#6A7C94]"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="h-5 w-5"
                  aria-hidden="true"
                >
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
                  <circle cx="12" cy="12" r="3" />
                  {showPassword && <path d="m3 3 18 18" />}
                </svg>
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 h-11 w-full rounded-lg bg-[#0B827B] text-sm font-bold text-white transition hover:bg-[#096C66] disabled:cursor-wait disabled:opacity-60"
          >
            {loading ? 'Logging in...' : 'Log in'}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-[#6A7C94]">
          New to PharmaLink?{' '}
          <button
            type="button"
            onClick={() => setMessage('The sign-up page will be added later.')}
            className="ml-1 font-semibold text-[#0B827B] hover:underline"
          >
            Create an account
          </button>
        </p>

        <p className="mt-7 text-center text-xs text-[#6A7C94]">
          Your role is supplied by your account.
        </p>

        {sessionMessage && <p role="status" className="mt-4 text-center text-sm text-[#0B827B]">{sessionMessage}</p>}
        {message && (
          <p role="status" className="mt-4 text-center text-sm text-[#0B827B]">
            {message}
          </p>
        )}
      </section>
    </main>
  )
}