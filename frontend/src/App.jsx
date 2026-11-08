import { useCallback, useMemo, useState } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { createApi } from './api/client'

export default function App() {
  const [session, setSession] = useState(null)
  const [sessionMessage, setSessionMessage] = useState('')
  const expire = useCallback(() => {
    setSession(null)
    setSessionMessage('Your session expired. Please log in again.')
  }, [])
  const api = useMemo(() => session ? createApi(session.accessToken, expire) : null, [session, expire])

  if (!session) return <Login sessionMessage={sessionMessage} onLogin={value => { setSessionMessage(''); setSession(value) }} />
  return <Dashboard user={session.user} api={api} onLogout={() => { setSession(null); setSessionMessage('You have been logged out.') }} />
}
