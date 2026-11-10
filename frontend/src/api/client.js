export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function errorText(value) {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(errorText).join(' ')
  if (value && typeof value === 'object') {
    return Object.entries(value).map(([key, item]) => `${key}: ${errorText(item)}`).join(' ')
  }
  return ''
}

// DRF may return absolute pagination URLs behind the Vite proxy.
export function apiPath(path) {
  const base = globalThis.location?.origin || 'http://localhost:5173'
  const url = new URL(path, base)
  if (![base, 'http://localhost:8000', 'http://127.0.0.1:8000'].includes(url.origin) || !url.pathname.startsWith('/api/')) {
    throw new ApiError('The server returned an unsupported API link.')
  }
  return url.pathname + url.search
}

export function createApi(accessToken, onExpired, refreshToken) {
  let expired = false
  let refreshing = null
  function expire() {
    if (!expired) { expired = true; onExpired() }
    return new ApiError('Your session expired. Please log in again.', 401)
  }
  async function refresh() {
    if (expired || !refreshToken) throw expire()
    if (!refreshing) {
      refreshing = (async () => {
        let response
        try {
          response = await fetch('/api/token/refresh/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
          })
        } catch {
          throw new ApiError('Cannot renew your session. Check your connection and try again.')
        }
        if ([400, 401, 403].includes(response.status)) throw expire()
        const data = await response.json().catch(() => null)
        if (!response.ok || typeof data?.access !== 'string' || !data.access) {
          throw new ApiError('Cannot renew your session right now. Please try again.')
        }
        accessToken = data.access
        if (data.refresh) refreshToken = data.refresh
      })().finally(() => { refreshing = null })
    }
    return refreshing
  }
  async function request(path, options = {}, retried = false) {
    if (expired) throw expire()
    options.signal?.throwIfAborted()
    const sentToken = accessToken
    let response
    try {
      response = await fetch(apiPath(path), {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers, Authorization: `Bearer ${sentToken}` },
      })
    } catch (error) {
      if (error.name === 'AbortError' || error instanceof ApiError) throw error
      throw new ApiError('Cannot reach the server. Check your connection and that Docker is running.')
    }
    if (response.status === 401) {
      // Only reads may be replayed. Never automatically resubmit a sale.
      if (!retried && (!options.method || options.method === 'GET') && refreshToken) {
        if (sentToken === accessToken) await refresh()
        return request(path, options, true)
      }
      throw expire()
    }
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new ApiError(errorText(data) || `Request failed (${response.status}). Please try again.`, response.status)
    }
    if (data === null) throw new ApiError('The server returned an unreadable response.')
    return data
  }
  async function list(path, options) {
    const result = []
    const visited = new Set()
    while (path) {
      const normalized = apiPath(path)
      if (visited.has(normalized)) throw new ApiError('The server returned a repeated pagination link.')
      visited.add(normalized)
      const data = await request(normalized, options)
      if (Array.isArray(data)) return [...result, ...data]
      if (!Array.isArray(data.results)) throw new ApiError('The server returned an unexpected list response.')
      result.push(...data.results)
      path = data.next
    }
    return result
  }
  return {
    stock: (signal) => list('/api/stock/', { signal }),
    medicines: (search, signal) => list(`/api/medicines/?search=${encodeURIComponent(search)}`, { signal }),
    finder: (query, signal) => list(`/api/finder/?q=${encodeURIComponent(query)}`, { signal }),
    sale: async (payload) => {
      // Renew before checkout so the POST is sent once with a fresh token.
      if (refreshToken) {
        try { await refresh() }
        catch (error) { error.notSent = true; throw error }
      }
      return request('/api/sales/', { method: 'POST', body: JSON.stringify(payload) })
    },
  }
}
